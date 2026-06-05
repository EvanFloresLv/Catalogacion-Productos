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
from config.settings import classification_settings

from .embedding_pipeline import EmbeddingPipeline
from .category_resolution import CategoryResolutionService
from .similarity_search import SimilaritySearchService
from .enhancement_service import EnhancementService

from domain.aggregates.product_classification_catalog import ProductClassification
from utils.business import intersect_businesses


logger = logging.getLogger(__name__)


class ClassifyBatchProductsUseCase:

    MAX_PRODUCTS_PER_BATCH = classification_settings.max_products_per_batch
    MAX_WORKERS = classification_settings.search_max_workers

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
            max_workers=classification_settings.search_max_workers,
        )

        self._uow = uow

        self._embedding_pipeline = EmbeddingPipeline(
            embedding_service=embedding_service,
            batch_size=classification_settings.embedding_batch_size,
            max_workers=classification_settings.embedding_max_workers,
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

            # Resolve thresholds once.
            self._enhance_threshold = (
                cmd.enhance_threshold
                if cmd.enhance_threshold is not None
                else classification_settings.enhance_threshold
            )
            self._min_confidence = (
                cmd.min_confidence
                if cmd.min_confidence is not None
                else classification_settings.min_confidence
            )

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

            if not product_data:
                logger.warning("No products found for SKUs: %s", cmd.product_skus)
                for sku in cmd.product_skus:
                    failed[sku] = f"Product with SKU {sku} not found"
                return BatchClassificationResult(results={}, failed=failed)

            # Phase 2: Generate embeddings
            embed_start = time.time()
            embeddings_map = self._embedding_pipeline.generate(product_data)
            logger.info("Embedding phase: %.2fs (%d embeddings)", time.time() - embed_start, len(embeddings_map))

            if not embeddings_map:
                logger.warning("No embeddings generated for any product")

            logger.info("Pre-search state: %d products, %d embeddings",
                        len(product_data), len(embeddings_map))

            # Phase 3: Category resolution (use shared path cache)
            cache_start = time.time()
            context.path_cache = shared_path_cache

            self._category_resolution_service.prewarm_category_cache(
                context=context,
                product_data=product_data,
            )

            # Phase 4: Similarity search
            search_start = time.time()
            logger.info(
                "Starting similarity search for %d products",
                len(product_data),
            )
            results, failed = self._similarity_search_service.classify(
                context=context,
                product_data=product_data,
                embeddings_map=embeddings_map,
                top_k=cmd.top_k,
            )
            logger.info("Search phase: %.2fs", time.time() - search_start)

            # Phase 5: Enhancement (optional). Skip the LLM re-rank for
            # products whose top1 cosine is above the configured
            # threshold — the embedding match is already confident.
            if cmd.enhance and self._enhance_threshold > 0.0:
                to_enhance = {
                    sku: businesses
                    for sku, businesses in results.items()
                    if any(
                        biz_res is not None
                        and biz_res.top_k
                        and biz_res.top_k[0].score < self._enhance_threshold
                        for biz_res in businesses.values()
                    )
                }

                if to_enhance:
                    enhance_start = time.time()
                    enhanced = self._enhancement_service.enhance(
                        results=to_enhance,
                        product_data=product_data,
                    )

                    for sku, businesses in enhanced.items():
                        results.setdefault(sku, {}).update(businesses)

                    logger.info(
                        "Enhancement phase: %.2fs (%d/%d enhanced, threshold=%.2f)",
                        time.time() - enhance_start,
                        len(enhanced),
                        len(results),
                        self._enhance_threshold,
                    )
                else:
                    logger.info(
                        "Enhancement skipped: all %d products above threshold %.2f",
                        len(results),
                        self._enhance_threshold,
                    )

            # Phase 6: Reject results whose score < min_confidence
            if self._min_confidence > 0.0:
                rejected = 0
                for sku, businesses in results.items():
                    for business, classification in list(businesses.items()):
                        if classification is None or not classification.top_k:
                            continue
                        if classification.top_k[0].score < self._min_confidence:
                            businesses[business] = None
                            rejected += 1
                if rejected:
                    logger.info(
                        "Confidence phase: %d business results below min_confidence=%.2f (set to None)",
                        rejected,
                        self._min_confidence,
                    )

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
            self._uow.rollback()
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

        brand = brands_cache.get(product.brand)

        if brand is None:
            return set(product.business)

        return intersect_businesses(product.business, brand.business)