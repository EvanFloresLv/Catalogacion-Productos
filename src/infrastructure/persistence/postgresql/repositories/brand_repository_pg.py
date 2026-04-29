# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from typing import List, Optional
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
from domain.entities.brand import Brand
from domain.repositories.brand_repository import BrandRepository
from infrastructure.persistence.postgresql.models.brand_model import (
    BrandModel,
)


class BrandRepositoryPG(BrandRepository):

    def __init__(self, session: Session):
        self.session = session

    def save(self, brand: Brand) -> None:
        row = self._build_row(brand)
        stmt = insert(BrandModel).values(**row)
        stmt = (
            stmt.on_conflict_do_update(
                index_elements=["name"],
                set_=self._build_update_map(stmt),
            )
            .returning(BrandModel)
        )
        result = self.session.execute(stmt).scalar_one()
        self.session.flush()
        return self._to_entity(result)

    def save_batch(self, brands: List[Brand]) -> List[Brand]:
        if not brands:
            return []

        rows = [self._build_row(brand) for brand in brands]
        stmt = insert(BrandModel).values(rows)
        stmt = (
            stmt.on_conflict_do_update(
                index_elements=["name"],
                set_=self._build_update_map(stmt),
            )
            .returning(BrandModel)
        )
        results = self.session.execute(stmt).scalars().all()
        self.session.flush()
        return [self._to_entity(r) for r in results]

    def get_all(self) -> List[Brand]:
        stmt = select(BrandModel)
        results = self.session.execute(stmt).scalars().all()
        return [self._to_entity(r) for r in results]

    def get_by_name(self, brand_name: str) -> Optional[Brand]:
        stmt = select(BrandModel).where(BrandModel.name == brand_name)
        result = self.session.execute(stmt).scalar_one_or_none()
        return self._to_entity(result) if result else None

    def get_by_id(self, brand_id):
        stmt = select(BrandModel).where(BrandModel.id == brand_id)
        result = self.session.execute(stmt).scalar_one_or_none()
        return self._to_entity(result) if result else None

    def get_by_business(self, business_str: str) -> List[Brand]:
        stmt = select(BrandModel).where(BrandModel.business == business_str)
        results = self.session.execute(stmt).scalars().all()
        return [self._to_entity(r) for r in results]


    # ============================================================
    # Helpers
    # ============================================================

    @staticmethod
    def _build_row(brand: Brand) -> dict:

        model_columns = {c.name for c in BrandModel.__table__.columns}

        row = {}

        for field in fields(Brand):

            if field.name not in model_columns:
                continue

            if not getattr(brand, field.name):
                raise ValueError(f"Missing required field '{field.name}' for BrandModel")

            value = getattr(brand, field.name)

            if field.name == "business":
                value = list(value or [])  # Convert set to list for JSONB storage

            row[field.name] = value

        return row

    # -------------------------------------------------------------
    @staticmethod
    def _build_update_map(stmt) -> dict:
        return {
            column.name: getattr(stmt.excluded, column.name)
            for column in BrandModel.__table__.columns
        }

    # -------------------------------------------------------------

    @staticmethod
    def _to_entity(model: BrandModel) -> Brand:
        brand = Brand(
            id=model.id,
            name=model.name,
            business=tuple(model.business or []),
        )
        return brand


    # -------------------------------------------------------------

    def _to_entities(
        self,
        models: list[BrandModel],
    ) -> list[Brand]:

        return [self._to_entity(m) for m in models]