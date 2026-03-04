# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID
from dataclasses import asdict
import json

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
from application.ports.category_repository import CategoryRepository
from infrastructure.persistence.postgresql.models.category_model import CategoryModel
from utils.json import json_to_set


class CategoryRepositoryPG(CategoryRepository):

    def __init__(self, session: Session):
        self.session = session

    # ============================================================
    # Persistence
    # ============================================================

    def save(self, category: Category) -> Category:
        cat_data = self._build_data(category)

        stmt = insert(CategoryModel).values(**cat_data)

        update_fields = {
            column.name: getattr(stmt.excluded, column.name)
            for column in CategoryModel.__table__.columns
            if column.name != "id"
        }

        stmt = (
            stmt.on_conflict_do_update(
                index_elements=["id"],
                set_=update_fields,
            )
            .returning(CategoryModel)
        )

        result = self.session.execute(stmt).scalar_one()

        # ensure visibility inside transaction
        self.session.flush()

        return self._to_entity(result)

    # -------------------------------------------------------------

    def save_batch(self, categories: list[Category]) -> list[Category]:
        if not categories:
            return []

        values = [self._build_data(cat) for cat in categories]

        stmt = insert(CategoryModel).values(values)

        update_fields = {
            column.name: getattr(stmt.excluded, column.name)
            for column in CategoryModel.__table__.columns
            if column.name != "id"
        }

        stmt = (
            stmt.on_conflict_do_update(
                index_elements=["id"],
                set_=update_fields,
            )
            .returning(CategoryModel)
        )

        results = self.session.execute(stmt).scalars().all()

        # single flush for entire batch
        self.session.flush()

        return [self._to_entity(r) for r in results]

    # ============================================================
    # Queries
    # ============================================================

    def get_all(self) -> list[Category]:
        stmt = select(CategoryModel)
        results = self.session.execute(stmt).scalars().all()
        return self._to_entities(results)


    def get_by_id(self, category_id: UUID) -> Category | None:
        stmt = select(CategoryModel).where(CategoryModel.id == category_id)
        result = self.session.execute(stmt).scalar_one_or_none()
        return self._to_entity(result) if result else None


    def get_by_ids(self, category_ids: list[UUID]) -> list[Category]:
        if not category_ids:
            return []

        stmt = select(CategoryModel).where(
            CategoryModel.id.in_(category_ids)
        )
        results = self.session.execute(stmt).scalars().all()
        return self._to_entities(results)

    # ============================================================
    # Helpers
    # ============================================================

    @staticmethod
    def _build_data(category: Category) -> dict:
        data = asdict(category)
        data["keywords_json"] = list(category.keywords_json)

        return data


    @staticmethod
    def _to_entity(model: CategoryModel) -> Category:
        return Category(
            id=model.id,
            name=model.name,
            level=model.level,
            description=model.description,
            url=model.url,
            brand=model.brand,
            direction=model.direction,
            business=model.business,
            semantic_hash=SemanticHash(model.semantic_hash),
            keywords_json=tuple(model.keywords_json),
            parent_id=model.parent_id,
        )

    def _to_entities(self, models: list[CategoryModel]) -> list[Category]:
        return [self._to_entity(m) for m in models]