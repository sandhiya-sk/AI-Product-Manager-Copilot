"""
services/aggregation_pipeline.py — Module 5 Feature Request Aggregation

Uses Google Gemini to semantically cluster classified feature requests,
detect duplicates, calculate frequency, assign importance, group customers,
and detect trends over time.
"""

import os
import json
import time
import uuid
from datetime import datetime, timezone
from collections import Counter

import google.generativeai as genai
from sqlalchemy import func

from database.db import db
from models.classified_feedback import ClassifiedFeedback
from models.processed_feedback import ProcessedFeedback
from models.aggregated_feature import AggregatedFeature


# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────

AGGREGATION_SYSTEM_INSTRUCTION = """You are an expert AI Product Manager assistant that aggregates and clusters feature requests.

Your task is to analyze a list of classified feature requests and group semantically similar ones into clusters.

For each cluster, return a JSON object with:
1. **cluster_label** (string): A concise, human-readable name for the feature cluster (e.g., "Dark Mode", "Export to PDF", "Multi-language Support"). Use Title Case.
2. **cluster_description** (string): A 1-2 sentence description of what the feature cluster encompasses.
3. **importance** (string): One of "Critical", "High", "Medium", "Low" — derived from:
   - Frequency (more requests = higher importance)
   - Sentiment intensity (strong negative sentiment = higher urgency)
   - Number of distinct users requesting it
4. **member_ids** (array of integers): The index numbers of the feature requests that belong to this cluster (0-based indices from the input list).
5. **representative_keywords** (array of strings): 3-8 keywords that best represent this cluster.

IMPORTANT RULES:
- Return ONLY valid JSON — an array of cluster objects. No markdown, no code fences, no explanation text.
- Every input feature request MUST appear in exactly one cluster. Do not skip any.
- Merge semantically similar requests even if they use different wording (e.g., "night mode", "dark theme", "dark mode" should all be in one cluster).
- Single unique feature requests that don't match any other should still form their own cluster (with 1 member).
- Sort clusters by importance (Critical first, then High, Medium, Low).
- The cluster_label should be concise (2-5 words max).
"""


class AggregationPipeline:
    """
    Module 5 Feature Request Aggregation Pipeline.

    Fetches classified feature requests, sends them to Gemini for
    semantic clustering, calculates metrics, detects trends,
    and stores results in the aggregated_features table.
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.prompt_version = os.getenv("AGGREGATION_PROMPT_VERSION", "1.0.0")

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set in environment variables. "
                "Please add it to your .env file."
            )

        # Configure Gemini SDK
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=AGGREGATION_SYSTEM_INSTRUCTION,
            generation_config=genai.GenerationConfig(
                temperature=0.15,
                top_p=0.8,
                max_output_tokens=8192,
                response_mime_type="application/json",
            ),
        )

    # ──────────────────────────────────────────────────────────
    # Fetch Feature Requests from Classified Feedback
    # ──────────────────────────────────────────────────────────

    def fetch_feature_requests(self, project_id) -> list[ClassifiedFeedback]:
        """
        Fetch all classified_feedback records with ai_category = 'Feature Request'
        for the given project.
        """
        return (
            ClassifiedFeedback.query
            .filter_by(
                project_id=project_id,
                ai_category="Feature Request",
                classification_status="classified",
            )
            .order_by(ClassifiedFeedback.classified_at.asc())
            .all()
        )

    # ──────────────────────────────────────────────────────────
    # Build Aggregation Prompt
    # ──────────────────────────────────────────────────────────

    def build_prompt(self, feature_requests: list[ClassifiedFeedback]) -> str:
        """
        Construct the user prompt listing all feature requests for Gemini
        to cluster semantically.
        """
        prompt_parts = [
            f"Analyze the following {len(feature_requests)} feature requests "
            f"and group semantically similar ones into clusters.\n\n"
        ]

        for idx, fr in enumerate(feature_requests):
            summary = fr.ai_summary or ""
            keywords = ", ".join(fr.keywords or [])
            themes = ", ".join(fr.themes or [])
            intent = fr.customer_intent or ""

            prompt_parts.append(
                f"[{idx}] Summary: {summary} | "
                f"Keywords: {keywords} | "
                f"Themes: {themes} | "
                f"Intent: {intent} | "
                f"Sentiment: {fr.ai_sentiment} ({fr.ai_sentiment_score}) | "
                f"Weight: {fr.weight}\n"
            )

        prompt_parts.append(
            "\nReturn a JSON array of cluster objects. "
            "Each cluster must have: cluster_label, cluster_description, "
            "importance, member_ids (0-based indices), representative_keywords."
        )

        return "".join(prompt_parts)

    # ──────────────────────────────────────────────────────────
    # Call Gemini for Semantic Clustering
    # ──────────────────────────────────────────────────────────

    def cluster_via_gemini(self, feature_requests: list[ClassifiedFeedback]) -> tuple[list[dict], dict]:
        """
        Send feature requests to Gemini and get semantic clusters back.

        Returns:
            (clusters_list, metadata_dict)
        """
        prompt = self.build_prompt(feature_requests)
        start_time = time.time()

        response = self.model.generate_content(prompt)
        duration_ms = int((time.time() - start_time) * 1000)

        # Parse JSON response
        response_text = response.text.strip()

        # Clean potential markdown fences
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines)

        clusters = json.loads(response_text)

        # Extract token usage
        token_usage = {}
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = response.usage_metadata
            token_usage = {
                "prompt_tokens": getattr(usage, "prompt_token_count", 0),
                "completion_tokens": getattr(usage, "candidates_token_count", 0),
                "total_tokens": getattr(usage, "total_token_count", 0),
            }

        metadata = {
            "gemini_model": self.model_name,
            "prompt_version": self.prompt_version,
            "aggregation_duration_ms": duration_ms,
            "total_feature_requests_analyzed": len(feature_requests),
            "clusters_formed": len(clusters),
            "token_usage": token_usage,
        }

        return clusters, metadata

    # ──────────────────────────────────────────────────────────
    # Calculate Trend Direction
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def calculate_trend(member_records: list[ClassifiedFeedback]) -> tuple[str, dict]:
        """
        Analyze the timestamps of cluster member records to determine
        if the feature request trend is rising, stable, or declining.

        Returns:
            (trend_direction, trend_details)
        """
        if not member_records:
            return "stable", {}

        # Collect timestamps
        timestamps = []
        for rec in member_records:
            ts = rec.classified_at or rec.created_at
            if ts:
                timestamps.append(ts)

        if not timestamps:
            return "stable", {}

        timestamps.sort()
        first_seen = timestamps[0]
        last_seen = timestamps[-1]

        # Group by ISO week
        weekly_counts = Counter()
        for ts in timestamps:
            week_key = ts.strftime("%G-W%V")
            weekly_counts[week_key] += 1

        sorted_weeks = sorted(weekly_counts.items())

        # Calculate growth rate (compare first half vs second half)
        if len(sorted_weeks) >= 2:
            mid = len(sorted_weeks) // 2
            first_half_avg = sum(c for _, c in sorted_weeks[:mid]) / max(mid, 1)
            second_half_avg = sum(c for _, c in sorted_weeks[mid:]) / max(len(sorted_weeks) - mid, 1)

            if first_half_avg > 0:
                growth_rate = (second_half_avg - first_half_avg) / first_half_avg
            else:
                growth_rate = 1.0 if second_half_avg > 0 else 0.0
        else:
            growth_rate = 0.0

        # Determine direction
        if growth_rate > 0.20:
            direction = "rising"
        elif growth_rate < -0.20:
            direction = "declining"
        else:
            direction = "stable"

        trend_details = {
            "weekly_counts": [
                {"week": week, "count": count}
                for week, count in sorted_weeks
            ],
            "first_seen": first_seen.isoformat(),
            "last_seen": last_seen.isoformat(),
            "growth_rate": round(growth_rate, 3),
        }

        return direction, trend_details

    # ──────────────────────────────────────────────────────────
    # Calculate Dominant Sentiment
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def calculate_dominant_sentiment(member_records: list[ClassifiedFeedback]) -> str:
        """Find the most frequent sentiment among cluster members."""
        if not member_records:
            return "Neutral"

        sentiment_counts = Counter()
        for rec in member_records:
            sentiment_counts[rec.ai_sentiment] += (rec.weight or 1)

        return sentiment_counts.most_common(1)[0][0]

    # ──────────────────────────────────────────────────────────
    # Calculate Affected Users
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def calculate_affected_users(member_records: list[ClassifiedFeedback]) -> int:
        """
        Count distinct users across cluster members by looking up
        processed_feedback → raw_feedback → user_id chain.
        """
        user_ids = set()
        for rec in member_records:
            if rec.processed_feedback:
                user_ids.add(str(rec.processed_feedback.user_id))
        return len(user_ids)

    # ──────────────────────────────────────────────────────────
    # Validate Importance
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def validate_importance(importance: str) -> str:
        """Ensure importance is one of the valid values."""
        valid = ["Critical", "High", "Medium", "Low"]
        if importance in valid:
            return importance
        # Fuzzy match
        importance_lower = importance.lower()
        for v in valid:
            if v.lower() in importance_lower:
                return v
        return "Medium"

    # ──────────────────────────────────────────────────────────
    # Run Full Aggregation Pipeline
    # ──────────────────────────────────────────────────────────

    def run(self, project_id) -> dict:
        """
        Runs the full Module 5 aggregation pipeline:
        1. Fetch all classified Feature Request records for the project
        2. Send to Gemini for semantic clustering
        3. Calculate metrics (frequency, affected users, trends)
        4. Clear old aggregation data for the project
        5. Store fresh clusters in aggregated_features

        Returns:
            dict with counts: clusters_created, total_requests, failed
        """
        # Convert to UUID if string
        if isinstance(project_id, str):
            project_id = uuid.UUID(project_id)

        feature_requests = self.fetch_feature_requests(project_id)

        if not feature_requests:
            return {
                "clusters_created": 0,
                "total_requests": 0,
                "failed": 0,
                "message": "No classified feature requests found for this project.",
            }

        # If we have a very large number, we still send them all
        # (Gemini can handle large contexts)
        try:
            clusters, metadata = self.cluster_via_gemini(feature_requests)
        except Exception as e:
            print(f"[Module 5] Gemini clustering failed: {e}")
            return {
                "clusters_created": 0,
                "total_requests": len(feature_requests),
                "failed": 1,
                "error": str(e),
            }

        # Clear existing aggregations for this project (full refresh)
        AggregatedFeature.query.filter_by(project_id=project_id).delete()
        db.session.flush()

        clusters_created = 0
        failed = 0

        for cluster_data in clusters:
            try:
                # Get member indices and resolve to actual records
                member_indices = cluster_data.get("member_ids", [])
                member_records = []
                member_ids = []

                for idx in member_indices:
                    if 0 <= idx < len(feature_requests):
                        rec = feature_requests[idx]
                        member_records.append(rec)
                        member_ids.append(rec.classified_id)

                if not member_records:
                    continue

                # Calculate frequency (sum of weights)
                frequency = sum(rec.weight or 1 for rec in member_records)

                # Calculate affected users
                affected_users = self.calculate_affected_users(member_records)

                # Calculate average sentiment score
                total_sentiment = sum(
                    rec.ai_sentiment_score * (rec.weight or 1)
                    for rec in member_records
                )
                avg_sentiment = total_sentiment / frequency if frequency > 0 else 0.0
                avg_sentiment = max(-1.0, min(1.0, avg_sentiment))

                # Calculate dominant sentiment
                dominant_sentiment = self.calculate_dominant_sentiment(member_records)

                # Calculate trend
                trend_direction, trend_details = self.calculate_trend(member_records)

                # Select sample feedback IDs (up to 5)
                sample_ids = [rec.classified_id for rec in member_records[:5]]

                # Validate importance
                importance = self.validate_importance(
                    cluster_data.get("importance", "Medium")
                )

                # Create aggregated record
                agg_record = AggregatedFeature(
                    project_id=project_id,
                    cluster_label=cluster_data.get("cluster_label", "Unknown Feature"),
                    cluster_description=cluster_data.get("cluster_description"),
                    frequency=frequency,
                    importance=importance,
                    affected_users=affected_users,
                    avg_sentiment_score=round(avg_sentiment, 3),
                    dominant_sentiment=dominant_sentiment,
                    representative_keywords=cluster_data.get("representative_keywords", []),
                    sample_feedback_ids=sample_ids,
                    member_classified_ids=member_ids,
                    trend_direction=trend_direction,
                    trend_details=trend_details,
                    aggregation_metadata=metadata,
                    aggregation_status="aggregated",
                )

                db.session.add(agg_record)
                clusters_created += 1

            except Exception as e:
                print(
                    f"[Module 5] Failed to create cluster "
                    f"'{cluster_data.get('cluster_label', '?')}': {e}"
                )
                failed += 1

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[Module 5] Failed to commit aggregation results: {e}")
            return {
                "clusters_created": 0,
                "total_requests": len(feature_requests),
                "failed": len(clusters),
                "error": str(e),
            }

        return {
            "clusters_created": clusters_created,
            "total_requests": len(feature_requests),
            "failed": failed,
        }
