"""
models/classified_feedback.py — SQLAlchemy model for the classified_feedback table
Module 4: NLP Classification & Theme Extraction
Stores AI-generated classification, sentiment, themes, keywords, and pain points.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
    Text,
    CheckConstraint,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from database.db import db


class ClassifiedFeedback(db.Model):
    __tablename__ = "classified_feedback"

    __table_args__ = (
        CheckConstraint(
            "ai_category IN ("
            "'Bug Report', 'Feature Request', 'Complaint', 'Praise', "
            "'Question', 'Pricing Issue', 'Performance Issue', "
            "'UI Issue', 'Security Concern')",
            name="chk_clf_ai_category",
        ),
        CheckConstraint(
            "ai_sentiment IN ('Positive', 'Negative', 'Neutral', 'Mixed')",
            name="chk_clf_ai_sentiment",
        ),
        CheckConstraint(
            "ai_confidence_score >= 0.0 AND ai_confidence_score <= 1.0",
            name="chk_clf_confidence_range",
        ),
        CheckConstraint(
            "ai_sentiment_score >= -1.0 AND ai_sentiment_score <= 1.0",
            name="chk_clf_sentiment_score_range",
        ),
        CheckConstraint(
            "classification_status IN ('classified', 'failed')",
            name="chk_clf_status",
        ),
        CheckConstraint("weight >= 1", name="chk_clf_weight"),
    )

    # ------------------------------------------------------------------
    # Primary Key
    # ------------------------------------------------------------------
    classified_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Foreign Key → processed_feedback (cascade delete)
    # ------------------------------------------------------------------
    processed_feedback_id = Column(
        UUID(as_uuid=True),
        db.ForeignKey("processed_feedback.processed_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # ------------------------------------------------------------------
    # Project Association (inherited from processed_feedback)
    # ------------------------------------------------------------------
    project_id = Column(UUID(as_uuid=True), nullable=False)

    # ------------------------------------------------------------------
    # AI Classification Output
    # ------------------------------------------------------------------
    ai_category = Column(String(100), nullable=False)
    # One of: Bug Report, Feature Request, Complaint, Praise, Question,
    #         Pricing Issue, Performance Issue, UI Issue, Security Concern

    ai_confidence_score = Column(Float, nullable=False, default=0.0)
    # Gemini's confidence in the classification (0.0 – 1.0)

    # ------------------------------------------------------------------
    # AI Sentiment Analysis
    # ------------------------------------------------------------------
    ai_sentiment = Column(String(50), nullable=False, default="Neutral")
    # Positive / Negative / Neutral / Mixed

    ai_sentiment_score = Column(Float, nullable=False, default=0.0)
    # Sentiment intensity (-1.0 to 1.0)

    # ------------------------------------------------------------------
    # Extracted Topics, Themes, Keywords
    # ------------------------------------------------------------------
    topics = Column(ARRAY(Text), nullable=False, default=list)
    # High-level subject areas identified by AI

    themes = Column(ARRAY(Text), nullable=False, default=list)
    # Recurring patterns or themes

    keywords = Column(ARRAY(Text), nullable=False, default=list)
    # Important terms extracted from the text

    # ------------------------------------------------------------------
    # Pain Points & Customer Intent
    # ------------------------------------------------------------------
    pain_points = Column(ARRAY(Text), nullable=False, default=list)
    # Specific user frustrations identified by AI

    customer_intent = Column(String(500), nullable=True)
    # What the customer is trying to achieve

    # ------------------------------------------------------------------
    # AI Summary
    # ------------------------------------------------------------------
    ai_summary = Column(Text, nullable=True)
    # AI-generated concise summary of the feedback

    # ------------------------------------------------------------------
    # Weight (inherited from processed_feedback for quick aggregation)
    # ------------------------------------------------------------------
    weight = Column(Integer, nullable=False, default=1)

    # ------------------------------------------------------------------
    # Classification Metadata (JSONB)
    # ------------------------------------------------------------------
    classification_metadata = Column(JSONB, nullable=False, default=dict)
    # Structure:
    # {
    #   "gemini_model": "gemini-2.0-flash",
    #   "prompt_version": "1.0.0",
    #   "classification_duration_ms": 850,
    #   "token_usage": { "prompt_tokens": 500, "completion_tokens": 200 }
    # }

    # ------------------------------------------------------------------
    # Classification Status
    # ------------------------------------------------------------------
    classification_status = Column(
        String(50), nullable=False, default="classified"
    )
    classification_error = Column(Text, nullable=True)

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    classified_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    processed_feedback = relationship(
        "ProcessedFeedback",
        backref="classified_record",
        foreign_keys=[processed_feedback_id],
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def to_dict(self):
        return {
            "classified_id": str(self.classified_id),
            "processed_feedback_id": str(self.processed_feedback_id),
            "project_id": str(self.project_id),
            "ai_category": self.ai_category,
            "ai_confidence_score": self.ai_confidence_score,
            "ai_sentiment": self.ai_sentiment,
            "ai_sentiment_score": self.ai_sentiment_score,
            "topics": self.topics or [],
            "themes": self.themes or [],
            "keywords": self.keywords or [],
            "pain_points": self.pain_points or [],
            "customer_intent": self.customer_intent,
            "ai_summary": self.ai_summary,
            "weight": self.weight,
            "classification_metadata": self.classification_metadata or {},
            "classification_status": self.classification_status,
            "classification_error": self.classification_error,
            "classified_at": (
                self.classified_at.isoformat() if self.classified_at else None
            ),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }

    def to_summary_dict(self):
        """Lightweight summary for list views."""
        return {
            "classified_id": str(self.classified_id),
            "ai_category": self.ai_category,
            "ai_confidence_score": self.ai_confidence_score,
            "ai_sentiment": self.ai_sentiment,
            "keywords": (self.keywords or [])[:5],
            "weight": self.weight,
            "classified_at": (
                self.classified_at.isoformat() if self.classified_at else None
            ),
        }

    def __repr__(self):
        return (
            f"<ClassifiedFeedback {self.classified_id} "
            f"cat={self.ai_category} conf={self.ai_confidence_score:.2f}>"
        )
