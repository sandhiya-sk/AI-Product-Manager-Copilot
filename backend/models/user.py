"""
models/user.py — SQLAlchemy model for the users table
Mirrors schema.md: Table 1 — users
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.db import db


class User(db.Model):
    __tablename__ = "users"

    # ------------------------------------------------------------------
    # Primary Key
    # ------------------------------------------------------------------
    user_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)

    # ------------------------------------------------------------------
    # Role — enforced via CHECK in DB and application layer
    # ------------------------------------------------------------------
    role = Column(String(50), nullable=False)
    # Valid values: 'product_manager' | 'customer'

    # ------------------------------------------------------------------
    # Project association (optional)
    # ------------------------------------------------------------------
    project_id = Column(UUID(as_uuid=True), nullable=True)

    # ------------------------------------------------------------------
    # Account lifecycle
    # ------------------------------------------------------------------
    is_active = Column(Boolean, nullable=False, default=True)

    # ------------------------------------------------------------------
    # Audit timestamps (UTC)
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
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    raw_feedbacks = relationship(
        "RawFeedback",
        back_populates="user",
        lazy="dynamic",
        foreign_keys="RawFeedback.user_id",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def to_dict(self):
        """Serialise to a safe public-facing dict (no password_hash)."""
        return {
            "user_id": str(self.user_id),
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "project_id": str(self.project_id) if self.project_id else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": (
                self.last_login_at.isoformat() if self.last_login_at else None
            ),
        }

    def __repr__(self):
        return f"<User {self.email} [{self.role}]>"
