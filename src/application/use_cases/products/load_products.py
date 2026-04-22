# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.repositories.product_repository import ProductRepository
from domain.entities.product import Product

from shared.kernel.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class LoadProductCommand:
    products: list[dict]


class LoadProductsUseCase:
    """
    Use case for loading products with automatic normalization.

    Architecture:
      - Uses UnitOfWork for transactional commit + event dispatch
      - The Product.create factory handles validation and normalization
    """

    def __init__(
        self,
        products: ProductRepository,
        uow: UnitOfWork,
    ):
        self.products = products
        self.uow = uow

    def execute(self, cmd: LoadProductCommand) -> list[Product]:
        # Load products by IDs
        products = [
            Product.create(**product_data)
            for product_data in cmd.products
        ]

        # Save all products in batch
        self.products.save_batch(products)

        # Commit via UoW
        self.uow.commit()

        return products