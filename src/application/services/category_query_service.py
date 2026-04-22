# -----------------------------------------------------------------
# Application Service — Category Query Service (Read side — CQRS)
# -----------------------------------------------------------------
from __future__ import annotations

from typing import List, Optional, Dict, Any

from application.dto.queries.category_queries import (
    GetCategoryTreeQuery,
    GetProfilesByConstraintsQuery,
)
from domain.repositories.category_repository import CategoryRepository
from domain.repositories.category_profile_repository import CategoryProfileRepository
from domain.entities.category import Category
from domain.entities.category_profile import CategoryProfile


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
        profiles: CategoryProfileRepository,
    ):
        self._categories = categories
        self._profiles = profiles

    def get_category_tree(self, query: GetCategoryTreeQuery) -> List[Dict[str, Any]]:
        """
        Build a hierarchical tree structure for display.
        Returns lightweight dicts (not aggregates).
        """
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

    def get_profiles_by_constraints(
        self,
        query: GetProfilesByConstraintsQuery,
    ) -> List[CategoryProfile]:
        """
        Find profiles matching constraint criteria.
        Delegates to the read-optimized repository method.
        """
        return self._profiles.get_profiles_by_constraints(
            gender=query.gender,
            direction=query.direction,
            brand=query.brand,
            business=query.business,
            is_leaf=query.is_leaf,
            limit=query.limit,
        )

    def build_category_path(self, category_id: str) -> str:
        """
        Build hierarchical path from root to the given category.
        Returns "Root > Parent > Child > Leaf".
        """
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
