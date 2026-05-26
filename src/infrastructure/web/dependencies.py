# -----------------------------------------------------------------
# FastAPI Dependencies — Session & Use Case Injection
# -----------------------------------------------------------------
from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from infrastructure.persistence.postgresql.session import SessionLocal

from config.composition_root import (
    create_unit_of_work,
    create_category_query_service,
    create_embedding_repository,
    create_product_repository,
    create_load_categories_from_file_use_case,
    create_classify_batch_products_use_case,
)
from infrastructure.persistence.postgresql.repositories.brand_repository_pg import (
    BrandRepositoryPG,
)
from infrastructure.embeddings.gemini.client import EmbeddingClient

from application.use_cases.classification.classify_product import ClassifyProductUseCase
from application.use_cases.classification.classify_batch_products import ClassifyBatchProductsUseCase
from application.use_cases.categories.load_categories_from_file import LoadCategoriesFromFileUseCase
from application.use_cases.products.load_products_from_file import LoadProductsFromFileUseCase
from application.services.category_query_service import CategoryQueryService


# -----------------------------------------------------------------
# Session
# -----------------------------------------------------------------
def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# -----------------------------------------------------------------
# Use case factories (called per-request with a fresh session)
# -----------------------------------------------------------------
def get_classify_product_use_case(session: Session) -> ClassifyProductUseCase:
    uow = create_unit_of_work(session)
    return ClassifyProductUseCase(
        products=create_product_repository(session),
        brands=BrandRepositoryPG(session),
        embeddings=create_embedding_repository(session),
        category_query_service=create_category_query_service(session),
        service=EmbeddingClient(embedding_dim=768),
        uow=uow,
    )


def get_classify_batch_use_case(session: Session) -> ClassifyBatchProductsUseCase:
    return create_classify_batch_products_use_case(session)


def get_load_categories_use_case(session: Session) -> LoadCategoriesFromFileUseCase:
    return create_load_categories_from_file_use_case(session)


def get_load_products_use_case(session: Session) -> LoadProductsFromFileUseCase:
    uow = create_unit_of_work(session)
    return LoadProductsFromFileUseCase(
        repo=create_product_repository(session),
        uow=uow,
    )


def get_category_query_service(session: Session) -> CategoryQueryService:
    return create_category_query_service(session)
