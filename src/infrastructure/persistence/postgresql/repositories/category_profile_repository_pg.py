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

    def get_profiles_by_constraints(self, **kwargs) -> list[CategoryProfile]:

        allowed_fields = {'gender', 'direction', 'brand', 'business', 'is_leaf', 'limit'}
        for key in kwargs:
            if key not in allowed_fields:
                raise ValueError(f"Invalid constraint field: {key}")

        constraint_fields = {
            'gender': kwargs.get('gender', None),
            'direction': kwargs.get('direction', None),
            'brand': kwargs.get('brand', None),
            'business': kwargs.get('business', None),
            'is_leaf': kwargs.get('is_leaf', None),
        }

        limit = kwargs.get('limit', None)

        stmt = select(CategoryProfileModel).options(
            selectinload(CategoryProfileModel.category)
        )

        print("\n=== Querying profiles by constraints ===")
        print(f"Constraints: gender={constraint_fields['gender']}, business={constraint_fields['business']}, "
              f"direction={constraint_fields['direction']}, brand={constraint_fields['brand']}, is_leaf={constraint_fields['is_leaf']}")


        for field_name, value in constraint_fields.items():
            if value is not None:
                model_field = getattr(CategoryProfileModel, field_name)

                if isinstance(value, bool):
                    # For boolean fields, exact match
                    print(f"  - Adding filter: {field_name} = {value}")
                    stmt = stmt.where(model_field == value)
                else:
                    # For string fields, match or NULL
                    print(f"  - Adding filter: {field_name} = '{value}' OR {field_name} IS NULL")
                    stmt = stmt.where(
                        (model_field == value) | (model_field.is_(None))
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
        All constraint fields are stored directly on the profile.
        """
        return {
            "category_id": profile.category.id,
            "gender": profile.gender,
            "direction": profile.direction,
            "brand": profile.brand,
            "business": profile.business,
            "is_leaf": profile.is_leaf,
        }


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

        category_model = model.category

        # Hydrate Category dynamically
        category = Category(
            **{
                field: getattr(category_model, field)
                for field in category_field_names
                if hasattr(category_model, field)
            }
        )

        # Create CategoryProfile with constraint fields from model
        return CategoryProfile.create(
            category=category,
            gender=model.gender,
            direction=model.direction,
            brand=model.brand,
            business=model.business,
            is_leaf=model.is_leaf,
        )