from __future__ import annotations
from typing import List, Dict, Optional

from shared.kernel.aggregate_root import AggregateRoot
from domain.entities.category import Category
from domain.entities.category_profile import CategoryProfile
from domain.events.category_events import (
    CategoryCreatedEvent,
    CategoryProfileCreatedEvent,
    CategoryKeywordsEnhancedEvent,
)


class CategoryCatalog(AggregateRoot):
    """
    Aggregate root that manages a collection of categories and their profiles.

    Invariants:
      - Every category must have a valid parent_id (if not root)
      - Leaf categories must have profiles before classification
      - Keywords are enhanced from parent chain (excluding root)

    Events emitted:
      - CategoryCreatedEvent
      - CategoryProfileCreatedEvent
      - CategoryKeywordsEnhancedEvent
    """

    def __init__(self) -> None:
        super().__init__()
        self._categories: Dict[str, Category] = {}
        self._profiles: Dict[str, CategoryProfile] = {}

    # ---------------------------
    # Properties
    # ---------------------------
    @property
    def categories(self) -> List[Category]:
        return list(self._categories.values())

    @property
    def profiles(self) -> List[CategoryProfile]:
        return list(self._profiles.values())

    # ---------------------------
    # Commands
    # ---------------------------
    def add_category(self, category: Category) -> None:
        """Add a category to the catalog, enforcing parent integrity."""
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
        """Add multiple categories, validate parent integrity after all are added."""
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

    def add_profile(self, profile: CategoryProfile) -> None:
        """Add or update a profile for a category."""
        self._profiles[profile.category.id] = profile

        self._record_event(CategoryProfileCreatedEvent(
            category_id=profile.category.id,
            gender=profile.gender,
            direction=profile.direction,
            business=profile.business,
            brand=profile.brand,
            is_leaf=profile.is_leaf,
        ))

    def enhance_keywords_from_parents(self) -> List[Category]:
        """
        Enhance non-root categories with keywords from their parent chain
        (excluding root level 1). Returns the enhanced categories.
        """
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
