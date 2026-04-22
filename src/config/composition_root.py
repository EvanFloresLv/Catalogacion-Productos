# -----------------------------------------------------------------
# Composition Root — Dependency Injection Factory
# -----------------------------------------------------------------
"""
Wires all dependencies together following Clean Architecture rules:

  Domain (inner) ← Application ← Infrastructure (outer) ← Interfaces

This module is the ONLY place that knows about concrete implementations.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from shared.kernel.unit_of_work import UnitOfWork

# Infrastructure — Repositories
from infrastructure.persistence.postgresql.repositories.category_repository_pg import (
    CategoryRepositoryPG,
)
from infrastructure.persistence.postgresql.repositories.category_profile_repository_pg import (
    CategoryProfileRepositoryPG,
)
from infrastructure.persistence.postgresql.repositories.embedding_repository_pg import (
    EmbeddingRepositoryPG,
)
from infrastructure.persistence.postgresql.repositories.product_repository_pg import (
    ProductRepositoryPG,
)

# Infrastructure — UoW + Outbox
from infrastructure.persistence.postgresql.unit_of_work import SqlAlchemyUnitOfWork
from infrastructure.persistence.postgresql.session import SessionLocal
from adapters.messaging.postgres_outbox_writer import PostgresOutboxWriter

# Infrastructure — External services
from infrastructure.embeddings.gemini.client import EmbeddingClient
from infrastructure.llm.gemini.client import LLMClient
from infrastructure.prompts import Prompt

# Application — Event handlers
from application.event_handlers.logging_handler import LoggingEventHandler
from application.event_handlers.event_bus_handler import EventBusHandler
from application.event_handlers.base import EventHandler

# Application — Event bus + projections
from adapters.messaging.in_process_event_bus import InProcessEventBus
from application.event_handlers.wiring import wire_projections

# Application — Query services
from application.services.category_query_service import CategoryQueryService

# Application — Use cases
from application.use_cases.categories.load_categories_from_file import (
    LoadCategoriesFromFileUseCase,
)
from application.use_cases.products.load_products import LoadProductsUseCase
from application.use_cases.classification.classify_product import ClassifyProductUseCase


# -----------------------------------------------------------------
# Repository factories
# -----------------------------------------------------------------
def create_category_repository(session: Session) -> CategoryRepositoryPG:
    return CategoryRepositoryPG(session)


def create_category_profile_repository(session: Session) -> CategoryProfileRepositoryPG:
    return CategoryProfileRepositoryPG(session)


def create_embedding_repository(
    session: Session,
    expected_dimension: int = 768,
) -> EmbeddingRepositoryPG:
    return EmbeddingRepositoryPG(session, expected_dimension=expected_dimension)


def create_product_repository(session: Session) -> ProductRepositoryPG:
    return ProductRepositoryPG(session)


# -----------------------------------------------------------------
# Event bus factory
# -----------------------------------------------------------------
def create_event_bus() -> InProcessEventBus:
    """Create an event bus with all projection handlers wired."""
    bus = InProcessEventBus()
    wire_projections(bus, SessionLocal)
    return bus


# -----------------------------------------------------------------
# UoW factory
# -----------------------------------------------------------------
def create_unit_of_work(
    session: Session,
    event_handlers: Optional[List[EventHandler]] = None,
) -> SqlAlchemyUnitOfWork:
    outbox = PostgresOutboxWriter(session)
    if event_handlers is None:
        bus = create_event_bus()
        event_handlers = [
            LoggingEventHandler(),
            EventBusHandler(bus),
        ]
    return SqlAlchemyUnitOfWork(
        session=session,
        outbox=outbox,
        event_handlers=event_handlers,
    )


# -----------------------------------------------------------------
# Query service factories
# -----------------------------------------------------------------
def create_category_query_service(session: Session) -> CategoryQueryService:
    return CategoryQueryService(
        categories=create_category_repository(session),
        profiles=create_category_profile_repository(session),
    )


# -----------------------------------------------------------------
# Use case factories
# -----------------------------------------------------------------
def create_load_categories_from_file_use_case(
    session: Session,
    uow: Optional[UnitOfWork] = None,
) -> LoadCategoriesFromFileUseCase:
    uow = uow or create_unit_of_work(session)
    return LoadCategoriesFromFileUseCase(
        category_repository=create_category_repository(session),
        profiles_repository=create_category_profile_repository(session),
        embedding_repository=create_embedding_repository(session),
        embedding_service=EmbeddingClient(embedding_dim=768),
        llm_service=LLMClient(),
        prompt_service=Prompt(),
        uow=uow,
    )


def create_create_product_use_case(
    session: Session,
    uow: Optional[UnitOfWork] = None,
) -> LoadProductsUseCase:
    uow = uow or create_unit_of_work(session)
    return LoadProductsUseCase(
        products=create_product_repository(session),
        uow=uow,
    )


def create_classify_product_use_case(
    session: Session,
    uow: Optional[UnitOfWork] = None,
) -> ClassifyProductUseCase:
    uow = uow or create_unit_of_work(session)
    return ClassifyProductUseCase(
        products=create_product_repository(session),
        category_query_service=create_category_query_service(session),
        embeddings=create_embedding_repository(session),
        embeddings_service=EmbeddingClient(embedding_dim=768),
        uow=uow,
    )
