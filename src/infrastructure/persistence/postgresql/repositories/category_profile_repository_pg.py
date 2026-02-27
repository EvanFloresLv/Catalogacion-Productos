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
from domain.entities.categories.category import Category
from domain.value_objects.semantic_hash import SemanticHash
from domain.entities.categories.category_profile import CategoryProfile
from domain.entities.categories.category_constraints import CategoryConstraints
from application.ports.category_profile_repository import CategoryProfileRepository

from infrastructure.persistence.postgresql.models.category_profile_model import CategoryProfileModel
from infrastructure.persistence.postgresql.models.category_model import CategoryModel

from utils.json import json_to_set, set_to_json


class CategoryProfileRepositoryPG(CategoryProfileRepository):

    def __init__(self, session: Session):
        self.session = session

    # ---------------------------------
    # Upsert
    # ---------------------------------
    def upsert_profile(
        self,
        category_id: UUID,
        keywords: list[str],
        allowed_genders: set[str] | None,
        allowed_business_types: set[str] | None,
    ) -> None:

        stmt = insert(CategoryProfileModel).values(
            category_id=category_id,
            keywords_json=set_to_json(keywords),
            allowed_genders_json=set_to_json(allowed_genders),
            allowed_business_types_json=set_to_json(allowed_business_types),
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["category_id"],
            set_={
                "keywords_json": stmt.excluded.keywords_json,
                "allowed_genders_json": stmt.excluded.allowed_genders_json,
                "allowed_business_types_json": stmt.excluded.allowed_business_types_json,
            },
        )

        self.session.execute(stmt)
        self.session.commit()

    # ---------------------------------
    # List all
    # ---------------------------------
    def list_all_profiles(self) -> list[CategoryProfile]:

        stmt = (
            select(CategoryProfileModel, CategoryModel)
            .join(
                CategoryModel,
                CategoryModel.id == CategoryProfileModel.category_id,
            )
        )

        rows = self.session.execute(stmt).all()

        if not rows:
            return []

        return [
            self._to_entity(profile_row, category_row)
            for profile_row, category_row in rows
            ]

    # ---------------------------------
    # Mapper
    # ---------------------------------
    @staticmethod
    def _to_entity(
        profile_model: CategoryProfileModel,
        category_model: CategoryModel,
    ) -> CategoryProfile:

        category = Category(
            id=category_model.id,
            name=category_model.name,
            description=category_model.description,
            semantic_hash=SemanticHash(category_model.semantic_hash),
            keywords=json_to_set(category_model.keywords_json),
            parent_id=category_model.parent_id,
        )

        constraints = CategoryConstraints(
            allowed_genders=json_to_set(profile_model.allowed_genders_json),
            allowed_business_types=json_to_set(profile_model.allowed_business_types_json),
        )

        return CategoryProfile(
            category=category,
            constraints=constraints,
        )
