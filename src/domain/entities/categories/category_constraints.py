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
class CategoryConstraints:
    allowed_genders: list[str]
    allowed_business_types: list[str]
    allowed_directions: list[str]
    allowed_brands: list[str]
    required_keywords: list[str]

    @staticmethod
    def create(
        allowed_genders: list[str] | None = None,
        allowed_business_types: list[str] | None = None,
        allowed_directions: list[str] | None = None,
        allowed_brands: list[str] | None = None,
        required_keywords: list[str] | None = None
    ) -> CategoryConstraints:
        return CategoryConstraints(
            allowed_genders=allowed_genders,
            allowed_business_types=allowed_business_types,
            allowed_directions=allowed_directions,
            allowed_brands=allowed_brands,
            required_keywords=required_keywords
        )