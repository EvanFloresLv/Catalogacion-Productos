# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import logging
from dataclasses import dataclass
from typing import List

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.product import Product
from domain.repositories.product_repository import ProductRepository
from domain.aggregates.product_catalog import ProductCatalog

from shared.kernel.unit_of_work import UnitOfWork


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

        try:
            logger.info(f"Loading products: {len(cmd.products)}")

            catalog = ProductCatalog()
            self.uow.register(catalog)

            catalog.add_products_batch(cmd.products)
            _ = self.repo.save_batch(catalog.products)

            self.uow.commit()

            logger.info(f"Products loaded successfully: {len(catalog.products)}")

            return catalog.products

        except Exception as e:
            logger.error(f"Error loading products: {e}")
            self.uow.rollback()
            raise e