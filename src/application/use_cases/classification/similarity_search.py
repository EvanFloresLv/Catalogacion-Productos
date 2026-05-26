# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import math
from concurrent.futures import ThreadPoolExecutor

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.result import CategoryMatch
from domain.entities.result import ClassificationContext


class SimilaritySearchService:

    def __init__(
        self,
        embeddings_repository,
        category_query_service,
        category_resolution_service,
        max_workers: int = 4,
    ):
        self._embeddings = embeddings_repository
        self._category_query_service = category_query_service
        self._category_resolution_service = category_resolution_service
        self._max_workers = max_workers


    def classify(
        self,
        context: ClassificationContext,
        product_data: dict,
        embeddings_map: dict,
        top_k: int,
    ):

        results = {}
        failed = {}

        work_items = []

        for sku, data in product_data.items():
            vector = embeddings_map.get(sku)

            if vector is None:
                failed[sku] = "No embedding generated"
                continue

            for business in data["businesses"]:
                work_items.append((sku, business, vector, data["product"]))

        search_results = self._parallel_search(context, work_items, top_k)

        for sku, business, raw_results, error in search_results:

            if error:
                failed[sku] = error
                continue

            results.setdefault(sku, {})

            if not raw_results:
                results[sku][business] = None
                continue

            data = product_data[sku]

            matches = self._build_category_matches(
                context=context,
                raw_results=raw_results[:top_k],
            )

            query = self._category_resolution_service.get_query(
                context=context,
                product=data["product"],
                business=business,
            )

            classification = data["classification"].record_classification(
                business=business,
                top_k=matches,
                query=str(query) if query else "",
            )

            results[sku][business] = classification

        return results, failed


    def _parallel_search(self, context, work_items, top_k):

        # Use ceil to ensure even distribution across workers
        batch_size = max(1, math.ceil(len(work_items) / self._max_workers))

        batches = [
            work_items[i:i + batch_size]
            for i in range(0, len(work_items), batch_size)
        ]

        all_results = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = [
                executor.submit(self._search_worker, context, batch, top_k)
                for batch in batches
            ]

            for future in futures:
                all_results.extend(future.result())

        return all_results


    def _search_worker(self, context, items, top_k):

        results = []

        for sku, business, vector, product in items:

            try:
                category_ids = self._category_resolution_service.get_category_ids(
                    context=context,
                    product=product,
                    business=business,
                )

                if not category_ids:
                    results.append((sku, business, None, None))
                    continue

                raw = self._embeddings.search_similar(
                    query_vector=vector,
                    category_ids=list(category_ids),
                    limit=top_k,
                )

                results.append((sku, business, raw, None))

            except Exception as exc:
                results.append((sku, business, None, str(exc)))

        return results


    def _build_category_matches(self, context, raw_results):

        category_ids = [emb.category_id for emb, _ in raw_results]

        uncached_ids = [
            category_id
            for category_id in category_ids
            if category_id not in context.category_entity_cache
        ]

        if uncached_ids:
            categories = self._category_query_service.get_by_ids(uncached_ids)

            for category in categories:
                context.category_entity_cache[category.id] = category

            for category_id in uncached_ids:
                context.category_entity_cache.setdefault(category_id, None)

        matches = []

        for embedding, score in raw_results:

            category = context.category_entity_cache.get(embedding.category_id)

            matches.append(
                CategoryMatch(
                    category_id=embedding.category_id,
                    score=float(abs(score)),
                    name=category.name if category else None,
                    path=self._category_resolution_service.get_category_path(
                        context=context,
                        category_id=embedding.category_id,
                    ),
                    keywords=category.keywords if category else (),
                )
            )

        return matches