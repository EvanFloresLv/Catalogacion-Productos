# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.categories.category import Category
from domain.entities.categories.errors import CategoryNameError


@dataclass(frozen=True)
class CategoryProfile:
    """
    Category profile with constraint fields for product matching.
    """

    category: Category

    # Constraint fields
    gender: str | None = None
    direction: str | None = None
    brand: str | None = None
    business: str | None = None
    is_leaf: bool | None = None

    @classmethod
    def create(cls, **data) -> CategoryProfile:
        """
        Flexible factory:
        - Auto-maps dataclass fields
        - Rejects unknown fields
        - Normalizes consistently
        """

        field_map = {f.name: f for f in fields(cls)}

        # -----------------------------
        # Guard against unknown fields
        # -----------------------------
        unknown = set(data) - set(field_map)
        if unknown:
            raise CategoryNameError(f"Unknown fields: {unknown}")

        # -----------------------------
        # Required field validation
        # -----------------------------
        category = data.get("category")
        if category is None:
            raise CategoryNameError("category is required")
        if not isinstance(category, Category):
            raise TypeError("category must be a Category instance")

        # -----------------------------
        # Normalize dynamically
        # -----------------------------
        normalized_data: dict[str, Any] = {}

        for name, field_def in field_map.items():
            value = data.get(name)

            if name == "category":
                # Category field - no normalization
                normalized_data[name] = value
            elif name == "is_leaf":
                # Boolean field
                normalized_data[name] = cls._normalize_bool(value)
            else:
                # String fields
                normalized_data[name] = cls._normalize_str(value)

        return cls(**normalized_data)

    # -----------------------------------------------------------------
    # Normalizers
    # -----------------------------------------------------------------

    @staticmethod
    def _normalize_str(value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {type(value).__name__}")
        value = value.strip()
        return value.lower() if value else None

    @staticmethod
    def _normalize_bool(value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            v = value.strip().lower()
            if v in {"true", "yes", "1"}:
                return True
            if v in {"false", "no", "0"}:
                return False
        raise TypeError(f"Invalid boolean value: {value}")