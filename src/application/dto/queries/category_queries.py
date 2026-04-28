# -----------------------------------------------------------------
# Application DTO — Queries — Category
# -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class GetCategoryTreeQuery:
    """Query to get a category tree."""
    root_category_id: Optional[str] = None


@dataclass(frozen=True)
class GetCategoriesByConstraintsQuery:
    """Query to find categories matching constraints."""
    gender: Optional[str] = None
    direction: Optional[str] = None
    brand: Optional[str] = None
    business: Optional[str] = None
    is_leaf: Optional[bool] = None
    limit: Optional[int] = None
