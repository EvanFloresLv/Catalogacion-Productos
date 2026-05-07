# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.product import Product

from domain.repositories.product_repository import ProductRepository
from domain.repositories.brand_repository import BrandRepository
from domain.repositories.embedding_repository import EmbeddingRepository

from domain.services.embedding_service import EmbeddingService

from application.services.category_query_service import CategoryQueryService
from application.dto.queries.category_queries import GetCategoriesByConstraintsQuery

from domain.entities.result import ClassificationResult, CategoryMatch
from domain.aggregates.product_classification_catalog import ProductClassification

from shared.kernel.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------
@dataclass(frozen=True)
class ClassifyProductCommand:
    product_sku: str
    top_k: int = 5


# ---------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------
class ClassifyProductUseCase:
    """Classifies a product against every eligible business line."""

    def __init__(
        self,
        products: ProductRepository,
        brands: BrandRepository,
        embeddings: EmbeddingRepository,
        category_query_service: CategoryQueryService,
        service: EmbeddingService,
        uow: UnitOfWork,
    ):
        self._products = products
        self._brands = brands
        self._embeddings = embeddings
        self._category_query_service = category_query_service
        self._embedding_service = service
        self._uow = uow

    # -----------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------
    def execute(self, cmd: ClassifyProductCommand) -> List[ClassificationResult]:
        try:
            return self._classify(cmd)
        except Exception:
            self._uow.rollback()
            logger.exception("Classification failed for SKU %s", cmd.product_sku)
            return []

    # -----------------------------------------------------------------
    # Core orchestration
    # -----------------------------------------------------------------
    def _classify(self, cmd: ClassifyProductCommand) -> List[ClassificationResult]:
        product = self._products.get_by_sku(cmd.product_sku)
        if not product:
            raise ValueError(f"Product with SKU {cmd.product_sku} not found.")

        classification = ProductClassification(product)
        self._uow.register(classification)

        query_vector = self._embedding_service.generate(product.to_embedding_text())
        businesses = self._resolve_businesses(product)

        results = {
            business: self._classify_for_business(
                classification, product, query_vector, business, cmd.top_k,
            )
            for business in businesses
        }

        if not results:
            raise ValueError(f"No eligible matches found for product {product.sku}")

        self._uow.commit()
        return results

    # -----------------------------------------------------------------
    # Business resolution
    # -----------------------------------------------------------------
    def _resolve_businesses(self, product: Product) -> set[str]:
        product_businesses = set(product.business)
        brand = self._brands.get_by_name(product.brand)

        if not brand:
            return product_businesses

        return product_businesses & set(brand.business)

    # -----------------------------------------------------------------
    # Single-business classification
    # -----------------------------------------------------------------
    def _classify_for_business(
        self,
        classification: ProductClassification,
        product,
        query_vector,
        business: str,
        top_k: int,
    ) -> ClassificationResult | None:

        category_ids = self._fetch_allowed_category_ids(product, business)

        if not category_ids:
            return None

        raw_results = self._embeddings.search_similar(
            query_vector=query_vector,
            category_ids=list(category_ids),
            limit=top_k,
        )
        if not raw_results:
            return None

        matches = self._build_category_matches(raw_results[:top_k])

        return classification.record_classification(
            business=business,
            top_k=matches,
        )

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    def _fetch_allowed_category_ids(self, product: Product, business: str) -> set[str]:

        brand = product.brand if "blp" in business else None
        gender = product.gender if product.gender in ("hombre", "mujer") else None

        query = GetCategoriesByConstraintsQuery(
            gender=gender,
            business=business,
            article_group=product.article_group,
            brand=brand if "blp" in business else None,
            is_leaf=True,
        )

        categories = self._category_query_service.get_categories_by_constraints(query)
        return {c.id for c in categories} if categories else set()

    def _build_category_matches(
        self, raw_results: list,
    ) -> list[CategoryMatch]:
        return [
            CategoryMatch(
                category_id=embedding.category_id,
                score=float(abs(score)),
                path=self._category_query_service.build_category_path(embedding.category_id),
            )
            for embedding, score in raw_results
        ]