"""
services/classification_pipeline.py — Module 4 NLP Classification & Theme Extraction

Uses Google Gemini to classify processed feedback into 9 categories and extract
topics, themes, sentiments, keywords, pain points, and customer intent.
"""

import os
import json
import time
import uuid
from datetime import datetime, timezone

import google.generativeai as genai

from database.db import db
from models.processed_feedback import ProcessedFeedback
from models.classified_feedback import ClassifiedFeedback


# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────

VALID_CATEGORIES = [
    "Bug Report",
    "Feature Request",
    "Complaint",
    "Praise",
    "Question",
    "Pricing Issue",
    "Performance Issue",
    "UI Issue",
    "Security Concern",
]

VALID_SENTIMENTS = ["Positive", "Negative", "Neutral", "Mixed"]

SYSTEM_INSTRUCTION = """You are an expert AI Product Manager assistant that classifies customer feedback.
You analyze product feedback and extract structured insights.

Your task is to analyze the provided feedback text and return a JSON object with the following fields:

1. **category** (string): Classify into exactly ONE of these categories:
   - "Bug Report" — Software defect, error, crash, malfunction
   - "Feature Request" — New capability, enhancement, addition desired
   - "Complaint" — General dissatisfaction, frustration expression
   - "Praise" — Positive feedback, compliment, appreciation
   - "Question" — Inquiry, help request, clarification needed
   - "Pricing Issue" — Cost concern, billing problem, subscription issue
   - "Performance Issue" — Slow speed, lag, resource consumption, timeout
   - "UI Issue" — Interface problem, design flaw, usability issue, layout bug
   - "Security Concern" — Security vulnerability, privacy issue, data breach worry

2. **confidence_score** (float): Your confidence in the classification (0.0 to 1.0)

3. **sentiment** (string): One of "Positive", "Negative", "Neutral", "Mixed"

4. **sentiment_score** (float): Sentiment intensity from -1.0 (very negative) to 1.0 (very positive)

5. **topics** (array of strings): 2-5 high-level subject areas (e.g., "authentication", "mobile app", "billing")

6. **themes** (array of strings): 2-5 recurring patterns or themes (e.g., "user onboarding friction", "payment flow complexity")

7. **keywords** (array of strings): 5-10 important terms extracted from the text

8. **pain_points** (array of strings): 1-5 specific user frustrations or problems identified

9. **customer_intent** (string): A one-sentence description of what the customer wants to achieve

10. **summary** (string): A 1-2 sentence concise summary of the feedback

IMPORTANT RULES:
- Return ONLY valid JSON. No markdown, no code fences, no explanation text.
- All string values must be properly escaped.
- Arrays must contain at least 1 item.
- The category MUST be exactly one of the 9 listed categories.
- The sentiment MUST be exactly one of: Positive, Negative, Neutral, Mixed.
"""


class ClassificationPipeline:
    """
    Module 4 Classification Pipeline.

    Fetches unclassified processed feedback, sends each to Gemini for
    AI-powered classification and theme extraction, and stores results
    in the classified_feedback table.
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.prompt_version = os.getenv("CLASSIFICATION_PROMPT_VERSION", "1.0.0")
        self.batch_size = int(os.getenv("CLASSIFICATION_BATCH_SIZE", 10))

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set in environment variables. "
                "Please add it to your .env file."
            )

        # Configure Gemini SDK
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=SYSTEM_INSTRUCTION,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                top_p=0.8,
                max_output_tokens=2048,
                response_mime_type="application/json",
            ),
        )

    # ──────────────────────────────────────────────────────────
    # Fetch Unclassified Records
    # ──────────────────────────────────────────────────────────

    def fetch_unclassified(self, project_id=None) -> list[ProcessedFeedback]:
        """
        Fetch processed_feedback records that are ready for classification
        but have not yet been classified.
        """
        query = ProcessedFeedback.query.filter_by(
            ready_for_classification=True
        ).filter(ProcessedFeedback.classified_at.is_(None))

        if project_id:
            query = query.filter_by(project_id=project_id)

        return query.order_by(
            ProcessedFeedback.processing_timestamp.asc()
        ).limit(self.batch_size).all()

    # ──────────────────────────────────────────────────────────
    # Build Prompt for a Single Feedback
    # ──────────────────────────────────────────────────────────

    def build_prompt(self, feedback: ProcessedFeedback) -> str:
        """
        Construct the user prompt with all available context
        for Gemini classification.
        """
        prompt_parts = [
            "Analyze the following product feedback and classify it.\n",
            f"**Subject:** {feedback.original_subject}\n",
            f"**Description:** {feedback.original_description}\n",
            f"**Clean Text:** {feedback.clean_text}\n",
        ]

        # Add optional metadata context
        if feedback.category and feedback.category != "General":
            prompt_parts.append(
                f"**Self-Reported Category (user-provided, may be inaccurate):** "
                f"{feedback.category}\n"
            )

        if feedback.priority:
            prompt_parts.append(
                f"**Self-Reported Priority:** {feedback.priority}\n"
            )

        if feedback.sentiment_self_reported:
            prompt_parts.append(
                f"**Self-Reported Sentiment:** "
                f"{feedback.sentiment_self_reported}\n"
            )

        if feedback.tags:
            prompt_parts.append(
                f"**User Tags:** {', '.join(feedback.tags)}\n"
            )

        if feedback.product_name:
            prompt_parts.append(
                f"**Product:** {feedback.product_name}"
            )
            if feedback.product_version:
                prompt_parts.append(f" v{feedback.product_version}")
            prompt_parts.append("\n")

        if feedback.lemmas:
            prompt_parts.append(
                f"**Key Lemmas:** {', '.join(feedback.lemmas[:15])}\n"
            )

        prompt_parts.append(
            f"\n**Weight (duplicate count):** {feedback.weight}\n"
        )

        prompt_parts.append(
            "\nReturn a JSON object with: category, confidence_score, "
            "sentiment, sentiment_score, topics, themes, keywords, "
            "pain_points, customer_intent, summary."
        )

        return "".join(prompt_parts)

    # ──────────────────────────────────────────────────────────
    # Classify a Single Feedback via Gemini
    # ──────────────────────────────────────────────────────────

    def classify_single(self, feedback: ProcessedFeedback) -> dict:
        """
        Send a single feedback to Gemini and parse the structured response.

        Returns:
            dict with classification fields, or raises on failure.
        """
        prompt = self.build_prompt(feedback)
        start_time = time.time()

        response = self.model.generate_content(prompt)
        duration_ms = int((time.time() - start_time) * 1000)

        # Parse the JSON response
        response_text = response.text.strip()

        # Clean potential markdown fences
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first and last lines if they are fences
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines)

        parsed = json.loads(response_text)

        # Validate and sanitize the response
        result = self._validate_response(parsed)
        result["duration_ms"] = duration_ms

        # Extract token usage if available
        token_usage = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = response.usage_metadata
            token_usage = {
                "prompt_tokens": getattr(usage, "prompt_token_count", 0),
                "completion_tokens": getattr(
                    usage, "candidates_token_count", 0
                ),
                "total_tokens": getattr(usage, "total_token_count", 0),
            }
        result["token_usage"] = token_usage

        return result

    # ──────────────────────────────────────────────────────────
    # Validate & Sanitize Gemini Response
    # ──────────────────────────────────────────────────────────

    def _validate_response(self, parsed: dict) -> dict:
        """
        Validate and sanitize the parsed JSON response from Gemini.
        Ensures all fields conform to expected types and constraints.
        """
        # Category validation
        category = parsed.get("category", "Complaint")
        if category not in VALID_CATEGORIES:
            # Attempt fuzzy match
            category_lower = category.lower()
            matched = False
            for valid_cat in VALID_CATEGORIES:
                if valid_cat.lower() in category_lower or category_lower in valid_cat.lower():
                    category = valid_cat
                    matched = True
                    break
            if not matched:
                category = "Complaint"  # Safe fallback

        # Confidence score
        confidence = float(parsed.get("confidence_score", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        # Sentiment validation
        sentiment = parsed.get("sentiment", "Neutral")
        if sentiment not in VALID_SENTIMENTS:
            sentiment = "Neutral"

        # Sentiment score
        sentiment_score = float(parsed.get("sentiment_score", 0.0))
        sentiment_score = max(-1.0, min(1.0, sentiment_score))

        # Array fields — ensure list of strings
        topics = self._ensure_string_list(parsed.get("topics", []))
        themes = self._ensure_string_list(parsed.get("themes", []))
        keywords = self._ensure_string_list(parsed.get("keywords", []))
        pain_points = self._ensure_string_list(parsed.get("pain_points", []))

        # String fields
        customer_intent = str(parsed.get("customer_intent", ""))[:500]
        summary = str(parsed.get("summary", ""))

        return {
            "category": category,
            "confidence_score": confidence,
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "topics": topics,
            "themes": themes,
            "keywords": keywords,
            "pain_points": pain_points,
            "customer_intent": customer_intent or None,
            "summary": summary or None,
        }

    @staticmethod
    def _ensure_string_list(value) -> list:
        """Convert a value to a list of strings, handling edge cases."""
        if isinstance(value, list):
            return [str(item) for item in value if item]
        if isinstance(value, str):
            return [value]
        return []

    # ──────────────────────────────────────────────────────────
    # Run Full Classification Pipeline
    # ──────────────────────────────────────────────────────────

    def run(self, project_id=None) -> dict:
        """
        Runs the full classification pipeline:
        1. Fetch unclassified processed_feedback records
        2. Classify each via Gemini
        3. Store results in classified_feedback
        4. Update processed_feedback.classified_at

        Returns:
            dict with counts: classified, failed, skipped
        """
        records = self.fetch_unclassified(project_id)

        if not records:
            return {"classified": 0, "failed": 0, "total_fetched": 0}

        classified_count = 0
        failed_count = 0

        for feedback in records:
            start_time = time.time()

            try:
                # Classify via Gemini
                result = self.classify_single(feedback)
                duration_ms = result.pop("duration_ms", 0)
                token_usage = result.pop("token_usage", {})

                # Build classification metadata
                metadata = {
                    "gemini_model": self.model_name,
                    "prompt_version": self.prompt_version,
                    "classification_duration_ms": duration_ms,
                    "token_usage": token_usage,
                }

                # Create ClassifiedFeedback record
                classified_rec = ClassifiedFeedback(
                    processed_feedback_id=feedback.processed_id,
                    project_id=feedback.project_id,
                    ai_category=result["category"],
                    ai_confidence_score=result["confidence_score"],
                    ai_sentiment=result["sentiment"],
                    ai_sentiment_score=result["sentiment_score"],
                    topics=result["topics"],
                    themes=result["themes"],
                    keywords=result["keywords"],
                    pain_points=result["pain_points"],
                    customer_intent=result["customer_intent"],
                    ai_summary=result["summary"],
                    weight=feedback.weight,
                    classification_metadata=metadata,
                    classification_status="classified",
                )

                db.session.add(classified_rec)

                # Mark the processed_feedback as classified
                feedback.classified_at = datetime.now(timezone.utc)

                db.session.commit()
                classified_count += 1

            except Exception as e:
                db.session.rollback()
                print(
                    f"[Module 4] Failed to classify processed_feedback "
                    f"{feedback.processed_id}: {e}"
                )

                # Attempt to store a failed record for traceability
                try:
                    failed_rec = ClassifiedFeedback(
                        processed_feedback_id=feedback.processed_id,
                        project_id=feedback.project_id,
                        ai_category="Complaint",  # Fallback category
                        ai_confidence_score=0.0,
                        ai_sentiment="Neutral",
                        ai_sentiment_score=0.0,
                        topics=[],
                        themes=[],
                        keywords=[],
                        pain_points=[],
                        customer_intent=None,
                        ai_summary=None,
                        weight=feedback.weight,
                        classification_metadata={
                            "gemini_model": self.model_name,
                            "prompt_version": self.prompt_version,
                            "error": str(e),
                        },
                        classification_status="failed",
                        classification_error=str(e)[:2000],
                    )
                    db.session.add(failed_rec)

                    # Still mark as classified to prevent infinite retries
                    feedback.classified_at = datetime.now(timezone.utc)

                    db.session.commit()
                except Exception as inner_e:
                    db.session.rollback()
                    print(
                        f"[Module 4] Failed to store error record for "
                        f"{feedback.processed_id}: {inner_e}"
                    )

                failed_count += 1

        return {
            "classified": classified_count,
            "failed": failed_count,
            "total_fetched": len(records),
        }
