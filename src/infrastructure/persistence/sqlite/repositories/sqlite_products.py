# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import json
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.products.product import Product
from application.ports.outbound.product_repository import ProductRepository


class SQLiteProductRepository(ProductRepository):

    def __init__(self, conn):
        self.conn = conn


    def save(self, product: Product) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO products
            (id, title, description, keywords_json, gender, business_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(product.id),
                product.title,
                product.description,
                json.dumps(product.keywords),
                product.gender,
                product.business_type,
            ),
        )
        self.conn.commit()


    def get_by_id(self, product_id: UUID) -> Product | None:
        row = self.conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (str(product_id),),
        ).fetchone()

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
