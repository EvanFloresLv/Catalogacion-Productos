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


@dataclass(frozen=True)
class CategoryMatch:
    category_id: str
    score: float


@dataclass(frozen=True)
class ClassificationResult:
    product_sku: str
    best: CategoryMatch
    top_k: list[CategoryMatch]