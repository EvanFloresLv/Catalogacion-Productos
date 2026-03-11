# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID
from dataclasses import fields

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.products.product import Product
from application.ports.product_repository import ProductRepository
from infrastructure.persistence.postgresql.models.product_model import ProductModel
from utils.json import set_to_json, json_to_set


class ProductRepositoryPG(ProductRepository):

    def __init__(self, session: Session):
        self.session = session

    # ---------------------------------
    # Single upsert
    # ---------------------------------
    def save(self, product: Product) -> None:
        """
        Save or update a product.

        On conflict (sku)
        - Updates all fields except sku
        """
        values = {
            field.name: getattr(product, field.name)
            for field in fields(Product)
        }

        stmt = insert(ProductModel).values(**values)

        # Build update dict excluding sku and composite key fields
        update_fields = {
            field.name: getattr(stmt.excluded, field.name)
            for field in fields(Product)
            if field.name not in ["sku"]
        }

        stmt = stmt.on_conflict_do_update(
            index_elements=["sku"],
            set_=update_fields,
        )

        self.session.execute(stmt)
        self.session.commit()

    # ---------------------------------
    # Batch upsert
    # ---------------------------------
    def save_batch(self, products: list[Product]) -> None:
        """
        Save or update multiple products in a batch.

        On conflict (sku):
        - Updates all fields except sku
        """
        if not products:
            return

        values = [
            {
                field.name: getattr(p, field.name)
                for field in fields(Product)
            }
            for p in products
        ]

        stmt = insert(ProductModel).values(values)

        # Build update dict excluding sku and composite key fields
        update_fields = {
            field.name: getattr(stmt.excluded, field.name)
            for field in fields(Product)
            if field.name not in ["sku"]
        }

        stmt = stmt.on_conflict_do_update(
            index_elements=["sku"],
            set_=update_fields,
        )

        self.session.execute(stmt)
        self.session.commit()

    # ---------------------------------
    # Get single
    # ---------------------------------
    def get_by_sku(self, sku: str) -> Product | None:

        stmt = select(ProductModel).where(
            ProductModel.sku == sku
        )

        result = self.session.execute(stmt).scalars().first()

        if not result:
            return None

        return self._to_entity(result)

    # ---------------------------------
    # Get multiple
    # ---------------------------------
    def get_by_skus(self, skus: list[str]) -> list[Product]:

        if not skus:
            return []


        stmt = select(ProductModel).where(
            ProductModel.sku.in_(skus)
        )

        results = self.session.execute(stmt).scalars().all()

        return [self._to_entity(model) for model in results]

    # ---------------------------------
    # Get all
    # ---------------------------------
    def get_all(self) -> list[Product]:

        stmt = select(ProductModel)

        results = self.session.execute(stmt).scalars().all()

        return [self._to_entity(model) for model in results]

    # ---------------------------------
    # Private mapper
    # ---------------------------------
    @staticmethod
    def _to_entity(model: ProductModel) -> Product:
        """
        Convert ProductModel to Product entity.

        Maps all fields from the model to the entity,
        handling keywords_json properly.
        """
        values = {
            field.name: getattr(model, field.name)
            for field in fields(Product)
        }

        return Product(**values)
