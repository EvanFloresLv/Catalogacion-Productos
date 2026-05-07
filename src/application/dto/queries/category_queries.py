# -----------------------------------------------------------------
# Application DTO — Queries — Category
# -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

@dataclass(frozen=True)
class GetCategoryTreeQuery:
    root_category_id: Optional[str] = None


@dataclass(frozen=True)
class GetCategoriesByConstraintsQuery:
    article_group: Optional[List[str]] = None
    gender: Optional[str] = None
    brand: Optional[str] = None
    direction: Optional[str] = None
    business: Optional[str] = None
    is_leaf: Optional[bool] = None
    limit: Optional[int] = None
