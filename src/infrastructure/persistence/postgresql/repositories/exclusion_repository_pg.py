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
from application.ports.exclusion_repository import ExclusionRepository
from domain.entities.products.product_category_exclusion import ProductCategoryExclusion

from infrastructure.persistence.postgresql.models.product_category_exclusion import (
    ProductCategoryExclusionModel,
)


class ExclusionRepositoryPG(ExclusionRepository):

    def __init__(self, session: Session):
        self.session = session

    # ---------------------------------
    # Get excluded categories
    # ---------------------------------
    def get_excluded_category_ids(
        self,
        product_id: UUID,
    ) -> set[UUID]:

        stmt = select(
            ProductCategoryExclusionModel.category_id
        ).where(
            ProductCategoryExclusionModel.product_id == product_id
        )

        results = self.session.execute(stmt).scalars().all()

        return set(results)

    # ---------------------------------
    # Idempotent add
    # ---------------------------------
    def add_exclusion(
        self,
        product_id: UUID,
        category_id: UUID,
        reason: str,
    ) -> None:

        stmt = insert(ProductCategoryExclusionModel).values(
            product_id=product_id,
            category_id=category_id,
            reason=reason,
        )

        stmt = stmt.on_conflict_do_nothing(
            index_elements=["product_id", "category_id"]
        )

        self.session.execute(stmt)
        self.session.commit()

    # ---------------------------------
    # Optional: batch add
    # ---------------------------------
    def add_exclusions_batch(
        self,
        exclusions: list[ProductCategoryExclusion],
    ) -> None:

        if not exclusions:
            return

        values = [
            {
                "product_id": exclusion.product_id,
                "category_id": exclusion.category_id,
                "reason": exclusion.reason,
            }
            for exclusion in exclusions
        ]

        stmt = insert(ProductCategoryExclusionModel).values(values)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["product_id", "category_id"]
        )

        self.session.execute(stmt)
        self.session.commit()
