# -----------------------------------------------------------------
# Infrastructure — Factory Methods
# -----------------------------------------------------------------
"""
Centralised factory for creating every Infrastructure-layer object:
ORM read-models, outbox rows, and event-bus instances.

Usage
-----
    from infrastructure.factories import InfrastructureFactory

    row = InfrastructureFactory.create_event_log_entry(event)
"""
from __future__ import annotations

import json

from shared.kernel.domain_event import DomainEvent

# ── ORM Write Models ─────────────────────────────────────────────
from infrastructure.persistence.postgresql.models.outbox_model import (
    OutboxModel,
)

# ── ORM Read Models ──────────────────────────────────────────────
from infrastructure.persistence.postgresql.models.read_models import (
    CategorySummaryReadModel,
    ProductClassificationReadModel,
    EventLogReadModel,
    EmbeddingStatsReadModel,
)

# ── Event Bus ────────────────────────────────────────────────────
from adapters.messaging.in_process_event_bus import InProcessEventBus
from application.ports.event_bus import EventBus
from application.event_handlers.wiring import wire_projections


class InfrastructureFactory:
    """Static factory methods for infrastructure-layer objects."""

    # =============================================================
    #  OUTBOX
    # =============================================================

    @staticmethod
    def create_outbox_entry(*, event: DomainEvent) -> OutboxModel:
        """Create an OutboxModel row from a domain event."""
        return OutboxModel(
            event_type=event.event_type,
            event_id=event.event_id,
            occurred_on=event.occurred_on,
            payload=json.dumps(event.to_dict(), default=str),
            processed=False,
        )

    # =============================================================
    #  READ MODELS
    # =============================================================

    # ── Category Summary ─────────────────────────────────────────
    @staticmethod
    def create_category_summary(
        *,
        category_id: str,
        name: str,
        level: int,
        parent_id: str | None = None,
        gender: str | None = None,
        direction: str | None = None,
        business: str | None = None,
        brand: str | None = None,
        is_leaf: bool | None = None,
        keyword_count: int = 0,
        has_embedding: bool = False,
    ) -> CategorySummaryReadModel:
        """Create a CategorySummaryReadModel row."""
        return CategorySummaryReadModel(
            category_id=category_id,
            name=name,
            level=level,
            parent_id=parent_id,
            gender=gender,
            direction=direction,
            business=business,
            brand=brand,
            is_leaf=is_leaf,
            keyword_count=keyword_count,
            has_embedding=has_embedding,
        )

    # ── Product Classification ───────────────────────────────────
    @staticmethod
    def create_product_classification_entry(
        *,
        sku: str,
        business: str,
        best_category_id: str,
        best_score: float,
        top_k_count: int,
    ) -> ProductClassificationReadModel:
        """Create a ProductClassificationReadModel row."""
        return ProductClassificationReadModel(
            sku=sku,
            business=business,
            best_category_id=best_category_id,
            best_score=best_score,
            top_k_count=top_k_count,
        )

    # ── Event Log ────────────────────────────────────────────────
    @staticmethod
    def create_event_log_entry(
        *, event: DomainEvent,
    ) -> EventLogReadModel:
        """Create an EventLogReadModel row from a domain event."""
        return EventLogReadModel(
            event_type=event.event_type,
            event_id=event.event_id,
            occurred_on=event.occurred_on,
            payload=json.dumps(event.to_dict(), default=str),
        )

    # ── Embedding Stats ──────────────────────────────────────────
    @staticmethod
    def create_embedding_stats_entry(
        *,
        category_id: str,
        dimension: int,
        content_hash: str,
    ) -> EmbeddingStatsReadModel:
        """Create an EmbeddingStatsReadModel row."""
        return EmbeddingStatsReadModel(
            category_id=category_id,
            dimension=dimension,
            content_hash=content_hash,
        )

    # =============================================================
    #  EVENT BUS
    # =============================================================

    @staticmethod
    def create_event_bus(*, session_factory=None) -> EventBus:
        """
        Create an InProcessEventBus, optionally wired with projections.

        Args:
            session_factory: SQLAlchemy session factory. When provided,
                             all projection handlers are auto-subscribed.
        """
        bus = InProcessEventBus()
        if session_factory is not None:
            wire_projections(bus, session_factory)
        return bus
