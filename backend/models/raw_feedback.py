"""
models/raw_feedback.py — SQLAlchemy model for the raw_feedback table
Mirrors schema.md: Table 2 — raw_feedback (24 columns)
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
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from database.db import db


class RawFeedback(db.Model):
    __tablename__ = "raw_feedback"

    __table_args__ = (
        CheckConstraint(
            "source IN ('csv_upload', 'text_form')",
            name="chk_raw_source",
        ),
        CheckConstraint(
            "submitted_by_role IN ('product_manager', 'customer')",
            name="chk_raw_submitted_by_role",
        ),
        CheckConstraint(
            "priority IN ('Low', 'Medium', 'High', 'Critical')",
            name="chk_raw_priority",
        ),
        CheckConstraint(
            "category IN ('Bug', 'Feature Request', 'Improvement', 'Complaint', 'General')",
            name="chk_raw_category",
        ),
        CheckConstraint(
            "sentiment_self_reported IN ('Positive', 'Negative', 'Neutral') OR sentiment_self_reported IS NULL",
            name="chk_raw_sentiment",
        ),
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'processed', 'duplicate', 'failed')",
            name="chk_raw_processing_status",
        ),
        CheckConstraint(
            "weight >= 1",
            name="chk_raw_weight_positive",
        ),
        CheckConstraint(
            "LENGTH(TRIM(subject)) > 0",
            name="chk_raw_subject_not_empty",
        ),
        CheckConstraint(
            "LENGTH(TRIM(description)) > 0",
            name="chk_raw_description_not_empty",
        ),
    )

    # ------------------------------------------------------------------
    # Primary Key
    # ------------------------------------------------------------------
    feedback_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Source & Submitter
    # ------------------------------------------------------------------
    source = Column(String(50), nullable=False)
    submitted_by_role = Column(String(50), nullable=False)
    user_id = Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=False,
    )
    project_id = Column(UUID(as_uuid=True), nullable=False)

    # ------------------------------------------------------------------
    # Customer Information (CSV rows only)
    # ------------------------------------------------------------------
    customer_name = Column(String(255), nullable=True)
    customer_email = Column(String(255), nullable=True)

    # ------------------------------------------------------------------
    # Core Feedback Content
    # ------------------------------------------------------------------
    subject = Column(Text, nullable=False)
    description = Column(Text, nullable=False)

    # ------------------------------------------------------------------
    # Structured Classification Fields
    # ------------------------------------------------------------------
    priority = Column(String(50), nullable=False, default="Medium")
    category = Column(String(100), nullable=False, default="General")
    product_name = Column(String(255), nullable=True)
    product_version = Column(String(100), nullable=True)
    submission_date = Column(Date, nullable=True)
    tags = Column(ARRAY(Text), nullable=True)
    sentiment_self_reported = Column(String(50), nullable=True)
    language = Column(String(10), nullable=False, default="en")

    # ------------------------------------------------------------------
    # Ingestion Metadata
    # ------------------------------------------------------------------
    upload_timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    raw_metadata = Column(JSONB, nullable=False, default=dict)
    canonical_json = Column(JSONB, nullable=False, default=dict)

    # ------------------------------------------------------------------
    # Deduplication Fields (set by Module 3)
    # ------------------------------------------------------------------
    weight = Column(Integer, nullable=False, default=1)
    duplicate_group_id = Column(UUID(as_uuid=True), nullable=True)

    # ------------------------------------------------------------------
    # Processing Status Lifecycle
    # ------------------------------------------------------------------
    processing_status = Column(String(50), nullable=False, default="pending")
    processing_error = Column(Text, nullable=True)
    processed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # ------------------------------------------------------------------
    # Audit Timestamps
    # ------------------------------------------------------------------
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
    user = relationship(
        "User",
        back_populates="raw_feedbacks",
        foreign_keys=[user_id],
    )
    processed_record = relationship(
        "ProcessedFeedback",
        back_populates="raw_feedback",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def to_dict(self):
        return {
            "feedback_id": str(self.feedback_id),
            "source": self.source,
            "submitted_by_role": self.submitted_by_role,
            "user_id": str(self.user_id) if self.user_id else None,
            "project_id": str(self.project_id) if self.project_id else None,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "subject": self.subject,
            "description": self.description,
            "priority": self.priority,
            "category": self.category,
            "product_name": self.product_name,
            "product_version": self.product_version,
            "submission_date": (
                self.submission_date.isoformat() if self.submission_date else None
            ),
            "tags": self.tags or [],
            "sentiment_self_reported": self.sentiment_self_reported,
            "language": self.language,
            "upload_timestamp": (
                self.upload_timestamp.isoformat() if self.upload_timestamp else None
            ),
            "raw_metadata": self.raw_metadata or {},
            "weight": self.weight,
            "duplicate_group_id": (
                str(self.duplicate_group_id) if self.duplicate_group_id else None
            ),
            "processing_status": self.processing_status,
            "processing_error": self.processing_error,
            "processed_at": (
                self.processed_at.isoformat() if self.processed_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_status_dict(self):
        """Lightweight status-only response."""
        return {
            "feedback_id": str(self.feedback_id),
            "processing_status": self.processing_status,
            "weight": self.weight,
            "duplicate_group_id": (
                str(self.duplicate_group_id) if self.duplicate_group_id else None
            ),
            "processing_error": self.processing_error,
            "upload_timestamp": (
                self.upload_timestamp.isoformat() if self.upload_timestamp else None
            ),
            "processed_at": (
                self.processed_at.isoformat() if self.processed_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<RawFeedback {self.feedback_id} [{self.processing_status}]>"
