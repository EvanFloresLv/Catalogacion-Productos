# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import logging
import time

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.result import ClassificationContext
from application.dto.classification.dto import (
    BatchClassificationResult,
    ClassifyBatchProductsCommand,
)

from .embedding_pipeline import EmbeddingPipeline
from .category_resolution import CategoryResolutionService
from .similarity_search import SimilaritySearchService
from .enhancement_service import EnhancementService

from domain.aggregates.product_classification_catalog import ProductClassification


logger = logging.getLogger(__name__)


class ClassifyBatchProductsUseCase:

    MAX_PRODUCTS_PER_BATCH = 100
    MAX_WORKERS = 4

    def __init__(
        self,
        products,
        brands,
        embeddings,
        embedding_service,
        category_query_service,
        uow,
    ):
        self._products_repository = products
        self._brands_repository = brands
        self._embeddings_repository = embeddings

        self._query_service = category_query_service
        self._category_resolution_service = CategoryResolutionService(category_query_service)
        self._similarity_search_service = SimilaritySearchService(
            embeddings_repository=embeddings,
            category_query_service=category_query_service,
            category_resolution_service=self._category_resolution_service,
            max_workers=self.MAX_WORKERS,
        )

        self._uow = uow

        self._embedding_pipeline = EmbeddingPipeline(
            embedding_service=embedding_service,
            max_workers=self.MAX_WORKERS,
        )

        self._enhancement_service = EnhancementService()

    def execute(
        self,
        cmd: ClassifyBatchProductsCommand,
    ) -> BatchClassificationResult:

        try:
            start_time = time.time()
            logger.info("Processing batch: %d SKUs (enhance=%s)", len(cmd.product_skus), cmd.enhance)

            logger.info(
                "Starting batch classification for %s SKUs",
                len(cmd.product_skus),
            )

            results = {}
            failed = {}
            context = ClassificationContext()

            cache_start = time.time()
            shared_path_cache = self._query_service.build_all_category_paths()

            logger.info(
                "Shared path cache built: %d paths in %.2fs",
                len(shared_path_cache),
                time.time() - cache_start,
            )

            # Phase 1: Prepare products (thread-local session)
            prep_start = time.time()
            product_data, not_found = self._prepare_products(
                cmd.product_skus, self._products_repository, self._brands_repository,
            )
            logger.info("Prepare phase: %.2fs (%d products loaded)", time.time() - prep_start, len(product_data))

            # Phase 2: Generate embeddings
            embed_start = time.time()
            embeddings_map = self._embedding_pipeline.generate(product_data)
            logger.info("Embedding phase: %.2fs (%d embeddings)", time.time() - embed_start, len(embeddings_map))

            # Phase 3: Category resolution (use shared path cache)
            cache_start = time.time()
            context.path_cache = shared_path_cache

            self._category_resolution_service.prewarm_category_cache(
                context=context,
                product_data=product_data,
            )

            # Phase 4: Similarity search
            search_start = time.time()
            results, failed = self._similarity_search_service.classify(
                context=context,
                product_data=product_data,
                embeddings_map=embeddings_map,
                top_k=cmd.top_k,
            )
            logger.info("Search phase: %.2fs", time.time() - search_start)

            # Phase 5: Enhancement (optional)
            if cmd.enhance:
                enhance_start = time.time()
                enhanced = self._enhancement_service.enhance(
                    results=results,
                    product_data=product_data,
                )

                for sku, businesses in enhanced.items():
                    results.setdefault(sku, {}).update(businesses)

                logger.info("Enhancement phase: %.2fs (%d enhanced)",
                            time.time() - enhance_start, len(enhanced))

            for sku in not_found:
                failed[sku] = f"Product with SKU {sku} not found"

            total_time = time.time() - start_time
            logger.info(
                "Process complete: %d products, %.2fs (%.2f prod/s)",
                len(cmd.product_skus),
                total_time,
                len(cmd.product_skus) / total_time if total_time > 0 else 0,
            )

            return BatchClassificationResult(
                results=results,
                failed=failed,
            )

        except Exception as exc:
            logger.error("Error occurred during batch classification: %s", exc)
            return BatchClassificationResult(
                results={},
                failed={**{sku: str(exc) for sku in cmd.product_skus}},
            )

    def _prepare_products(self, product_skus, products_repo, brands_repo):

        products = products_repo.get_by_skus(list(product_skus))

        products_by_sku = {
            product.sku: product
            for product in products
        }

        not_found = [
            sku
            for sku in product_skus
            if sku not in products_by_sku
        ]

        brands_cache = {}

        for product in products:

            if product.brand and product.brand not in brands_cache:
                brands_cache[product.brand] = (
                    brands_repo.get_by_name(product.brand)
                )

        product_data = {}

        for product in products:

            classification = ProductClassification(product)

            businesses = self._resolve_businesses(
                product=product,
                brands_cache=brands_cache,
            )

            product_data[product.sku] = {
                "product": product,
                "classification": classification,
                "businesses": businesses,
                "embedding_text": product.to_embedding_text(),
            }

        return product_data, not_found

    def _resolve_businesses(self, product, brands_cache):

        product_businesses = set(product.business)

        brand = brands_cache.get(product.brand)

        if brand is None:
            return product_businesses

        normalized = set()

        for business in brand.business:

            if business.startswith("blp_"):
                normalized.add(f"{business[4:]}-blp")
            else:
                normalized.add(business)

        intersection = product_businesses & normalized

        return intersection if intersection else product_businesses