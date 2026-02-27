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
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.categories.category import Category
from domain.value_objects.semantic_hash import SemanticHash
from application.ports.category_repository import CategoryRepository
from infrastructure.persistence.postgresql.models.category_model import CategoryModel
from utils.json import json_to_set, set_to_json


class CategoryRepositoryPG(CategoryRepository):

    def __init__(self, session: Session):
        self.session = session

    # ============================================================
    # Persistence
    # ============================================================

    def save(self, category: Category) -> Category:
        """Upsert single category and return rebuilt entity."""

        stmt = insert(CategoryModel).values(
            id=category.id,
            name=category.name,
            description=category.description,
            semantic_hash=str(category.semantic_hash),
            keywords_json=set_to_json(category.keywords),
            parent_id=category.parent_id,
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["semantic_hash"],
            set_={
                "name": stmt.excluded.name,
                "description": stmt.excluded.description,
                "keywords_json": stmt.excluded.keywords_json,
                "parent_id": stmt.excluded.parent_id,
            },
        ).returning(CategoryModel)

        result = self.session.execute(stmt).scalar_one()
        self.session.commit()

        return self._to_entity(result)

    # -------------------------------------------------------------

    def save_batch(
        self,
        categories: Iterable[Category],
        chunk_size: int = 100,
    ) -> list[Category]:
        """Batch upsert and return fully reconstructed domain entities."""

        categories = list(categories)
        if not categories:
            return []

        results: list[Category] = []

        values = [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "semantic_hash": str(c.semantic_hash),
                "keywords_json": set_to_json(c.keywords),
                "parent_id": c.parent_id,
            }
            for c in categories
        ]

        for i in range(0, len(values), chunk_size):
            batch = values[i : i + chunk_size]

            stmt = insert(CategoryModel).values(batch)

            stmt = stmt.on_conflict_do_update(
                index_elements=["semantic_hash"],
                set_={
                    "name": stmt.excluded.name,
                    "description": stmt.excluded.description,
                    "keywords_json": stmt.excluded.keywords_json,
                    "parent_id": stmt.excluded.parent_id,
                },
            ).returning(CategoryModel)

            rows = self.session.execute(stmt).scalars().all()
            results.extend(self._to_entities(rows))

        self.session.commit()

        return results

    # ============================================================
    # Queries
    # ============================================================

    def get_all(self) -> list[Category]:
        stmt = select(CategoryModel)

        results = self.session.execute(stmt).scalars().all()

        return self._to_entities(results)

    # -------------------------------------------------------------

    def get_by_id(self, category_id: UUID) -> Category | None:
        stmt = select(CategoryModel).where(CategoryModel.id == category_id)

        result = self.session.execute(stmt).scalar_one_or_none()

        if not result:
            return None

        return self._to_entity(result)

    # -------------------------------------------------------------

    def get_by_ids(self, category_ids: list[UUID]) -> list[Category]:
        if not category_ids:
            return []

        stmt = select(CategoryModel).where(
            CategoryModel.id.in_(category_ids)
        )

        results = self.session.execute(stmt).scalars().all()

        return self._to_entities(results)

    # ============================================================
    # Mapping helpers
    # ============================================================

    @staticmethod
    def _to_entity(model: CategoryModel) -> Category:
        return Category(
            id=model.id,
            name=model.name,
            description=model.description,
            semantic_hash=SemanticHash(model.semantic_hash),
            keywords=json_to_set(model.keywords_json),
            parent_id=model.parent_id,
        )

    # -------------------------------------------------------------

    def _to_entities(self, models: list[CategoryModel]) -> list[Category]:
        return [self._to_entity(m) for m in models]