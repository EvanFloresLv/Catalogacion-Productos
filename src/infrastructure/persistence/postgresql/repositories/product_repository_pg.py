# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID

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

        stmt = insert(ProductModel).values(
            id=product.id,
            title=product.title,
            description=product.description,
            keywords_json=set_to_json(product.keywords),
            gender=product.gender,
            business_type=product.business_type,
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "title": stmt.excluded.title,
                "description": stmt.excluded.description,
                "keywords_json": stmt.excluded.keywords_json,
                "gender": stmt.excluded.gender,
                "business_type": stmt.excluded.business_type,
            },
        )

        self.session.execute(stmt)
        self.session.commit()

    # ---------------------------------
    # Batch upsert
    # ---------------------------------
    def save_batch(self, products: list[Product]) -> None:

        if not products:
            return

        values = [
            {
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "keywords_json": set_to_json(p.keywords),
                "gender": p.gender,
                "business_type": p.business_type,
            }
            for p in products
        ]

        stmt = insert(ProductModel).values(values)

        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "title": stmt.excluded.title,
                "description": stmt.excluded.description,
                "keywords_json": stmt.excluded.keywords_json,
                "gender": stmt.excluded.gender,
                "business_type": stmt.excluded.business_type,
            },
        )

        self.session.execute(stmt)
        self.session.commit()

    # ---------------------------------
    # Get single
    # ---------------------------------
    def get_by_id(self, product_id: UUID) -> Product | None:

        stmt = select(ProductModel).where(
            ProductModel.id == product_id
        )

        result = self.session.execute(stmt).scalars().first()

        if not result:
            return None

        return self._to_entity(result)

    # ---------------------------------
    # Get multiple
    # ---------------------------------
    def get_by_ids(self, product_ids: list[UUID]) -> list[Product]:

        if not product_ids:
            return []


        stmt = select(ProductModel).where(
            ProductModel.id.in_(product_ids)
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

        return Product(
            id=model.id,
            title=model.title,
            description=model.description,
            keywords=json_to_set(model.keywords_json),
            gender=model.gender,
            business_type=model.business_type,
        )
