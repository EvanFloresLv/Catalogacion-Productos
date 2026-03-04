# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Iterable, Tuple

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CategoryConstraints:
    allowed_genders: Tuple[str, ...] = field(default_factory=tuple)
    allowed_business_types: Tuple[str, ...] = field(default_factory=tuple)
    allowed_directions: Tuple[str, ...] = field(default_factory=tuple)
    allowed_brands: Tuple[str, ...] = field(default_factory=tuple)
    required_keywords: Tuple[str, ...] = field(default_factory=tuple)


    @classmethod
    def create(cls, **data: Any):
        """
        Flexible factory:
        - Auto-maps dataclass fields
        - Rejects unknown fields
        - Normalizes values
        - Converts lists to tuples (immutability-safe)
        """

        field_names = {f.name for f in fields(cls)}

        # -----------------------------
        # Reject unknown fields
        # -----------------------------
        unknown_fields = set(data) - field_names

        if unknown_fields:
            raise ValueError(f"Unknown fields: {unknown_fields}")

        # -----------------------------
        # Normalize and convert values
        # -----------------------------
        normalized = {}

        for name in field_names:
            value = data.get(name, [])
            normalized[name] = cls._normalize_iterable(value)

        return cls(**normalized)


    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    @staticmethod
    def _normalize_iterable(
        value: Iterable[str] | None,
    ) -> tuple[str, ...]:

        if value is None:
            return ()

        cleaned = {
            str(v).strip().lower()
            for v in value
            if isinstance(v, str) and v.strip()
        }

        return tuple(sorted(cleaned))
