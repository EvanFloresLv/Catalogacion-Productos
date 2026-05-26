# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from typing import Any
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CategoryMatch:
    category_id: str
    score: float
    name: str | None = None
    path: str | None = None
    keywords: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "category_id": self.category_id,
            "name": self.name,
            "score": self.score,
            "path": self.path,
            "keywords": list(self.keywords),
        }


@dataclass(frozen=True)
class ClassificationResult:
    product_sku: str
    best: CategoryMatch
    top_k: list[CategoryMatch]
    query: str

    def to_dict(self) -> dict:
        return {
            "Results": [m.to_dict() for m in self.top_k],
        }


@dataclass
class ClassificationContext:
    brand_cache: dict[str, Any | None] = field(default_factory=dict)
    category_id_cache: dict[tuple, tuple[set[str], object | None]] = field(default_factory=dict)
    path_cache: dict[str, str] = field(default_factory=dict)
    category_entity_cache: dict[str, Any | None] = field(default_factory=dict)