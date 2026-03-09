# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.categories.category import Category
from domain.entities.categories.category_constraints import CategoryConstraints


@dataclass(frozen=True)
class CategoryProfile:
    category: Category
    constraints: CategoryConstraints

    @classmethod
    def create(
        cls,
        category: Category,
        constraints: CategoryConstraints,
    ) -> CategoryProfile:

        if not isinstance(category, Category):
            raise TypeError("category must be a Category instance")

        if not isinstance(constraints, CategoryConstraints):
            raise TypeError("constraints must be CategoryConstraints")

        return cls(
            category=category,
            constraints=constraints,
        )