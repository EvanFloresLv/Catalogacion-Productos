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
from application.ports.outbound.exclusion_repository import ExclusionRepository


class SQLExclusionRepository(ExclusionRepository):

    def __init__(self, db: Session):
        self.db = db


    def get_excluded_category_ids(self, product_id: UUID) -> set[UUID]:
        rows = (
            self.db.execute(
                text(
                    """
                    SELECT category_id
                    FROM product_category_exclusions
                    WHERE product_id = :product_id
                    """
                ),
                {"product_id": str(product_id)},
            )
            .mappings()
            .all()
        )

        return {UUID(r["category_id"]) for r in rows}


    def add_exclusion(
        self,
        product_id: UUID,
        category_id: UUID,
        reason: str,
    ) -> None:
        reason = reason.strip()
        if not reason:
            reason = "No reason provided"

        self.db.execute(
            text(
                """
                INSERT INTO product_category_exclusions
                    (product_id, category_id, reason)
                VALUES
                    (:product_id, :category_id, :reason)
                ON CONFLICT(product_id, category_id) DO UPDATE SET
                    reason = excluded.reason
                """
            ),
            {
                "product_id": str(product_id),
                "category_id": str(category_id),
                "reason": reason,
            },
        )

        self.db.commit()
