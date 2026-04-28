from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from shared.kernel.domain_event import DomainEvent

# Domain events
from domain.events.category_events import (
    CategoryCreatedEvent,
    CategoryKeywordsEnhancedEvent,
)
from domain.events.product_events import (
    ProductClassifiedEvent,
)
from domain.events.embedding_events import EmbeddingGeneratedEvent

# Read models
from infrastructure.persistence.postgresql.models.read_models import (
    CategorySummaryReadModel,
    ProductClassificationReadModel,
    EventLogReadModel,
    EmbeddingStatsReadModel,
)

logger = logging.getLogger(__name__)


# =================================================================
# Base projection
# =================================================================
class Projection:
    """
    Base class for projections.
    Each projection receives a session factory so it can open
    a dedicated short-lived session for each event.
    """

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def _get_session(self) -> Session:
        return self._session_factory()


# =================================================================
# 1. Event Log Projection — logs every event into rm_event_log
# =================================================================
class EventLogProjection(Projection):
    """Persists every domain event into the rm_event_log table."""

    def handle(self, event: DomainEvent) -> None:
        session = self._get_session()
        try:
            row = EventLogReadModel(
                event_type=event.event_type,
                event_id=event.event_id,
                occurred_on=event.occurred_on,
                payload=json.dumps(event.to_dict(), default=str),
            )
            session.add(row)
            session.commit()
            logger.info(
                "[Projection:EventLog] ✓ Persisted %s (id=%s)",
                event.event_type,
                event.event_id,
            )
        except Exception as exc:
            session.rollback()
            logger.error(
                "[Projection:EventLog] ✗ Failed for %s: %s",
                event.event_type,
                exc,
            )
        finally:
            session.close()


# =================================================================
# 2. Category Summary Projection
# =================================================================
class CategorySummaryProjection(Projection):
    """
    Builds / updates the rm_category_summary read model.

    Handles:
      - CategoryCreatedEvent            → inserts a new summary row
      - CategoryKeywordsEnhancedEvent   → updates keyword_count
      - EmbeddingGeneratedEvent         → marks has_embedding = True
    """

    def on_category_created(self, event: CategoryCreatedEvent) -> None:
        session = self._get_session()
        try:
            existing = (
                session.query(CategorySummaryReadModel)
                .filter_by(category_id=event.category_id)
                .first()
            )
            if existing:
                existing.name = event.name
                existing.level = event.level
                existing.parent_id = event.parent_id
                existing.updated_at = datetime.now(timezone.utc)
            else:
                row = CategorySummaryReadModel(
                    category_id=event.category_id,
                    name=event.name,
                    level=event.level,
                    parent_id=event.parent_id,
                )
                session.add(row)
            session.commit()
            logger.info(
                "[Projection:CategorySummary] ✓ CategoryCreated %s",
                event.category_id,
            )
        except Exception as exc:
            session.rollback()
            logger.error(
                "[Projection:CategorySummary] ✗ CategoryCreated failed: %s",
                exc,
            )
        finally:
            session.close()

    def on_keywords_enhanced(self, event: CategoryKeywordsEnhancedEvent) -> None:
        session = self._get_session()
        try:
            row = (
                session.query(CategorySummaryReadModel)
                .filter_by(category_id=event.category_id)
                .first()
            )
            if row:
                row.keyword_count = event.enhanced_keyword_count
                row.updated_at = datetime.now(timezone.utc)
                session.commit()
                logger.info(
                    "[Projection:CategorySummary] ✓ KeywordsEnhanced %s (%d→%d)",
                    event.category_id,
                    event.original_keyword_count,
                    event.enhanced_keyword_count,
                )
            else:
                session.commit()
                logger.warning(
                    "[Projection:CategorySummary] Category %s not found for keywords update",
                    event.category_id,
                )
        except Exception as exc:
            session.rollback()
            logger.error(
                "[Projection:CategorySummary] ✗ KeywordsEnhanced failed: %s",
                exc,
            )
        finally:
            session.close()

    def on_embedding_generated(self, event: EmbeddingGeneratedEvent) -> None:
        session = self._get_session()
        try:
            row = (
                session.query(CategorySummaryReadModel)
                .filter_by(category_id=event.category_id)
                .first()
            )
            if row:
                row.has_embedding = True
                row.updated_at = datetime.now(timezone.utc)
                session.commit()
                logger.info(
                    "[Projection:CategorySummary] ✓ EmbeddingGenerated %s",
                    event.category_id,
                )
            else:
                session.commit()
                logger.warning(
                    "[Projection:CategorySummary] Category %s not found for embedding update",
                    event.category_id,
                )
        except Exception as exc:
            session.rollback()
            logger.error(
                "[Projection:CategorySummary] ✗ EmbeddingGenerated failed: %s",
                exc,
            )
        finally:
            session.close()


# =================================================================
# 3. Product Classification Projection
# =================================================================
class ProductClassificationProjection(Projection):
    """
    Appends a row to rm_product_classification on each classification.

    Handles:
      - ProductClassifiedEvent
    """

    def on_product_classified(self, event: ProductClassifiedEvent) -> None:
        session = self._get_session()
        try:
            row = ProductClassificationReadModel(
                sku=event.sku,
                business=event.business,
                best_category_id=event.best_category_id,
                best_score=event.best_score,
                top_k_count=event.top_k_count,
            )
            session.add(row)
            session.commit()
            logger.info(
                "[Projection:ProductClassification] ✓ %s → %s (%.4f)",
                event.sku,
                event.best_category_id,
                event.best_score,
            )
        except Exception as exc:
            session.rollback()
            logger.error(
                "[Projection:ProductClassification] ✗ Failed for %s: %s",
                event.sku,
                exc,
            )
        finally:
            session.close()


# =================================================================
# 4. Embedding Stats Projection
# =================================================================
class EmbeddingStatsProjection(Projection):
    """
    Upserts into rm_embedding_stats on each embedding generation.

    Handles:
      - EmbeddingGeneratedEvent
    """

    def on_embedding_generated(self, event: EmbeddingGeneratedEvent) -> None:
        session = self._get_session()
        try:
            existing = (
                session.query(EmbeddingStatsReadModel)
                .filter_by(category_id=event.category_id)
                .first()
            )
            if existing:
                existing.dimension = event.dimension
                existing.content_hash = event.content_hash
                existing.generated_at = datetime.now(timezone.utc)
            else:
                row = EmbeddingStatsReadModel(
                    category_id=event.category_id,
                    dimension=event.dimension,
                    content_hash=event.content_hash,
                )
                session.add(row)
            session.commit()
            logger.info(
                "[Projection:EmbeddingStats] ✓ %s dim=%d",
                event.category_id,
                event.dimension,
            )
        except Exception as exc:
            session.rollback()
            logger.error(
                "[Projection:EmbeddingStats] ✗ Failed for %s: %s",
                event.category_id,
                exc,
            )
        finally:
            session.close()
