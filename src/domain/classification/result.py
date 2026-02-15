# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class CategoryMatch:
    category_id: UUID
    score: float


@dataclass(frozen=True)
class ClassificationResult:
    product_id: UUID
    best: CategoryMatch
    matches: list[CategoryMatch]