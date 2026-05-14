# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryMatch:
    category_id: str
    score: float
    path: str | None = None


@dataclass(frozen=True)
class ClassificationResult:
    product_sku: str
    best: CategoryMatch
    top_k: list[CategoryMatch]
    query: str