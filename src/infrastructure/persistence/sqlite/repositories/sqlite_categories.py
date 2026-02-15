# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.categories.category import Category
from application.ports.outbound.category_repository import CategoryRepository


class SQLiteCategoryRepository(CategoryRepository):

    def __init__(self, conn):
        self.conn = conn


    def save(self, category: Category) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO categories (id, name, parent_id)
            VALUES (?, ?, ?)
            """,
            (str(category.id), category.name, str(category.parent_id) if category.parent_id else None),
        )
        self.conn.commit()


    def get_all(self):
        rows = self.conn.execute("SELECT * FROM categories").fetchall()

        return [Category(
            id=UUID(row["id"]),
            name=row["name"],
            parent_id=UUID(row["parent_id"]) if row["parent_id"] else None
        ) for row in rows]


    def get_by_id(self, category_id: UUID) -> Category | None:
        row = self.conn.execute(
            "SELECT * FROM categories WHERE id = ?",
            (str(category_id),),
        ).fetchone()

        if row is None:
            return None

        parent = row["parent_id"]
        return Category(
            id=UUID(row["id"]),
            name=row["name"],
            parent_id=UUID(parent) if parent else None,
        )
