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
from domain.entities.products.product_context import ProductContext
from domain.entities.categories.category_profile import CategoryProfile


@dataclass(frozen=True)
class CategoryEligibilityPolicy:

    def is_allowed(
        self,
        product: ProductContext,
        category: CategoryProfile
    ) -> bool:
        c = category.constraints

        if (
            c.allowed_genders is not None and
            product.gender not in c.allowed_genders
        ):
            return False

        if (
            c.allowed_business_types is not None and
            product.business_type not in c.allowed_business_types
        ):
            return False

        return True