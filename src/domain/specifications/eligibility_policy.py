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

        # Gender constraint
        if c.allowed_genders:
            if product.gender not in c.allowed_genders:
                return False

        # Business type constraint
        if c.allowed_business_types:
            if product.business_type not in c.allowed_business_types:
                return False

        return True