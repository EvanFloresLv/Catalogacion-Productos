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
    gender: str | None = None
    business: str | None = None
    direction: str | None = None
    brand: str | None = None


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
            value = data.get(name, "")
            normalized[name] = value.strip().lower()

        return cls(**normalized)
