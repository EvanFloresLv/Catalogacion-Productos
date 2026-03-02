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


    @staticmethod
    def create(allowed_genders: list[str], allowed_business_types: list[str]) -> CategoryConstraints:
        return CategoryConstraints(
            allowed_genders=allowed_genders,
            allowed_business_types=allowed_business_types
        )