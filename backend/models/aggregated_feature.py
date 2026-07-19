"""
models/aggregated_feature.py — SQLAlchemy model for the aggregated_features table
Module 5: Feature Request Aggregation
Stores AI-clustered feature requests with frequency, importance, trend data.
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

from database.db import db


class AggregatedFeature(db.Model):
    __tablename__ = "aggregated_features"

    __table_args__ = (
        CheckConstraint(
            "importance IN ('Critical', 'High', 'Medium', 'Low')",
            name="chk_agg_importance",
        ),
        CheckConstraint(
            "dominant_sentiment IN ('Positive', 'Negative', 'Neutral', 'Mixed')",
            name="chk_agg_dominant_sentiment",
        ),
        CheckConstraint(
            "trend_direction IN ('rising', 'stable', 'declining')",
            name="chk_agg_trend_direction",
        ),
        CheckConstraint(
            "aggregation_status IN ('aggregated', 'failed')",
            name="chk_agg_status",
        ),
        CheckConstraint("frequency >= 1", name="chk_agg_frequency"),
        CheckConstraint("affected_users >= 0", name="chk_agg_affected_users"),
        CheckConstraint(
            "avg_sentiment_score >= -1.0 AND avg_sentiment_score <= 1.0",
            name="chk_agg_sentiment_score_range",
        ),
    )

    # ------------------------------------------------------------------
    # Primary Key
    # ------------------------------------------------------------------
    aggregate_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Project Association
    # ------------------------------------------------------------------
    project_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # ------------------------------------------------------------------
    # Cluster Identity (AI-generated)
    # ------------------------------------------------------------------
    cluster_label = Column(String(255), nullable=False)
    # e.g. "Dark Mode", "Export to PDF", "Multi-language Support"

    cluster_description = Column(Text, nullable=True)
    # AI-generated description of the feature cluster

    # ------------------------------------------------------------------
    # Aggregation Metrics
    # ------------------------------------------------------------------
    frequency = Column(Integer, nullable=False, default=1)
    # Total weighted count of requests in this cluster

    importance = Column(String(50), nullable=False, default="Medium")
    # Critical / High / Medium / Low — AI-derived from frequency + sentiment

    affected_users = Column(Integer, nullable=False, default=0)
    # Distinct user count in this cluster

    # ------------------------------------------------------------------
    # Sentiment Aggregation
    # ------------------------------------------------------------------
    avg_sentiment_score = Column(Float, nullable=False, default=0.0)
    # Average sentiment score across cluster members (-1.0 to 1.0)

    dominant_sentiment = Column(String(50), nullable=False, default="Neutral")
    # Most common sentiment in the cluster

    # ------------------------------------------------------------------
    # Extracted Data
    # ------------------------------------------------------------------
    representative_keywords = Column(ARRAY(Text), nullable=False, default=list)
    # Top keywords extracted across cluster members

    sample_feedback_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    # Up to 5 representative classified_feedback IDs

    member_classified_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    # All classified_feedback IDs in this cluster

    # ------------------------------------------------------------------
    # Trend Detection
    # ------------------------------------------------------------------
    trend_direction = Column(String(50), nullable=False, default="stable")
    # "rising" / "stable" / "declining"

    trend_details = Column(JSONB, nullable=False, default=dict)
    # Structure:
    # {
    #   "weekly_counts": [{"week": "2026-W28", "count": 15}, ...],
    #   "first_seen": "2026-06-01T...",
    #   "last_seen": "2026-07-19T...",
    #   "growth_rate": 0.15   (positive = rising, negative = declining)
    # }

    # ------------------------------------------------------------------
    # Aggregation Metadata
    # ------------------------------------------------------------------
    aggregation_metadata = Column(JSONB, nullable=False, default=dict)
    # Structure:
    # {
    #   "gemini_model": "gemini-2.0-flash",
    #   "prompt_version": "1.0.0",
    #   "aggregation_duration_ms": 1200,
    #   "total_feature_requests_analyzed": 200,
    #   "clusters_formed": 15,
    #   "token_usage": { ... }
    # }

    aggregation_status = Column(
        String(50), nullable=False, default="aggregated"
    )
    aggregation_error = Column(Text, nullable=True)

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    aggregated_at = Column(
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
    # Helpers
    # ------------------------------------------------------------------
    def to_dict(self):
        return {
            "aggregate_id": str(self.aggregate_id),
            "project_id": str(self.project_id),
            "cluster_label": self.cluster_label,
            "cluster_description": self.cluster_description,
            "frequency": self.frequency,
            "importance": self.importance,
            "affected_users": self.affected_users,
            "avg_sentiment_score": self.avg_sentiment_score,
            "dominant_sentiment": self.dominant_sentiment,
            "representative_keywords": self.representative_keywords or [],
            "sample_feedback_ids": [
                str(fid) for fid in (self.sample_feedback_ids or [])
            ],
            "member_classified_ids": [
                str(mid) for mid in (self.member_classified_ids or [])
            ],
            "trend_direction": self.trend_direction,
            "trend_details": self.trend_details or {},
            "aggregation_metadata": self.aggregation_metadata or {},
            "aggregation_status": self.aggregation_status,
            "aggregation_error": self.aggregation_error,
            "aggregated_at": (
                self.aggregated_at.isoformat() if self.aggregated_at else None
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
            "aggregate_id": str(self.aggregate_id),
            "cluster_label": self.cluster_label,
            "frequency": self.frequency,
            "importance": self.importance,
            "affected_users": self.affected_users,
            "trend_direction": self.trend_direction,
            "dominant_sentiment": self.dominant_sentiment,
            "representative_keywords": (self.representative_keywords or [])[:5],
            "aggregated_at": (
                self.aggregated_at.isoformat() if self.aggregated_at else None
            ),
        }

    def __repr__(self):
        return (
            f"<AggregatedFeature {self.aggregate_id} "
            f"label='{self.cluster_label}' freq={self.frequency}>"
        )
