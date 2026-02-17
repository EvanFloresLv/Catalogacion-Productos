# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import json
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import text
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.products.product import Product
from application.ports.outbound.product_repository import ProductRepository


class SQLProductRepository(ProductRepository):

    def __init__(self, db: Session):
        self.db = db


    def save(self, product: Product) -> None:
        self.db.execute(
            text(
                """
                INSERT INTO products
                    (id, title, description, keywords_json, gender, business_type)
                VALUES
                    (:id, :title, :description, :keywords_json, :gender, :business_type)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    keywords_json = excluded.keywords_json,
                    gender = excluded.gender,
                    business_type = excluded.business_type
                """
            ),
            {
                "id": str(product.id),
                "title": product.title,
                "description": product.description,
                "keywords_json": json.dumps(product.keywords),
                "gender": product.gender,
                "business_type": product.business_type,
            },
        )
        self.db.commit()


    def get_by_id(self, product_id: UUID) -> Product | None:
        row = (
            self.db.execute(
                text(
                    """
                    SELECT id, title, description, keywords_json, gender, business_type
                    FROM products
                    WHERE id = :id
                    """
                ),
                {"id": str(product_id)},
            )
            .mappings()
            .first()
        )

        if row is None:
            return None

        return Product(
            id=UUID(row["id"]),
            title=row["title"],
            description=row["description"],
            keywords=json.loads(row["keywords_json"]),
            gender=row["gender"],
            business_type=row["business_type"],
        )
