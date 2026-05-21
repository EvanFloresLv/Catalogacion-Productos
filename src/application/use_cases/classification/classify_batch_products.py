# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Callable, Optional

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

from application.use_cases.classification.enhance_classification import (
    EnhanceClassificationCommand,
    EnhanceClassificationUseCase
)

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
    enhance: bool = True        # Select categories with LLM model


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
    MAX_WORKERS = 4

    def __init__(
        self,
        products: ProductRepository,
        brands: BrandRepository,
        embeddings: EmbeddingRepository,
        category_query_service: CategoryQueryService,
        service: EmbeddingService,
        session_factory: Optional[Callable] = None,
        uow: UnitOfWork = None,
    ):
        self._products = products
        self._brands = brands
        self._embeddings = embeddings
        self._category_query_service = category_query_service
        self._embedding_service = service
        self._session_factory = session_factory
        self._uow = uow

        # Caches (per-execute lifecycle)
        self._brand_cache: Dict[str, object | None] = {}
        self._category_id_cache: Dict[tuple, tuple[set[str], GetCategoriesByConstraintsQuery | None]] = {}
        self._path_cache: Dict[str, str] = {}
        self._category_entity_cache: Dict[str, object | None] = {}

    # -----------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------
    def execute(self, cmd: ClassifyBatchProductsCommand) -> BatchClassificationResult:
        try:
            logger.info(f"Starting batch classification for {len(cmd.product_skus)} SKUs")

            self._brand_cache.clear()
            self._category_id_cache.clear()
            self._path_cache.clear()
            self._category_entity_cache.clear()

            # Phase 1: Load products + resolve businesses
            product_data, not_found = self._prepare_products(cmd.product_skus)

            # Phase 2: Generate embeddings in parallel (IO-bound)
            embeddings_map = self._generate_embeddings_parallel(product_data)

            # Phase 3: Prewarm category ID cache (sequential, shared session)
            self._prewarm_category_id_cache(product_data)

            # Phase 3.5: Prewarm all category paths in one pass (avoids N+1 tree walks)
            self._path_cache = self._category_query_service.build_all_category_paths()

            # Phase 4: Similarity search in parallel (thread-per-session)
            results, failed = self._classify_all(product_data, embeddings_map, cmd.top_k)

            # Phase 5 (Optional):
            if cmd.enhance:

                # Extract product classification results
                payload = self._result_to_payload(results, product_data)

                # Send payload to LLM for enhancement
                enhance_cmd = EnhanceClassificationCommand(data=payload)
                enhance_use_case = EnhanceClassificationUseCase()
                enhance_results = enhance_use_case.execute(enhance_cmd)

                # Reorder results based on LLM ranking
                enhanced_results: Dict[str, Dict[str, ClassificationResult | None]] = {}
                for enhancement in enhance_results:
                    sku = enhancement.get("product_sku")
                    business = enhancement.get("business")
                    best_id = enhancement.get("best_category_id")
                    ranked_ids = enhancement.get("ranked", [])

                    # Get original classification to access CategoryMatch objects
                    original = results.get(sku, {}).get(business)
                    if not original:
                        continue

                    # Build lookup from original top_k
                    match_by_id = {m.category_id: m for m in original.top_k}

                    # Reorder top_k based on LLM ranking
                    reordered = [match_by_id[cid] for cid in ranked_ids if cid in match_by_id]

                    best = match_by_id.get(best_id, reordered[0] if reordered else original.best)

                    enhanced_results.setdefault(sku, {})[business] = ClassificationResult(
                        product_sku=sku,
                        best=best,
                        top_k=reordered,
                        query=original.query,
                    )

                # Merge: enhanced overrides originals
                for sku, businesses in enhanced_results.items():
                    for biz, result in businesses.items():
                        results.setdefault(sku, {})[biz] = result

            for sku in not_found:
                failed[sku] = f"Product with SKU {sku} not found"

            self._uow.commit()
            logger.info(f"Batch done: {len(results)} succeeded, {len(failed)} failed.")
            return BatchClassificationResult(results=results, failed=failed)

        except Exception as e:
            logger.exception("Batch classification failed")
            self._uow.rollback()
            return BatchClassificationResult(
                results={},
                failed={sku: str(e) for sku in cmd.product_skus},
            )

    def _result_to_payload(self, results: dict, products: dict) -> list[dict]:
        payload = []

        for sku, businesses in results.items():
            product_data = products.get(sku)
            if not product_data or not product_data.get("product"):
                continue

            product_dict = product_data["product"].to_dict()
            classifications = []

            for business, classification in businesses.items():
                if classification:
                    classifications.append({
                        "business": business,
                        "results": classification.to_dict(),
                    })
                else:
                    classifications.append({
                        "business": business,
                        "results": None,
                    })

            payload.append({
                "product": product_dict,
                "classifications": classifications,
            })

        return payload

    # -----------------------------------------------------------------
    # Phase 1: Prepare
    # -----------------------------------------------------------------
    def _prepare_products(self, skus: tuple[str, ...]) -> tuple[dict, list[str]]:
        products = self._products.get_by_skus(list(skus))
        products_by_sku = {p.sku: p for p in products}

        not_found = [sku for sku in skus if sku not in products_by_sku]
        if not_found:
            logger.warning(f"{len(not_found)} SKUs not found: {not_found[:10]}...")

        # Pre-warm brand cache
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

    # -----------------------------------------------------------------
    # Phase 2: Embeddings (parallel, IO-bound)
    # -----------------------------------------------------------------
    def _generate_embeddings_parallel(self, product_data: dict) -> dict:
        texts = {sku: d["embedding_text"] for sku, d in product_data.items()}
        if not texts:
            return {}

        skus = list(texts.keys())
        text_list = [texts[sku] for sku in skus]

        all_vectors = []
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = [
                executor.submit(self._embedding_service.generate_batch, text_list[i:i + self.BATCH_SIZE])
                for i in range(0, len(text_list), self.BATCH_SIZE)
            ]
            for future in futures:
                all_vectors.extend(future.result())

        return dict(zip(skus, all_vectors))

    # -----------------------------------------------------------------
    # Phase 3: Prewarm category cache
    # -----------------------------------------------------------------
    def _prewarm_category_id_cache(self, product_data: dict) -> None:
        unique_keys: set[tuple] = set()
        for data in product_data.values():
            product = data["product"]
            for business in data["businesses"]:
                unique_keys.add(self._cache_key(product, business))

        for key in unique_keys:
            if key not in self._category_id_cache:
                article_group, business, gender, brand = key
                self._category_id_cache[key] = self._fetch_category_ids(
                    article_group, business, gender, brand
                )

        logger.info(f"Category ID cache warmed: {len(self._category_id_cache)} combos")

    # -----------------------------------------------------------------
    # Phase 4: Classify (parallel similarity search)
    # -----------------------------------------------------------------
    def _classify_all(
        self,
        product_data: dict,
        embeddings_map: dict,
        top_k: int,
    ) -> tuple[Dict[str, Dict[str, ClassificationResult | None]], Dict[str, str]]:

        results: Dict[str, Dict[str, ClassificationResult | None]] = {}
        failed: Dict[str, str] = {}

        # Build work items
        work_items: list[tuple[str, str, list, Product]] = []
        for sku, data in product_data.items():
            vector = embeddings_map.get(sku)
            if vector is None:
                failed[sku] = "No embedding generated"
                continue
            for business in data["businesses"]:
                work_items.append((sku, business, vector, data["product"]))

        if not work_items:
            return results, failed

        # Similarity search — in-memory repo is thread-safe, run in parallel
        search_results = self._parallel_search(work_items, top_k)

        # Process results (sequential — mutates domain aggregates)
        for sku, business, raw_results, error in search_results:
            if error:
                failed.setdefault(sku, error)
                continue

            results.setdefault(sku, {})

            if not raw_results:
                results[sku][business] = None
                continue

            data = product_data[sku]
            matches = self._build_category_matches(raw_results[:top_k])
            _, query = self._category_id_cache.get(
                self._cache_key(data["product"], business), (set(), None)
            )

            result = data["classification"].record_classification(
                business=business,
                top_k=matches,
                query=str(query) if query else "",
            )
            results[sku][business] = result

        return results, failed

    def _parallel_search(self, work_items: list, top_k: int) -> list[tuple]:
        batch_size = max(1, len(work_items) // self.MAX_WORKERS)
        batches = [
            work_items[i:i + batch_size]
            for i in range(0, len(work_items), batch_size)
        ]

        all_results = []
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            futures = [executor.submit(self._search_worker, batch, top_k) for batch in batches]
            for future in futures:
                all_results.extend(future.result())

        return all_results

    def _sequential_search(self, work_items: list, top_k: int) -> list[tuple]:
        results = []
        for sku, business, vector, product in work_items:
            try:
                category_ids = self._get_category_ids(product, business)
                if not category_ids:
                    results.append((sku, business, None, None))
                    continue
                raw = self._embeddings.search_similar(
                    query_vector=vector, category_ids=list(category_ids), limit=top_k
                )
                results.append((sku, business, raw, None))
            except Exception as e:
                results.append((sku, business, None, str(e)))
        return results

    def _search_worker(self, items: list, top_k: int) -> list[tuple]:
        """Thread-safe: in-memory repo uses read-only NumPy ops."""
        results = []
        for sku, business, vector, product in items:
            try:
                category_ids = self._get_category_ids(product, business)
                if not category_ids:
                    results.append((sku, business, None, None))
                    continue
                raw = self._embeddings.search_similar(
                    query_vector=vector, category_ids=list(category_ids), limit=top_k
                )
                results.append((sku, business, raw, None))
            except Exception as e:
                results.append((sku, business, None, str(e)))
        return results

    # -----------------------------------------------------------------
    # Business resolution
    # -----------------------------------------------------------------
    def _resolve_businesses(self, product: Product) -> set[str]:
        product_businesses = set(product.business)
        brand = self._brand_cache.get(product.brand)

        if brand is None:
            return product_businesses

        normalized = set()
        for b in brand.business:
            if b.startswith("blp_"):
                normalized.add(f"{b[4:]}-blp")
            else:
                normalized.add(b)

        intersection = product_businesses & normalized
        return intersection if intersection else product_businesses

    # -----------------------------------------------------------------
    # Category lookup (with fallback strategies)
    # -----------------------------------------------------------------
    def _cache_key(self, product: Product, business: str) -> tuple:
        brand = product.brand if "blp" in business else None
        gender = product.gender if product.gender in ("hombre", "mujer") else None
        article_group = tuple(sorted(product.article_group)) if product.article_group else None
        return (article_group, business, gender, brand)

    def _get_category_ids(self, product: Product, business: str) -> set[str]:
        cached = self._category_id_cache.get(self._cache_key(product, business))
        if cached is None:
            return set()
        ids, _ = cached
        return ids

    def _fetch_category_ids(
        self,
        article_group: tuple | None,
        business: str,
        gender: str | None,
        brand: str | None,
    ) -> tuple[set[str], GetCategoriesByConstraintsQuery | None]:

        # Strategy 1: Full constraints
        if article_group:
            ids, q = self._query_categories(
                article_group=list(article_group), business=business,
                gender=gender, brand=brand, is_leaf=True,
            )
            if ids:
                return ids, q

            # Strategy 2: Drop gender
            ids, q = self._query_categories(
                article_group=list(article_group), business=business,
                brand=brand, is_leaf=True,
            )
            if ids:
                return ids, q

        # Strategy 3: Drop article_group
        ids, q = self._query_categories(
            business=business, gender=gender, brand=brand, is_leaf=True,
        )
        if ids:
            return ids, q

        # Strategy 4: Broadest
        return self._query_categories(business=business, brand=brand, is_leaf=True)

    def _query_categories(self, **kwargs) -> tuple[set[str], GetCategoriesByConstraintsQuery]:
        query = GetCategoriesByConstraintsQuery(**kwargs)
        categories = self._category_query_service.get_categories_by_constraints(query)
        ids = {c.id for c in categories} if categories else set()
        return ids, query

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    def _build_category_matches(self, raw_results: list) -> list[CategoryMatch]:
        # Batch-load all category entities in one query (eliminates N+1)
        cat_ids = [emb.category_id for emb, _ in raw_results]
        uncached_ids = [cid for cid in cat_ids if cid not in self._category_entity_cache]
        if uncached_ids:
            cats = self._category_query_service.get_by_ids(uncached_ids)
            for cat in cats:
                self._category_entity_cache[cat.id] = cat
            # Mark missing as None
            for cid in uncached_ids:
                self._category_entity_cache.setdefault(cid, None)

        matches = []
        for embedding, score in raw_results:
            cat = self._category_entity_cache.get(embedding.category_id)
            matches.append(CategoryMatch(
                category_id=embedding.category_id,
                score=float(abs(score)),
                name=cat.name if cat else None,
                path=self._get_category_path(embedding.category_id),
                keywords=cat.keywords if cat else (),
            ))
        return matches

    def _get_category_path(self, category_id: str) -> str:
        if category_id not in self._path_cache:
            self._path_cache[category_id] = (
                self._category_query_service.build_category_path(category_id)
            )
        return self._path_cache[category_id]
