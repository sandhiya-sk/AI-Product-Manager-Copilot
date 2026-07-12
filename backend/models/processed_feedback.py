"""
models/processed_feedback.py — SQLAlchemy model for the processed_feedback table
Mirrors schema.md: Table 3 — processed_feedback (32 columns)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Integer,
    String,
    Text,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMPTZ, TSVECTOR, UUID
from sqlalchemy.orm import relationship

from database.db import db


class ProcessedFeedback(db.Model):
    __tablename__ = "processed_feedback"

    __table_args__ = (
        CheckConstraint(
            "source IN ('csv_upload', 'text_form')",
            name="chk_proc_source",
        ),
        CheckConstraint(
            "submitted_by_role IN ('product_manager', 'customer')",
            name="chk_proc_submitted_by_role",
        ),
        CheckConstraint(
            "priority IN ('Low', 'Medium', 'High', 'Critical')",
            name="chk_proc_priority",
        ),
        CheckConstraint(
            "category IN ('Bug', 'Feature Request', 'Improvement', 'Complaint', 'General')",
            name="chk_proc_category",
        ),
        CheckConstraint(
            "sentiment_self_reported IN ('Positive', 'Negative', 'Neutral') OR sentiment_self_reported IS NULL",
            name="chk_proc_sentiment",
        ),
        CheckConstraint(
            "processing_status IN ('processed', 'failed', 'reprocessing')",
            name="chk_proc_processing_status",
        ),
        CheckConstraint("weight >= 1", name="chk_proc_weight"),
        CheckConstraint("word_count >= 0", name="chk_proc_word_count"),
        CheckConstraint("char_count >= 0", name="chk_proc_char_count"),
        CheckConstraint("token_count >= 0", name="chk_proc_token_count"),
        CheckConstraint("lemma_count >= 0", name="chk_proc_lemma_count"),
    )

    # ------------------------------------------------------------------
    # Primary Key
    # ------------------------------------------------------------------
    processed_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Foreign Key → raw_feedback (cascade delete)
    # ------------------------------------------------------------------
    raw_feedback_id = Column(
        UUID(as_uuid=True),
        db.ForeignKey("raw_feedback.feedback_id", ondelete="CASCADE"),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Source & Identity (inherited)
    # ------------------------------------------------------------------
    source = Column(String(50), nullable=False)
    submitted_by_role = Column(String(50), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    project_id = Column(UUID(as_uuid=True), nullable=False)

    # ------------------------------------------------------------------
    # Original Text (verbatim from raw_feedback)
    # ------------------------------------------------------------------
    original_subject = Column(Text, nullable=False)
    original_description = Column(Text, nullable=False)

    # ------------------------------------------------------------------
    # NLP Pipeline Text Stages
    # ------------------------------------------------------------------
    clean_text = Column(Text, nullable=False)
    # After: HTML, URL, emoji, extra-space removal

    standardized_text = Column(Text, nullable=False)
    # After: lowercase + date normalization

    # ------------------------------------------------------------------
    # NLP Output Arrays
    # ------------------------------------------------------------------
    tokens = Column(ARRAY(Text), nullable=False, default=list)
    # NLTK word_tokenize; stop words removed

    lemmas = Column(ARRAY(Text), nullable=False, default=list)
    # spaCy en_core_web_sm lemmatization

    # ------------------------------------------------------------------
    # Structured Metadata (normalized)
    # ------------------------------------------------------------------
    priority = Column(String(50), nullable=False, default="Medium")
    category = Column(String(100), nullable=False, default="General")
    product_name = Column(String(255), nullable=True)
    product_version = Column(String(100), nullable=True)
    tags = Column(ARRAY(Text), nullable=True)
    sentiment_self_reported = Column(String(50), nullable=True)
    language = Column(String(10), nullable=False, default="en")
    submission_date = Column(Date, nullable=True)

    # ------------------------------------------------------------------
    # Deduplication Fields
    # ------------------------------------------------------------------
    weight = Column(Integer, nullable=False, default=1)
    duplicate_group_id = Column(UUID(as_uuid=True), nullable=False)

    # ------------------------------------------------------------------
    # Text Statistics
    # ------------------------------------------------------------------
    word_count = Column(Integer, nullable=False, default=0)
    char_count = Column(Integer, nullable=False, default=0)
    token_count = Column(Integer, nullable=False, default=0)
    lemma_count = Column(Integer, nullable=False, default=0)

    # ------------------------------------------------------------------
    # Processing Metadata (JSONB)
    # ------------------------------------------------------------------
    processing_metadata = Column(JSONB, nullable=False, default=dict)
    processing_status = Column(String(50), nullable=False, default="processed")
    processing_error = Column(Text, nullable=True)

    # ------------------------------------------------------------------
    # Full-Text Search Vector (auto-maintained by DB trigger)
    # ------------------------------------------------------------------
    search_vector = Column(TSVECTOR, nullable=True)

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    processing_timestamp = Column(
        TIMESTAMPTZ,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_at = Column(
        TIMESTAMPTZ,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        TIMESTAMPTZ,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ------------------------------------------------------------------
    # Module 4 Handoff Flags
    # ------------------------------------------------------------------
    ready_for_classification = Column(Boolean, nullable=False, default=True)
    classified_at = Column(TIMESTAMPTZ, nullable=True)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    raw_feedback = relationship(
        "RawFeedback",
        back_populates="processed_record",
        foreign_keys=[raw_feedback_id],
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def to_dict(self):
        return {
            "processed_id": str(self.processed_id),
            "raw_feedback_id": str(self.raw_feedback_id),
            "source": self.source,
            "submitted_by_role": self.submitted_by_role,
            "user_id": str(self.user_id),
            "project_id": str(self.project_id),
            "original_subject": self.original_subject,
            "original_description": self.original_description,
            "clean_text": self.clean_text,
            "standardized_text": self.standardized_text,
            "tokens": self.tokens or [],
            "lemmas": self.lemmas or [],
            "priority": self.priority,
            "category": self.category,
            "product_name": self.product_name,
            "product_version": self.product_version,
            "tags": self.tags or [],
            "sentiment_self_reported": self.sentiment_self_reported,
            "language": self.language,
            "submission_date": (
                self.submission_date.isoformat() if self.submission_date else None
            ),
            "weight": self.weight,
            "duplicate_group_id": str(self.duplicate_group_id),
            "word_count": self.word_count,
            "char_count": self.char_count,
            "token_count": self.token_count,
            "lemma_count": self.lemma_count,
            "processing_metadata": self.processing_metadata or {},
            "processing_status": self.processing_status,
            "processing_error": self.processing_error,
            "processing_timestamp": (
                self.processing_timestamp.isoformat()
                if self.processing_timestamp
                else None
            ),
            "ready_for_classification": self.ready_for_classification,
            "classified_at": (
                self.classified_at.isoformat() if self.classified_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ProcessedFeedback {self.processed_id} w={self.weight}>"
