from __future__ import annotations
from typing import List, Dict, Optional

from shared.kernel.aggregate_root import AggregateRoot
from domain.entities.category import Category
from domain.events.category_events import (
    CategoryCreatedEvent,
    CategoryKeywordsEnhancedEvent,
)


class CategoryCatalog(AggregateRoot):
    """
    Aggregate root that manages a collection of categories.

    Invariants:
      - Every category must have a valid parent_id (if not root)
      - Keywords are enhanced from parent chain (excluding root)

    Events emitted:
      - CategoryCreatedEvent
      - CategoryKeywordsEnhancedEvent
    """

    def __init__(self) -> None:
        super().__init__()
        self._categories: Dict[str, Category] = {}

    # ---------------------------
    # Properties
    # ---------------------------
    @property
    def categories(self) -> List[Category]:
        return list(self._categories.values())

    # ---------------------------
    # Commands
    # ---------------------------
    def add_category(self, category: Category) -> None:

        if category.parent_id and category.parent_id not in self._categories:
            # Allow if parent will be added later (batch scenarios)
            pass

        self._categories[category.id] = category

        self._record_event(CategoryCreatedEvent(
            category_id=category.id,
            name=category.name,
            level=category.level,
            parent_id=category.parent_id,
        ))

    def add_categories_batch(self, categories: List[Category]) -> None:

        for cat in categories:
            self._categories[cat.id] = cat

        # Validate parent integrity
        self._validate_parent_integrity()

        # Record events
        for cat in categories:
            self._record_event(CategoryCreatedEvent(
                category_id=cat.id,
                name=cat.name,
                level=cat.level,
                parent_id=cat.parent_id,
            ))

    def enhance_keywords_from_parents(self) -> List[Category]:
        enhanced = []

        for cat in self._categories.values():
            if cat.level == 1:
                enhanced.append(cat)
                continue

            all_keywords = set(cat.keywords) if cat.keywords else set()
            original_count = len(all_keywords)

            parent_keywords = self._collect_parent_keywords(cat.parent_id)
            all_keywords.update(parent_keywords)

            if len(all_keywords) > original_count:

                new_cat = Category.create(
                    id=cat.id,
                    name=cat.name,
                    level=cat.level,
                    parent_id=cat.parent_id,
                    description=cat.description,
                    keywords=tuple(sorted(all_keywords)),
                    gender=cat.gender,
                    direction=cat.direction,
                    brand=cat.brand,
                    is_leaf=cat.is_leaf,
                    group_articles=cat.group_articles,
                    business=cat.business,
                )

                self._categories[cat.id] = new_cat
                enhanced.append(new_cat)

                self._record_event(CategoryKeywordsEnhancedEvent(
                    category_id=cat.id,
                    original_keyword_count=original_count,
                    enhanced_keyword_count=len(all_keywords),
                ))
            else:
                enhanced.append(cat)

        return enhanced

    # ---------------------------
    # Queries on the aggregate
    # ---------------------------
    def get_category(self, category_id: str) -> Optional[Category]:
        return self._categories.get(category_id)

    # ---------------------------
    # Private — Invariant checks
    # ---------------------------
    def _validate_parent_integrity(self) -> None:
        for cat in self._categories.values():
            if cat.parent_id and cat.parent_id not in self._categories:
                raise ValueError(
                    f"Missing parent {cat.parent_id} for category {cat.id}"
                )

    def _collect_parent_keywords(self, parent_id: Optional[str]) -> set:
        keywords = set()
        if not parent_id or parent_id not in self._categories:
            return keywords

        parent = self._categories[parent_id]
        if parent.level == 1:
            return keywords

        if parent.keywords:
            keywords.update(parent.keywords)

        keywords.update(self._collect_parent_keywords(parent.parent_id))
        return keywords
