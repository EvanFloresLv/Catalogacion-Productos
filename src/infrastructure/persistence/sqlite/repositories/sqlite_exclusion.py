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
from application.ports.outbound.exclusion_repository import ExclusionRepository


class SQLiteExclusionRepository(ExclusionRepository):

    def __init__(self, conn):
        self.conn = conn


    def get_excluded_category_ids(self, product_id: UUID) -> set[UUID]:
        rows = self.conn.execute(
            """
            SELECT category_id FROM product_category_exclusions
            WHERE product_id = ?
            """,
            (str(product_id),),
        ).fetchall()

        return {UUID(r["category_id"]) for r in rows}


    def add_exclusion(
        self,
        product_id: UUID,
        category_id: UUID,
        reason: str
    ) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO product_category_exclusions
            (product_id, category_id, reason)
            VALUES (?, ?, ?)
            """,
            (str(product_id), str(category_id), reason.strip()),
        )
        self.conn.commit()