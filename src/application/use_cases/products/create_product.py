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


@dataclass(frozen=True)
class CreateProductCommand:
    title: str
    description: str
    keywords: list[str]
    gender: str | None
    business_type: str | None


class CreateProductUseCase:
    def __init__(self, products: ProductRepository):
        self.products = products

    def execute(self, cmd: CreateProductCommand) -> Product:
        p = Product.create(
            title=cmd.title,
            description=cmd.description,
            keywords=cmd.keywords,
            gender=cmd.gender,
            business_type=cmd.business_type,
        )
        self.products.save(p)
        return p