# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

from concurrent.futures import ThreadPoolExecutor

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

logging.basicConfig(level=logging.INFO)
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

    BATCH_SIZE = 50

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

        # Caches (per-execute lifecycle)
        self._brand_cache: Dict[str, object | None] = {}
        self._category_id_cache: Dict[tuple, set[str]] = {}
        self._path_cache: Dict[str, str] = {}

    # -----------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------
    def execute(self, cmd: ClassifyBatchProductsCommand) -> BatchClassificationResult:
        try:
            logger.info(f"Starting batch classification for {len(cmd.product_skus)} SKUs")

            # Clear caches for this execution
            self._brand_cache.clear()
            self._category_id_cache.clear()
            self._path_cache.clear()

            # Phase 1: Load all products in a single query + resolve businesses
            product_data, not_found = self._prepare_products(cmd.product_skus)

            # Phase 2: Generate all embeddings in parallel (IO-bound)
            embeddings_map = self._generate_embeddings_parallel(product_data)

            # Phase 3: Classify all products (DB-bound, with caching)
            results, failed = self._classify_all(
                product_data, embeddings_map, cmd.top_k
            )

            # Add not-found SKUs to failed
            for sku in not_found:
                failed[sku] = f"Product with SKU {sku} not found"

            self._uow.commit()

            logger.info(f"Batch classification completed: {len(results)} succeeded, {len(failed)} failed.")

            return BatchClassificationResult(results=results, failed=failed)

        except Exception as e:
            logger.exception("Batch classification failed")
            self._uow.rollback()
            return BatchClassificationResult(
                results={},
                failed={sku: str(e) for sku in cmd.product_skus}
            )


    def _prepare_products(self, skus: tuple[str, ...]) -> tuple[dict, list[str]]:
        products = self._products.get_by_skus(list(skus))
        products_by_sku = {p.sku: p for p in products}

        not_found = [sku for sku in skus if sku not in products_by_sku]
        if not_found:
            logger.warning(f"{len(not_found)} SKUs not found: {not_found[:10]}...")

        # Pre-warm brand cache for all unique brands in one pass
        unique_brands = {p.brand for p in products if p.brand}
        for brand_name in unique_brands:
            if brand_name not in self._brand_cache:
                self._brand_cache[brand_name] = self._brands.get_by_name(brand_name)

        product_data = {}
        for product in products:
            classification = ProductClassification(product)
            self._uow.register(classification)
            businesses = self._resolve_businesses(product)

            product_data[product.sku] = {
                "product": product,
                "classification": classification,
                "businesses": businesses,
                "embedding_text": product.to_embedding_text(),
            }

        return product_data, not_found


    def _generate_embeddings_parallel(self, product_data: dict) -> dict:
        texts = {
            sku: data["embedding_text"]
            for sku, data in product_data.items()
        }

        if not texts:
            return {}

        skus = list(texts.keys())
        text_list = [texts[sku] for sku in skus]

        all_vectors = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for i in range(0, len(text_list), self.BATCH_SIZE):
                batch = text_list[i:i + self.BATCH_SIZE]
                futures.append(executor.submit(self._embedding_service.generate_batch, batch))

            for future in futures:
                all_vectors.extend(future.result())

        return dict(zip(skus, all_vectors))


    def _classify_all(
        self,
        product_data: dict,
        embeddings_map: dict,
        top_k: int,
    ) -> tuple[Dict[str, Dict[str, ClassificationResult | None]], Dict[str, str]]:

        results: Dict[str, Dict[str, ClassificationResult | None]] = {}
        failed: Dict[str, str] = {}

        for sku, data in product_data.items():
            try:
                query_vector = embeddings_map.get(sku)

                if query_vector is None:
                    failed[sku] = "No embedding generated"
                    continue

                classification_result = {}

                for business in data["businesses"]:
                    classification_result[business] = self._classify_for_business(
                        data["classification"],
                        data["product"],
                        query_vector,
                        business,
                        top_k,
                    )

                results[sku] = classification_result

            except Exception as e:
                logger.exception("Classification failed for SKU %s", sku)
                failed[sku] = str(e)

        return results, failed

    # -----------------------------------------------------------------
    # Business resolution
    # -----------------------------------------------------------------
    def _resolve_businesses(self, product: Product) -> set[str]:
        product_businesses = set(product.business)
        brand = self._brand_cache.get(product.brand)

        if brand is None:
            return product_businesses

        # Normalize brand business names to canonical format
        # DB may store "blp_liverpool" but we use "liverpool-blp"
        normalized_brand_businesses = set()
        for b in brand.business:
            if b.startswith("blp_"):
                normalized_brand_businesses.add(f"{b[4:]}-blp")
            else:
                normalized_brand_businesses.add(b)

        return product_businesses & normalized_brand_businesses

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

        category_ids, query = self._fetch_allowed_category_ids(product, business)

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
            query=str(query),
        )


    def _fetch_allowed_category_ids(self, product: Product, business: str) -> tuple[set[str], GetCategoriesByConstraintsQuery | None]:
        brand = product.brand if "blp" in business else None
        gender = product.gender if product.gender in ("hombre", "mujer") else None
        article_group = tuple(sorted(product.article_group)) if product.article_group else None

        # Build a cache key from constraints
        cache_key = (article_group, business, gender, brand)
        if cache_key in self._category_id_cache:
            return self._category_id_cache[cache_key]

        result = self._fetch_allowed_category_ids_uncached(
            article_group, business, gender, brand
        )
        self._category_id_cache[cache_key] = result
        return result


    def _fetch_allowed_category_ids_uncached(
        self,
        article_group: tuple | None,
        business: str,
        gender: str | None,
        brand: str | None,
    ) -> tuple[set[str], GetCategoriesByConstraintsQuery | None]:

        # Strategy 1: Full constraints (article_group has highest priority)
        if article_group:
            ids, query = self._query_categories(
                article_group=list(article_group),
                business=business,
                gender=gender,
                brand=brand,
                is_leaf=True,
            )
            if ids:
                return ids, query

            # Strategy 2: Drop gender, keep article_group
            ids, query = self._query_categories(
                article_group=list(article_group),
                business=business,
                brand=brand,
                is_leaf=True,
            )
            if ids:
                return ids, query

        # Strategy 3: Drop article_group, use gender
        ids, query = self._query_categories(
            business=business,
            gender=gender,
            brand=brand,
            is_leaf=True,
        )
        if ids:
            return ids, query

        # Strategy 4: Broadest — just business + is_leaf
        return self._query_categories(
            business=business,
            brand=brand,
            is_leaf=True,
        )

    def _query_categories(self, **kwargs) -> tuple[set[str], GetCategoriesByConstraintsQuery]:
        query = GetCategoriesByConstraintsQuery(**kwargs)
        categories = self._category_query_service.get_categories_by_constraints(query)
        ids = {c.id for c in categories} if categories else set()
        return ids, query

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
                path=self._get_category_path(embedding.category_id),
            )
            for embedding, score in raw_results
        ]

    def _get_category_path(self, category_id: str) -> str:
        if category_id not in self._path_cache:
            self._path_cache[category_id] = (
                self._category_query_service.build_category_path(category_id)
            )
        return self._path_cache[category_id]
