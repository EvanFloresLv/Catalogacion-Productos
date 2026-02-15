# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.categories.category import Category
from domain.classification.category_constraints import CategoryConstraints


@dataclass(frozen=True)
class CategoryProfile:
    category: Category
    constraints: CategoryConstraints