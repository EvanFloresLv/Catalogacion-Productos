# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

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
class ClassifyBatchProductsCommand:
    product_skus: tuple[str, ...]
    top_k: int = 5


# ---------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------
@dataclass(frozen=True)
class BatchClassificationResult:
    results: Dict[str, Dict[str, ClassificationResult | None]]
    failed: Dict[str, str]

    @property
    def succeeded_count(self) -> int:
        return len(self.results)

    @property
    def failed_count(self) -> int:
        return len(self.failed)

    @property
    def total(self) -> int:
        return self.succeeded_count + self.failed_count


# ---------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------
class ClassifyBatchProductsUseCase:
    """Classifies multiple products using the same logic as ClassifyProductUseCase."""

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
    def execute(self, cmd: ClassifyBatchProductsCommand) -> BatchClassificationResult:
        results: Dict[str, Dict[str, ClassificationResult | None]] = {}
        failed: Dict[str, str] = {}

        for sku in cmd.product_skus:
            try:
                classification = self._classify_single(sku, cmd.top_k)
                results[sku] = classification
            except Exception as e:
                logger.exception("Classification failed for SKU %s", sku)
                failed[sku] = str(e)

        try:
            self._uow.commit()
        except Exception:
            self._uow.rollback()
            logger.exception("Failed to commit batch classification")

        return BatchClassificationResult(results=results, failed=failed)

    # -----------------------------------------------------------------
    # Single product classification (mirrors ClassifyProductUseCase)
    # -----------------------------------------------------------------
    def _classify_single(
        self, sku: str, top_k: int,
    ) -> Dict[str, ClassificationResult | None]:

        product = self._products.get_by_sku(sku)
        if not product:
            raise ValueError(f"Product with SKU {sku} not found.")

        classification = ProductClassification(product)
        self._uow.register(classification)

        query_vector = self._embedding_service.generate(product.to_embedding_text())
        businesses = self._resolve_businesses(product)

        return {
            business: self._classify_for_business(
                classification, product, query_vector, business, top_k,
            )
            for business in businesses
        }

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
        product: Product,
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
    # Category fetching with fallback strategy
    # -----------------------------------------------------------------
    def _fetch_allowed_category_ids(self, product: Product, business: str) -> set[str]:
        brand = product.brand if "blp" in business else None
        gender = product.gender if product.gender in ("hombre", "mujer") else None

        # Strategy 1: Full constraints (article_group has highest priority)
        if product.article_group:
            categories = self._query_categories(
                article_group=list(product.article_group),
                business=business,
                gender=gender,
                brand=brand,
                is_leaf=True,
            )
            if categories:
                return categories

            # Strategy 2: Drop gender, keep article_group
            categories = self._query_categories(
                article_group=list(product.article_group),
                business=business,
                brand=brand,
                is_leaf=True,
            )
            if categories:
                return categories

        # Strategy 3: Drop article_group, use gender
        categories = self._query_categories(
            business=business,
            gender=gender,
            brand=brand,
            is_leaf=True,
        )
        if categories:
            return categories

        # Strategy 4: Broadest — just business + is_leaf
        return self._query_categories(
            business=business,
            brand=brand,
            is_leaf=True,
        )

    def _query_categories(self, **kwargs) -> set[str]:
        query = GetCategoriesByConstraintsQuery(**kwargs)
        categories = self._category_query_service.get_categories_by_constraints(query)
        return {c.id for c in categories} if categories else set()

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
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
