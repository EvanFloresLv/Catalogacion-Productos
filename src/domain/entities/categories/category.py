# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, field, fields, replace, asdict
from typing import Tuple, Iterable, Any
import re
import unicodedata

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from .errors import CategoryNameError
from domain.value_objects.semantic_hash import SemanticHash


# -------------------------------------------------------------
# Helpers
# -------------------------------------------------------------
def _normalize_text(value: str | None) -> str:
    if value is None:
        return value

    value = unicodedata.normalize("NFKD", str(value))
    value = re.sub(r"\s+", " ", value)
    value = value.strip()

    return value or None


def _normalize_keywords(values: Iterable[str] | None) -> Tuple[str, ...]:
    if not values:
        return ()  # Return empty tuple instead of None

    normalized = {
        _normalize_text(v).lower()
        for v in values
        if isinstance(v, str) and v.strip()
    }

    return tuple(sorted(normalized)) if normalized else ()

# -------------------------------------------------------------
# Entity
# -------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Category:

    # ---------------------------------------------------------
    # Required fields
    # ---------------------------------------------------------
    id: str
    name: str
    level: int
    semantic_hash: str

    # ---------------------------------------------------------
    # Optional fields
    # ---------------------------------------------------------
    parent_id: str | None = None
    description: str | None = None
    url: str | None = None
    brand: str | None = None
    direction: str | None = None
    business: str | None = None

    # ---------------------------------------------------------
    # Structured fields
    # ---------------------------------------------------------
    keywords_json: Tuple[str, ...] = field(default_factory=tuple)

    # ---------------------------------------------------------
    # Factory
    # ---------------------------------------------------------
    @classmethod
    def create(cls, **data: Any) -> Category:
        """
        Flexible factory:
        - Auto-maps dataclass fields
        - Rejects unknown fields
        - Normalizes consistently
        - Computes semantic_hash internally
        """

        field_names = {f.name for f in fields(cls)}
        allowed_input_fields = field_names - {"semantic_hash"}

        # -----------------------------
        # Guard against unknown fields
        # -----------------------------
        unknown = set(data.keys()) - allowed_input_fields
        if unknown:
            raise CategoryNameError(
                f"Unknown fields for Category: {unknown}"
            )

        normalized: dict[str, Any] = {}

        for field_name in allowed_input_fields:
            value = data.get(field_name)

            if field_name == "keywords_json":
                normalized[field_name] = _normalize_keywords(value)
            elif isinstance(value, str) or value is None:
                normalized[field_name] = _normalize_text(value)
            else:
                normalized[field_name] = value

        normalized["semantic_hash"] = SemanticHash.from_text(
            cls._build_embedding_text(
                name=normalized["name"],
                description=normalized.get("description", ""),
                keywords=normalized.get("keywords_json", ()),
            )
        ).value

        # -----------------------------
        # Validation
        # -----------------------------
        cls._validate(normalized)
        return cls(**normalized)

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------
    @staticmethod
    def _validate(data: dict[str, Any]) -> None:

        if not data.get("id"):
            raise CategoryNameError("Category ID cannot be empty.")

        if not data.get("name"):
            raise CategoryNameError("Category name cannot be empty.")

        level = data.get("level")
        if not isinstance(level, int) or level < 1:
            raise CategoryNameError(
                "Category level must be a positive integer."
            )

        if len(data["name"]) > 100:
            raise CategoryNameError(
                "Category name cannot exceed 100 characters."
            )

        if data.get("parent_id") == data.get("id"):
            raise CategoryNameError(
                "Category cannot reference itself as parent."
            )

    # ---------------------------------------------------------
    # Embedding text builder
    # ---------------------------------------------------------
    @staticmethod
    def _build_embedding_text(
        name: str,
        description: str,
        keywords: Tuple[str, ...],
    ) -> str:
        return (
            f"TÍTULO: {name}\n"
            f"DESCRIPCIÓN: {description}\n"
            f"PALABRAS CLAVE: {', '.join(keywords)}"
        )

    # ---------------------------------------------------------
    # Public behavior
    # ---------------------------------------------------------
    def to_embedding_text(self) -> str:
        return self._build_embedding_text(
            self.name,
            self.description or "",
            self.keywords_json or (),
        )


    def with_id(self, new_id: str) -> Category:
        return replace(self, id=_normalize_text(new_id))


    def to_dict(self) -> dict:
        return asdict(self)