# -----------------------------------------------------------------
# Infrastructure ORM — Read Models
# -----------------------------------------------------------------
"""
Denormalized read-model tables updated by projection handlers.

These tables provide fast, query-optimized views of the data.
They are eventually consistent with the write model — updated
asynchronously through domain events.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    Text,
    Boolean,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.postgresql.base import Base


# -----------------------------------------------------------------
# 1. Category Summary — flat denormalized view of a category
# -----------------------------------------------------------------
class CategorySummaryReadModel(Base):
    """
    Denormalized view combining category + profile + embedding stats.
    Updated by CategoryCreatedEvent and CategoryProfileCreatedEvent.
    """
    __tablename__ = "rm_category_summary"

    category_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # From profile
    gender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(50), nullable=True)
    business: Mapped[str | None] = mapped_column(String(50), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_leaf: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Stats
    keyword_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_embedding: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_rm_cat_summary_direction", "direction"),
        Index("ix_rm_cat_summary_business", "business"),
        Index("ix_rm_cat_summary_level", "level"),
    )


# -----------------------------------------------------------------
# 2. Product Classification Log — audit trail of classifications
# -----------------------------------------------------------------
class ProductClassificationReadModel(Base):
    """
    Read-model log of every product classification event.
    Updated by ProductClassifiedEvent.
    """
    __tablename__ = "rm_product_classification"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    sku: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    business: Mapped[str] = mapped_column(String(50), nullable=False)
    best_category_id: Mapped[str] = mapped_column(String(36), nullable=False)
    best_score: Mapped[float] = mapped_column(Float, nullable=False)
    top_k_count: Mapped[int] = mapped_column(Integer, nullable=False)

    classified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_rm_prod_class_sku", "sku"),
        Index("ix_rm_prod_class_category", "best_category_id"),
    )


# -----------------------------------------------------------------
# 3. Event Log — queryable log of all domain events
# -----------------------------------------------------------------
class EventLogReadModel(Base):
    """
    Permanent read-model log of every domain event.
    Serves as an audit / debugging table.
    Updated by ALL events.
    """
    __tablename__ = "rm_event_log"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    event_type: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True,
    )
    event_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True,
    )
    occurred_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    payload: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("ix_rm_event_log_type", "event_type"),
        Index("ix_rm_event_log_occurred", "occurred_on"),
    )


# -----------------------------------------------------------------
# 4. Embedding Stats — tracks embedding generation per category
# -----------------------------------------------------------------
class EmbeddingStatsReadModel(Base):
    """
    Read-model tracking embedding generation per category.
    Updated by EmbeddingGeneratedEvent.
    """
    __tablename__ = "rm_embedding_stats"

    category_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, nullable=False,
    )
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_rm_emb_stats_category", "category_id"),
    )
