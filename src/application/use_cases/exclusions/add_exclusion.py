# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.product_repository import ProductRepository
from application.ports.category_repository import CategoryRepository
from application.ports.exclusion_repository import ExclusionRepository


@dataclass(frozen=True)
class AddExclusionCommand:
    product_id: UUID
    category_id: UUID
    reason: str


class AddExclusionUseCase:

    def __init__(
        self,
        products: ProductRepository,
        categories: CategoryRepository,
        exclusions: ExclusionRepository,
    ):
        self.products = products
        self.categories = categories
        self.exclusions = exclusions


    def execute(self, cmd: AddExclusionCommand) -> dict:
        p = self.products.get_by_id(cmd.product_id)
        if p is None:
            raise ValueError("Product not found")

        c = self.categories.get_by_id(cmd.category_id)
        if c is None:
            raise ValueError("Category not found")

        self.exclusions.add_exclusion(cmd.product_id, cmd.category_id, cmd.reason)
        return {"ok": True}
