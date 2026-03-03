# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID
from typing import Iterable

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
from domain.value_objects.semantic_hash import SemanticHash
from domain.entities.categories.category_profile import CategoryProfile
from domain.entities.categories.category_constraints import CategoryConstraints

from application.ports.category_profile_repository import CategoryProfileRepository

from infrastructure.persistence.postgresql.models.category_profile_model import CategoryProfileModel

from utils.json import json_to_set


class CategoryProfileRepositoryPG(CategoryProfileRepository):

    def __init__(self, session: Session):
        self.session = session

    # --------------------------------------------------
    # List all
    # --------------------------------------------------
    def list_all_profiles(self) -> list[CategoryProfile]:

        stmt = (
            select(CategoryProfileModel)
            .options(
                # Avoid N+1 category loading
                selectinload(CategoryProfileModel.category)
            )
        )

        rows = self.session.execute(stmt).scalars().all()

        return [self._to_entity(r) for r in rows]

    # --------------------------------------------------
    # Save Single
    # --------------------------------------------------
    def save(self, profile: CategoryProfile) -> CategoryProfile:

        stmt = insert(CategoryProfileModel).values(
            category_id=profile.category.id,
            allowed_genders=list(profile.constraints.allowed_genders),
            allowed_business_types=list(profile.constraints.allowed_business_types),
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["category_id"],
            set_={
                "allowed_genders": stmt.excluded.allowed_genders,
                "allowed_business_types": stmt.excluded.allowed_business_types,
            },
        ).returning(CategoryProfileModel)

        result = self.session.execute(stmt).scalar_one()
        self.session.commit()

        return self._to_entity(result)

    # --------------------------------------------------
    # Batch Save
    # --------------------------------------------------
    def save_batch(
        self,
        profiles: Iterable[CategoryProfile],
        chunk_size: int = 100,
    ) -> list[CategoryProfile]:

        profiles = list(profiles)

        if not profiles:
            return []

        saved: list[CategoryProfile] = []

        for i in range(0, len(profiles), chunk_size):

            chunk = profiles[i : i + chunk_size]

            stmt = insert(CategoryProfileModel).values(
                [
                    {
                        "category_id": p.category.id,
                        "allowed_genders": list(p.constraints.allowed_genders),
                        "allowed_business_types": list(
                            p.constraints.allowed_business_types
                        ),
                    }
                    for p in chunk
                ]
            )

            stmt = stmt.on_conflict_do_update(
                index_elements=["category_id"],
                set_={
                    "allowed_genders": stmt.excluded.allowed_genders,
                    "allowed_business_types": stmt.excluded.allowed_business_types,
                },
            ).returning(CategoryProfileModel)

            results = self.session.execute(stmt).scalars().all()
            saved.extend(results)

        self.session.commit()

        return [self._to_entity(r) for r in saved]

    # --------------------------------------------------
    # Constraint Matching
    # --------------------------------------------------
    def get_profiles_by_constraints(
        self,
        constraints: CategoryConstraints,
        limit: int | None = None,
    ) -> list[CategoryProfile]:

        stmt = select(CategoryProfileModel).options(
            selectinload(CategoryProfileModel.category)
        )

        for attr in constraints.__dataclass_fields__.keys():
            print(attr, getattr(constraints, attr))
            if getattr(constraints, attr):
                stmt = stmt.where(
                    getattr(CategoryProfileModel, attr).overlap(
                        list(getattr(constraints, attr))
                    )
                )

        stmt = stmt.order_by(CategoryProfileModel.category_id)

        if limit:
            stmt = stmt.limit(limit)

        rows = self.session.execute(stmt).scalars().all()

        return [self._to_entity(r) for r in rows]

    # --------------------------------------------------
    # Private loaders
    # --------------------------------------------------
    def _get_by_category_id(
        self,
        category_id: UUID,
    ) -> CategoryProfile | None:

        stmt = (
            select(CategoryProfileModel)
            .options(selectinload(CategoryProfileModel.category))
            .where(CategoryProfileModel.category_id == category_id)
        )

        result = self.session.execute(stmt).scalar_one_or_none()

        return self._to_entity(result) if result else None

    # --------------------------------------------------
    # Mapper (Clean Domain Hydration)
    # --------------------------------------------------
    @staticmethod
    def _to_entity(model: CategoryProfileModel) -> CategoryProfile:

        category_model = model.category

        category = Category(
            id=category_model.id,
            name=category_model.name,
            level=category_model.level,
            description=category_model.description,
            url=category_model.url,
            brand=category_model.brand,
            direction=category_model.direction,
            business=category_model.business,
            semantic_hash=SemanticHash(category_model.semantic_hash),
            keywords=set(json_to_set(category_model.keywords_json or "[]")),
            parent_id=category_model.parent_id,
        )

        constraints = CategoryConstraints(
            allowed_genders=set(model.allowed_genders or []),
            allowed_business_types=set(model.allowed_business_types or []),
            allowed_directions=set(model.allowed_directions or []),
            allowed_brands=set(model.allowed_brands or []),
            required_keywords=set(model.required_keywords or []),
        )

        return CategoryProfile(
            category=category,
            constraints=constraints,
        )