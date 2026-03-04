# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Tuple, Iterable
import re
import unicodedata

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from .errors import CategoryNameError
from domain.value_objects.semantic_hash import SemanticHash


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _normalize_keywords(keywords: Iterable[str] | None) -> Tuple[str, ...]:
    if not keywords:
        return ()

    normalized = {
        _normalize_text(k).lower()
        for k in keywords
        if isinstance(k, str) and k.strip()
    }

    return tuple(sorted(normalized))


# ---------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Category:
    id: str
    parent_id: str | None

    name: str
    level: int
    description: str
    url: str | None
    keywords_json: Tuple[str, ...]

    brand: str | None
    direction: str | None
    business: str | None

    semantic_hash: str

    # -------------------------------------------------------------
    # Factory
    # -------------------------------------------------------------
    @staticmethod
    def create(
        id: str,
        name: str,
        level: int,
        description: str = "",
        keywords_json: Iterable[str] | None = None,
        url: str | None = None,
        brand: str | None = None,
        direction: str | None = None,
        business: str | None = None,
        parent_id: str | None = None,
    ) -> Category:

        id = _normalize_text(id)
        name = _normalize_text(name)
        description = _normalize_text(description)
        url = _normalize_text(url)
        brand = _normalize_text(brand)
        direction = _normalize_text(direction)
        business = _normalize_text(business)
        keywords_json = _normalize_keywords(keywords_json)

        # -------------------------
        # Domain validations
        # -------------------------
        if not id:
            raise CategoryNameError("Category ID cannot be empty.")

        if not name:
            raise CategoryNameError("Category name cannot be empty.")

        if level < 1:
            raise CategoryNameError("Category level must be >= 1.")

        if len(name) > 100:
            raise CategoryNameError(
                "Category name cannot exceed 100 characters."
            )

        if parent_id and parent_id == id:
            raise CategoryNameError(
                "Category cannot reference itself as parent."
            )

        # -------------------------
        # Semantic hash (deterministic)
        # -------------------------
        embedding_text = Category._build_embedding_text(
            name=name,
            description=description,
            keywords_json=keywords_json,
        )

        semantic_hash = SemanticHash.from_text(
            embedding_text
        ).value

        return Category(
            id=id,
            parent_id=parent_id,
            name=name,
            level=level,
            description=description,
            url=url,
            keywords_json=keywords_json,
            brand=brand,
            direction=direction,
            business=business,
            semantic_hash=semantic_hash,
        )

    # -------------------------------------------------------------
    # Internal text builder
    # -------------------------------------------------------------
    @staticmethod
    def _build_embedding_text(
        name: str,
        description: str,
        keywords_json: Tuple[str, ...],
    ) -> str:

        keywords_str = ", ".join(keywords_json)
        return (
            f"TÍTULO: {name}\n"
            f"DESCRIPCIÓN: {description}\n"
            f"PALABRAS CLAVE: {keywords_str}"
        )

    # -------------------------------------------------------------
    # Public behavior
    # -------------------------------------------------------------
    def to_embedding_text(self) -> str:
        return self._build_embedding_text(
            self.name,
            self.description,
            self.keywords_json,
        )


    def with_id(self, new_id: str) -> Category:
        return replace(self, id=_normalize_text(new_id))


    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "name": self.name,
            "level": self.level,
            "description": self.description,
            "url": self.url,
            "keywords_json": set(self.keywords_json),
            "brand": self.brand,
            "direction": self.direction,
            "business": self.business,
            "semantic_hash": self.semantic_hash,
        }