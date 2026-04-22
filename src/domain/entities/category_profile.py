# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from .category import Category
from .brand import Brand
from utils.domain_validatons import validate_entity_fields


@dataclass(frozen=True)
class CategoryProfile:
    """
    Category profile with constraint fields for product matching.
    """

    category: Category

    # Constraint fields
    gender: str | None = None
    direction: str | None = None
    brand: Brand | None = None
    is_leaf: bool | None = None


    @classmethod
    def create(cls, **data) -> CategoryProfile:
        """
        Flexible factory:
        - Auto-maps dataclass fields
        - Rejects unknown fields
        - Normalizes consistently
        """

        normalized_data = validate_entity_fields(
            cls,
            data,
            required_fields={"category"},
        )

        return cls(
            category=normalized_data["category"],
            gender=normalized_data["gender"],
            direction=normalized_data["direction"],
            brand=normalized_data["brand"],
            is_leaf=normalized_data["is_leaf"],
        )


if __name__ == "__main__":

    brand = Brand.create(
        name="Generic",
        business={"liverpool", }
    )

    category = Category.create(
        id = "category-1",
        name = "Electronics",
        level = 1,
        parent_id = None,
        description = "All electronic items",
        keywords = tuple(["Electronics"])
    )

    profile = {
        "category": category,
        "gender": "unisex",
        "direction": "forward",
        "brand": brand,
        "is_leaf": True,
    }

    category_profile = CategoryProfile.create(**profile)

    print(category_profile)