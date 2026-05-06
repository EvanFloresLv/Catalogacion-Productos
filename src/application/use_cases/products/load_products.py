# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from dataclasses import dataclass
from typing import List

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.product import Product
from domain.repositories.product_repository import ProductRepository
from domain.aggregates.product_catalog import ProductCatalog

from shared.kernel.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class LoadProductsCommand:
    products: List[Product]


class LoadProductsUseCase:

    def __init__(
        self,
        repo: ProductRepository,
        uow: UnitOfWork,
    ):
        self.repo = repo
        self.uow = uow


    def execute(self, cmd: LoadProductsCommand) -> List[Product]:

        catalog = ProductCatalog()
        self.uow.register(catalog)

        catalog.add_products_batch(cmd.products)
        _ = self.repo.save_batch(catalog.products)

        self.uow.commit()

        return catalog.products

