# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from typing import Iterable
from dataclasses import fields

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.categories.category import Category
from domain.entities.categories.category_profile import CategoryProfile
from domain.entities.categories.category_constraints import CategoryConstraints

from application.ports.category_profile_repository import (
    CategoryProfileRepository,
)

from infrastructure.persistence.postgresql.models.category_profile_model import (
    CategoryProfileModel,
)


class CategoryProfileRepositoryPG(CategoryProfileRepository):

    def __init__(self, session: Session):
        self.session = session

    # ============================================================
    # List all
    # ============================================================

    def list_all_profiles(self) -> list[CategoryProfile]:

        stmt = (
            select(CategoryProfileModel)
            .options(selectinload(CategoryProfileModel.category))
        )

        rows = self.session.execute(stmt).scalars().all()

        return [self._to_entity(r) for r in rows]

    # ============================================================
    # Save Single (Dynamic Upsert)
    # ============================================================

    def save(self, profile: CategoryProfile) -> CategoryProfile:

        row = self._build_row(profile)

        stmt = insert(CategoryProfileModel).values(**row)

        stmt = (
            stmt.on_conflict_do_update(
                index_elements=["category_id"],
                set_=self._build_update_map(stmt),
            )
            .returning(CategoryProfileModel)
        )

        result = self.session.execute(stmt).scalar_one()
        self.session.commit()

        return self._to_entity(result)

    # ============================================================
    # Batch Save (Chunked Dynamic Upsert)
    # ============================================================

    def save_batch(
        self,
        profiles: Iterable[CategoryProfile],
        chunk_size: int = 100,
    ) -> list[CategoryProfile]:

        profiles = list(profiles)

        if not profiles:
            return []

        unique_profiles = {}
        for profile in profiles:
            unique_profiles[profile.category.id] = profile

        profiles = list(unique_profiles.values())

        saved_models: list[CategoryProfileModel] = []

        for i in range(0, len(profiles), chunk_size):

            chunk = profiles[i : i + chunk_size]

            rows = [self._build_row(p) for p in chunk]

            stmt = insert(CategoryProfileModel).values(rows)

            stmt = (
                stmt.on_conflict_do_update(
                    index_elements=["category_id"],
                    set_=self._build_update_map(stmt),
                )
                .returning(CategoryProfileModel)
            )

            results = self.session.execute(stmt).scalars().all()
            saved_models.extend(results)

        self.session.commit()

        return [self._to_entity(r) for r in saved_models]

    # ============================================================
    # Constraint Matching
    # ============================================================

    def get_profiles_by_constraints(
        self,
        constraints: CategoryConstraints,
        limit: int | None = None,
    ) -> list[CategoryProfile]:

        stmt = select(CategoryProfileModel).options(
            selectinload(CategoryProfileModel.category)
        )

        # Dynamically apply overlap filters
        for field in fields(CategoryConstraints):
            value = getattr(constraints, field.name)
            if value:
                stmt = stmt.where(
                    getattr(CategoryProfileModel, field.name).overlap(
                        list(value)
                    )
                )

        stmt = stmt.order_by(CategoryProfileModel.category_id)

        if limit:
            stmt = stmt.limit(limit)

        rows = self.session.execute(stmt).scalars().all()

        return [self._to_entity(r) for r in rows]

    # ============================================================
    # Private Helpers
    # ============================================================

    @staticmethod
    def _build_row(profile: CategoryProfile) -> dict:
        """
        Build dynamic insert row from CategoryProfile entity.
        - business field is stored as an array
        - other fields are stored as single string values
        """

        constraints = profile.constraints

        row = {
            "category_id": profile.category.id,
        }

        for field in fields(constraints):
            value = getattr(constraints, field.name)
            row[field.name] = value

        return row


    @staticmethod
    def _build_update_map(stmt) -> dict:
        """
        Build dynamic ON CONFLICT update map.
        Excludes primary key.
        """

        return {
            column.name: getattr(stmt.excluded, column.name)
            for column in CategoryProfileModel.__table__.columns
            if column.name != "category_id"
        }

    # -------------------------------------------------------------

    @staticmethod
    def _to_entity(model: CategoryProfileModel) -> CategoryProfile:

        category_field_names = {f.name for f in fields(Category)}
        constraints_field_names = {
            f.name for f in fields(CategoryConstraints)
        }

        category_model = model.category

        # Hydrate Category dynamically
        category = Category(
            **{
                field: getattr(category_model, field)
                for field in category_field_names
                if hasattr(category_model, field)
            }
        )

        # Hydrate Constraints dynamically
        # Handle business field as list, others as strings
        constraint_data = {}
        for field in constraints_field_names:
            if hasattr(model, field):
                value = getattr(model, field)
                constraint_data[field] = value

        constraints = CategoryConstraints(**constraint_data)

        return CategoryProfile(
            category=category,
            constraints=constraints,
        )