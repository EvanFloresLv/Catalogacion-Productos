# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
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
from domain.entities.category import Category
from domain.repositories.category_repository import CategoryRepository
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
                index_elements=["id"],
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

        print(f"Categories: {categories}")

        # Sort by level so parents are inserted before children,
        # preventing FK violations on the self-referencing parent_id.
        sorted_cats = sorted(categories, key=lambda c: c.level)

        all_results: list = []
        for level_group in self._group_by_level(sorted_cats):
            rows = [self._build_row(cat) for cat in level_group]

            stmt = insert(CategoryModel).values(rows)

            stmt = (
                stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_=self._build_update_map(stmt),
                )
                .returning(CategoryModel)
            )

            results = self.session.execute(stmt).scalars().all()
            self.session.flush()
            all_results.extend(results)

        return [self._to_entity(r) for r in all_results]


    @staticmethod
    def _group_by_level(
        sorted_categories: list[Category],
    ) -> list[list[Category]]:
        if not sorted_categories:
            return []

        groups: list[list[Category]] = []
        current_level = sorted_categories[0].level
        current_group: list[Category] = []

        for cat in sorted_categories:
            if cat.level != current_level:
                groups.append(current_group)
                current_group = []
                current_level = cat.level
            current_group.append(cat)

        if current_group:
            groups.append(current_group)

        return groups

    # ============================================================
    # Queries
    # ============================================================

    def get_all(self) -> list[Category]:
        stmt = select(CategoryModel)
        results = self.session.execute(stmt).scalars().all()
        return self._to_entities(results)

    def get_by_id(self, category_id: str) -> Category | None:
        stmt = select(CategoryModel).where(CategoryModel.id == category_id)
        result = self.session.execute(stmt).scalar_one_or_none()
        return self._to_entity(result) if result else None

    def get_by_ids(self, category_ids: list[str]) -> list[Category]:
        if not category_ids:
            return []
        stmt = select(CategoryModel).where(CategoryModel.id.in_(category_ids))
        results = self.session.execute(stmt).scalars().all()
        return self._to_entities(results)

    def get_categories_by_constraints(
        self,
        limit: int | None = None,
        **kwargs,
    ) -> list[Category]:
        stmt = select(CategoryModel)

        for key, value in kwargs.items():
            if value is not None:
                stmt = stmt.where(getattr(CategoryModel, key) == value)

        if limit is not None:
            stmt = stmt.limit(limit)

        results = self.session.execute(stmt).scalars().all()

        return self._to_entities(results)

    # ============================================================
    # Helpers
    # ============================================================

    @staticmethod
    def _build_row(category: Category) -> dict:

        model_columns = {c.name for c in CategoryModel.__table__.columns}
        row = {}

        for field in fields(Category):

            # Skip computed fields (init=False)
            if not field.init:
                continue

            # Skip fields not in the DB model
            if field.name not in model_columns:
                continue

            value = getattr(category, field.name)

            # Convert tuple -> list for Postgres arrays
            if field.name == "keywords":
                value = list(value or [])

            # Convert list -> list for Postgres JSONB
            if field.name == "group_articles":
                value = list(value) if value else None

            row[field.name] = value

        # Persist derived field explicitly
        if "semantic_hash" in model_columns:
            row["semantic_hash"] = category.semantic_hash

        return row

    # -------------------------------------------------------------

    @staticmethod
    def _build_update_map(stmt) -> dict:
        return {
            column.name: getattr(stmt.excluded, column.name)
            for column in CategoryModel.__table__.columns
            if column.name != "id"
        }

    # -------------------------------------------------------------

    @staticmethod
    def _to_entity(model: CategoryModel) -> Category:
        init_fields = {
            field.name
            for field in fields(Category)
            if field.init
        }

        kwargs: dict = {}
        for field_name in init_fields:
            if hasattr(model, field_name):
                kwargs[field_name] = getattr(model, field_name)

        return Category(**kwargs)

    # -------------------------------------------------------------

    def _to_entities(
        self,
        models: list[CategoryModel],
    ) -> list[Category]:

        return [self._to_entity(m) for m in models]