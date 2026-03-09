# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID
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
from domain.entities.categories.category import Category
from application.ports.category_repository import CategoryRepository
from infrastructure.persistence.postgresql.models.category_model import (
    CategoryModel,
)


class CategoryRepositoryPG(CategoryRepository):

    def __init__(self, session: Session):
        self.session = session

    # ============================================================
    # Persistence
    # ============================================================

    def save(self, category: Category) -> Category:

        row = self._build_row(category)

        stmt = insert(CategoryModel).values(**row)

        stmt = (
            stmt.on_conflict_do_update(
                constraint=["uq_categories_id_semantic_hash"],
                set_=self._build_update_map(stmt),
            )
            .returning(CategoryModel)
        )

        result = self.session.execute(stmt).scalar_one()
        self.session.flush()

        return self._to_entity(result)

    # -------------------------------------------------------------

    def save_batch(self, categories: list[Category]) -> list[Category]:

        if not categories:
            return []

        rows = [self._build_row(cat) for cat in categories]

        stmt = insert(CategoryModel).values(rows)

        stmt = (
            stmt.on_conflict_do_update(
                constraint="uq_categories_id_semantic_hash",
                set_=self._build_update_map(stmt),
            )
            .returning(CategoryModel)
        )

        results = self.session.execute(stmt).scalars().all()
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
    def _build_row(category: Category) -> dict:
        """
        Dynamically build persistence row from Category entity.
        Excludes init=False fields automatically.
        """

        row = {}

        for field in fields(Category):

            # Skip computed fields (init=False)
            if not field.init:
                continue

            value = getattr(category, field.name)

            # Convert tuple -> list for Postgres arrays
            if field.name == "keywords_json":
                value = list(value or [])

            row[field.name] = value

        # Persist derived field explicitly if needed
        # (safe because it is read-only in entity)
        row["semantic_hash"] = category.semantic_hash

        return row

    # -------------------------------------------------------------

    @staticmethod
    def _build_update_map(stmt) -> dict:
        """
        Dynamically build ON CONFLICT update map.
        Excludes primary key.
        """

        return {
            column.name: getattr(stmt.excluded, column.name)
            for column in CategoryModel.__table__.columns
            if column.name != "id"
        }

    # -------------------------------------------------------------

    @staticmethod
    def _to_entity(model: CategoryModel) -> Category:
        """
        Dynamic domain hydration.
        Only inject init=True fields.
        """

        init_fields = {
            field.name
            for field in fields(Category)
            if field.init
        }

        entity = Category(
            **{
                field: getattr(model, field)
                for field in init_fields
                if hasattr(model, field)
            }
        )

        return entity

    # -------------------------------------------------------------

    def _to_entities(
        self,
        models: list[CategoryModel],
    ) -> list[Category]:

        return [self._to_entity(m) for m in models]