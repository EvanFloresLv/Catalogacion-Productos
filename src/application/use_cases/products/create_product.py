# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from dataclasses import dataclass
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.outbound.product_repository import ProductRepository
from domain.products.product import Product


@dataclass
class CreateProductCommand:
    title: str
    description: str
    keywords: list[str]


class CreateProductUseCase:

    def __init__(self, products: ProductRepository):
        self.products = products


    def execute(self, cmd: CreateProductCommand) -> Product:

        product = Product(
            title=cmd.title,
            description=cmd.description,
            keywords=cmd.keywords
        )

        self.products.save(product)
        return product