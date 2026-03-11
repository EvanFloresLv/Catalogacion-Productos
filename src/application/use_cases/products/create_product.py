# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.product_repository import ProductRepository
from domain.entities.products.product import Product


@dataclass(frozen=True)
class CreateProductCommand:
    products: list[dict]


class CreateProductUseCase:
    """
    Use case for creating products with automatic normalization.

    The Product.create factory handles:
    - Field validation
    - Text normalization (unicode, whitespace)
    - Keyword extraction and deduplication
    - Product type validation
    """

    def __init__(self, products: ProductRepository):
        self.products = products


    def execute(self, cmd: CreateProductCommand) -> list[Product]:
        # Create normalized Product entities
        products = [
            Product.create(**product_data)
            for product_data in cmd.products
        ]

        # Save all products in batch
        self.products.save_batch(products)

        return products