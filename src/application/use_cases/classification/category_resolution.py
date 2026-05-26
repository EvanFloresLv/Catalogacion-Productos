# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.product import Product
from application.dto.queries.category_queries import GetCategoriesByConstraintsQuery
from domain.entities.result import ClassificationContext


class CategoryResolutionService:

    def __init__(self, category_query_service):
        self._category_query_service = category_query_service


    def cache_key(self, product: Product, business: str) -> tuple:
        brand = product.brand if "blp" in business else None
        gender = product.gender if product.gender in ("hombre", "mujer") else None
        article_group = tuple(sorted(product.article_group)) if product.article_group else None

        return article_group, business, gender, brand


    def prewarm_category_cache(
        self,
        context: ClassificationContext,
        product_data: dict,
    ) -> None:

        unique_keys: set[tuple] = set()

        for data in product_data.values():
            product = data["product"]

            for business in data["businesses"]:
                unique_keys.add(self.cache_key(product, business))

        for key in unique_keys:
            if key not in context.category_id_cache:
                article_group, business, gender, brand = key

                context.category_id_cache[key] = self._fetch_category_ids(
                    article_group=article_group,
                    business=business,
                    gender=gender,
                    brand=brand,
                )


    def get_category_ids(
        self,
        context: ClassificationContext,
        product: Product,
        business: str,
    ) -> set[str]:

        cached = context.category_id_cache.get(
            self.cache_key(product, business)
        )

        if cached is None:
            return set()

        ids, _ = cached
        return ids


    def get_query(
        self,
        context: ClassificationContext,
        product: Product,
        business: str,
    ):
        cached = context.category_id_cache.get(
            self.cache_key(product, business)
        )

        if cached is None:
            return None

        _, query = cached
        return query


    def get_category_path(
        self,
        context: ClassificationContext,
        category_id: str,
    ) -> str:

        if category_id not in context.path_cache:
            context.path_cache[category_id] = (
                self._category_query_service.build_category_path(category_id)
            )

        return context.path_cache[category_id]


    def _fetch_category_ids(
        self,
        article_group: tuple | None,
        business: str,
        gender: str | None,
        brand: str | None,
    ):

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

            ids, query = self._query_categories(
                article_group=list(article_group),
                business=business,
                brand=brand,
                is_leaf=True,
            )

            if ids:
                return ids, query

        ids, query = self._query_categories(
            business=business,
            gender=gender,
            brand=brand,
            is_leaf=True,
        )

        if ids:
            return ids, query

        return self._query_categories(
            business=business,
            brand=brand,
            is_leaf=True,
        )


    def _query_categories(self, **kwargs):
        query = GetCategoriesByConstraintsQuery(**kwargs)

        categories = self._category_query_service.get_categories_by_constraints(query)

        ids = {c.id for c in categories} if categories else set()

        return ids, query