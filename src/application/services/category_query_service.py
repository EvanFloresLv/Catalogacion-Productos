# -----------------------------------------------------------------
# Application Service — Category Query Service (Read side — CQRS)
# -----------------------------------------------------------------
from __future__ import annotations

from typing import List, Optional, Dict, Any

from application.dto.queries.category_queries import (
    GetCategoryTreeQuery,
    GetCategoriesByConstraintsQuery,
)
from domain.repositories.category_repository import CategoryRepository
from domain.entities.category import Category


class CategoryQueryService:
    """
    Read-side query service for categories.

    Rules (CQRS):
      - Does NOT use aggregates
      - Can use optimized SQL queries / views
      - May be eventually consistent
    """

    def __init__(
        self,
        categories: CategoryRepository,
    ):
        self._categories = categories

    def get_by_id(self, category_id: str) -> Optional[Category]:
        return self._categories.get_by_id(category_id)

    def get_by_ids(self, category_ids: list[str]) -> list[Category]:
        return self._categories.get_by_ids(category_ids)


    def get_category_tree(self, query: GetCategoryTreeQuery) -> List[Dict[str, Any]]:
        all_cats = self._categories.get_all() if hasattr(self._categories, "get_all") else []

        cat_map = {c.id: c for c in all_cats}
        children_map: Dict[str, List[Category]] = {}

        for cat in all_cats:
            if cat.parent_id:
                children_map.setdefault(cat.parent_id, []).append(cat)

        roots = [c for c in all_cats if c.parent_id is None]

        if query.root_category_id:
            root = cat_map.get(query.root_category_id)
            roots = [root] if root else []

        def build_node(category: Category) -> Dict[str, Any]:
            return {
                "id": category.id,
                "name": category.name,
                "level": category.level,
                "keyword_count": len(category.keywords) if category.keywords else 0,
                "children": [
                    build_node(child)
                    for child in children_map.get(category.id, [])
                ],
            }

        return [build_node(r) for r in roots]


    def get_categories_by_constraints(
        self,
        query: GetCategoriesByConstraintsQuery,
    ) -> List[Category]:
        return self._categories.get_categories_by_constraints(
            gender=query.gender,
            direction=query.direction,             # Direction won't be used for this iteration
            business=query.business,
            brand=query.brand,
            is_leaf=query.is_leaf,
            limit=query.limit,
        )


    def build_category_path(self, category_id: str) -> str:
        path_parts = []
        current_id: Optional[str] = category_id
        max_depth = 10

        while current_id and max_depth > 0:
            category = self._categories.get_by_id(current_id)
            if not category:
                break
            path_parts.append(category.name)
            current_id = category.parent_id
            max_depth -= 1

        path_parts.reverse()
        return " > ".join(path_parts)


    def build_all_category_paths(self) -> Dict[str, str]:

        all_cats = self._categories.get_all() if hasattr(self._categories, "get_all") else []
        cat_map = {c.id: c for c in all_cats}
        paths = {}

        for cat in all_cats:

            if cat.id in paths:
                continue

            path_parts = []
            current_id: Optional[str] = cat.id
            visited = set()

            while current_id and current_id not in visited:
                category = cat_map.get(current_id)
                if not category:
                    break
                path_parts.append(category.name)
                visited.add(current_id)
                current_id = category.parent_id

            path_parts.reverse()
            paths[cat.id] = " > ".join(path_parts)

        return paths