# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import text
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.categories.category import Category
from application.ports.outbound.category_repository import CategoryRepository


class SQLCategoryRepository(CategoryRepository):

    def __init__(self, db: Session):
        self.db = db


    def save(self, category: Category) -> None:
        self.db.execute(
            text(
                """
                INSERT INTO categories (id, name, parent_id)
                VALUES (:id, :name, :parent_id)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    parent_id = excluded.parent_id
                """
            ),
            {
                "id": str(category.id),
                "name": category.name,
                "parent_id": str(category.parent_id) if category.parent_id else None,
            },
        )
        self.db.commit()


    def get_all(self) -> list[Category]:
        rows = (
            self.db.execute(text("SELECT id, name, parent_id FROM categories"))
            .mappings()
            .all()
        )

        return [
            Category(
                id=UUID(r["id"]),
                name=r["name"],
                parent_id=UUID(r["parent_id"]) if r["parent_id"] else None,
            )
            for r in rows
        ]


    def get_by_id(self, category_id: UUID) -> Category | None:
        row = (
            self.db.execute(
                text(
                    """
                    SELECT id, name, parent_id
                    FROM categories
                    WHERE id = :id
                    """
                ),
                {"id": str(category_id)},
            )
            .mappings()
            .first()
        )

        if row is None:
            return None

        parent_id = row["parent_id"]

        return Category(
            id=UUID(row["id"]),
            name=row["name"],
            parent_id=UUID(parent_id) if parent_id else None,
        )
