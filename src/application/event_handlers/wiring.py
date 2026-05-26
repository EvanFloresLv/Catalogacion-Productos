# -----------------------------------------------------------------
# Application — Event Handler Wiring
# -----------------------------------------------------------------
"""
Registers all projection handlers with the event bus.

Call `wire_projections(bus, session_factory)` from the composition
root to connect domain events → read-model projections.
"""
from __future__ import annotations

from application.ports.event_bus import EventBus
from application.event_handlers.projections import (
    EventLogProjection,
    CategorySummaryProjection,
    EmbeddingStatsProjection,
)

# Domain events
from domain.events.category_events import (
    CategoryCreatedEvent,
    CategoryKeywordsEnhancedEvent,
)
from domain.events.product_events import ProductClassifiedEvent
from domain.events.embedding_events import EmbeddingGeneratedEvent


def wire_projections(bus: EventBus, session_factory) -> EventBus:
    """
    Subscribe all projection handlers to their domain events.

    Returns the bus so it can be used fluently.
    """

    # --- Event Log (catches ALL events) ---
    event_log = EventLogProjection(session_factory)
    for event_cls in (
        CategoryCreatedEvent,
        CategoryKeywordsEnhancedEvent,
        ProductClassifiedEvent,
        EmbeddingGeneratedEvent,
    ):
        bus.subscribe(event_cls, event_log.handle)

    # --- Category Summary ---
    cat_summary = CategorySummaryProjection(session_factory)
    bus.subscribe(CategoryCreatedEvent, cat_summary.on_category_created)
    # bus.subscribe(CategoryKeywordsEnhancedEvent, cat_summary.on_keywords_enhanced)
    bus.subscribe(EmbeddingGeneratedEvent, cat_summary.on_embedding_generated)

    # --- Embedding Stats ---
    emb_stats = EmbeddingStatsProjection(session_factory)
    bus.subscribe(EmbeddingGeneratedEvent, emb_stats.on_embedding_generated)

    return bus
