# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.product import Product
from domain.repositories.product_repository import ProductRepository
from domain.aggregates.product_catalog import ProductCatalog

from shared.kernel.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class LoadProductCommand:
    products: list[dict]


class LoadProductsUseCase:

    def __init__(
        self,
        repo: ProductRepository,
        uow: UnitOfWork,
    ):
        self.repo = repo
        self.uow = uow

    def execute(self, cmd: LoadProductCommand) -> list[Product]:

        catalog = ProductCatalog()
        self.uow.register(catalog)

        products = [
            Product.create(**product_data)
            for product_data in cmd.products
        ]

        catalog.add_products_batch(products)
        saved = self.repo.save_batch(catalog.products)

        self.uow.commit()

        return saved