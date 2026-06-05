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
from utils.business import intersect_businesses

logging.basicConfig(level=logging.INFO)
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
            logger.info(f"Classifying product with SKU: {cmd.product_sku}")
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

        if not businesses:
            logger.warning(
                f"No eligible businesses for product {product.sku} "
                f"(brand={product.brand}, product_type={product.product_type}, "
                f"business={product.business})"
            )
            # Fallback: use all product businesses without brand filtering
            businesses = set(product.business)

        results = {
            business: self._classify_for_business(
                classification, product, query_vector, business, cmd.top_k,
            )
            for business in businesses
        }

        if not any(results.values()):
            raise ValueError(
                f"No eligible matches found for product {product.sku} "
                f"(tried businesses: {businesses})"
            )

        self._uow.commit()
        return results

    # -----------------------------------------------------------------
    # Business resolution
    # -----------------------------------------------------------------
    def _resolve_businesses(self, product: Product) -> set[str]:
        brand = self._brands.get_by_name(product.brand)

        if not brand:
            return set(product.business)

        return intersect_businesses(product.business, brand.business)

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

        category_ids, query = self._fetch_allowed_category_ids(product, business)

        if not category_ids:
            logger.warning(f"No allowed categories found for product SKU {product.sku} in business {business} with query {query}")
            return None

        raw_results = self._embeddings.search_similar(
            query_vector=query_vector,
            category_ids=list(category_ids),
            limit=top_k,
        )

        if not raw_results:
            logger.warning(f"No similar embeddings found for product SKU {product.sku} in business {business}")
            return None

        matches = self._build_category_matches(raw_results[:top_k])

        return classification.record_classification(
            business=business,
            top_k=matches,
            query=str(query),
        )

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    def _fetch_allowed_category_ids(self, product: Product, business: str) -> tuple[set[str], GetCategoriesByConstraintsQuery | None]:
        brand = product.brand if "blp" in business else None
        gender = product.gender if product.gender in ("hombre", "mujer", "unisex") else None

        # Single multi-strategy SQL: returns ALL candidate IDs ranked by
        # the most specific strategy that produced them. Saves up to 3
        # DB round-trips per business per product.
        rows = self._category_query_service.get_categories_by_cascade(
            business=business,
            brand=brand,
            gender=gender,
            article_group=list(product.article_group) if product.article_group else None,
            is_leaf=True,
        )

        if rows:
            ids = {cat.id for _, cat in rows}
            first_priority, _ = rows[0]
            query = self._build_query_for_priority(
                priority=first_priority,
                product=product,
                business=business,
                gender=gender,
                brand=brand,
            )
            return ids, query

        # Final fallback (matches the old behavior for the no-candidates case)
        return self._query_categories(
            business=business,
            brand=brand,
            is_leaf=True,
        )

        if rows:
            ids = {cat.id for _, cat in rows}
            first_priority, _ = rows[0]
            query = self._build_query_for_priority(
                priority=first_priority,
                product=product,
                business=business,
                gender=gender,
                brand=brand,
            )
            return ids, query

        # Final fallback (matches the old behavior for the no-candidates case)
        return self._query_categories(
            business=business,
            brand=brand,
            is_leaf=True,
        )

    @staticmethod
    def _build_query_for_priority(
        *,
        priority: int,
        product: Product,
        business: str,
        gender: str | None,
        brand: str | None,
    ) -> GetCategoriesByConstraintsQuery:
        if priority == 1:
            return GetCategoriesByConstraintsQuery(
                article_group=list(product.article_group) if product.article_group else None,
                business=business,
                gender=gender,
                brand=brand,
                is_leaf=True,
            )
        if priority == 2:
            return GetCategoriesByConstraintsQuery(
                article_group=list(product.article_group) if product.article_group else None,
                business=business,
                brand=brand,
                is_leaf=True,
            )
        if priority == 3:
            return GetCategoriesByConstraintsQuery(
                business=business,
                gender=gender,
                brand=brand,
                is_leaf=True,
            )
        if priority == 4:
            return GetCategoriesByConstraintsQuery(
                business=business,
                brand=brand,
                is_leaf=True,
            )
        return GetCategoriesByConstraintsQuery(
            business=business,
            is_leaf=True,
        )

    def _query_categories(self, **kwargs) -> tuple[set[str], GetCategoriesByConstraintsQuery]:
        query = GetCategoriesByConstraintsQuery(**kwargs)
        categories = self._category_query_service.get_categories_by_constraints(query)
        ids = {c.id for c in categories} if categories else set()
        return ids, query

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