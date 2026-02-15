# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import json
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import select
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.products.product import Product
from application.ports.outbound.product_repository import ProductRepository
from infrastructure.persistence.models.product_model import ProductModel
from infrastructure.persistence.utils.uuid import uuid_to_bytes, bytes_to_uuid


class SQLProductRepository(ProductRepository):

    def __init__(self, session: Session):
        self.session = session


    def save(self, product: Product) -> None:
        model = ProductModel(
            id=uuid_to_bytes(product.id),
            title=product.title,
            description=product.description,
            keywords_json=json.dumps(product.keywords),
        )

        self.session.merge(model)
        self.session.commit()


    def get_all(self) -> list[Product]:
        stmt = select(ProductModel)
        result = self.session.execute(stmt).scalars().all()

        return [
            Product(
                id=bytes_to_uuid(item.id),
                title=item.title,
                description=item.description,
                keywords=json.loads(item.keywords_json)
            )
            for item in result
        ]


    def get_by_id(self, product_id: UUID) -> Product | None:
        result = self.session.get(ProductModel, uuid_to_bytes(product_id))

        if result is None:
            return None

        return Product(
            id=bytes_to_uuid(result.id),
            title=result.title,
            description=result.description,
            keywords=json.loads(result.keywords_json)
        )