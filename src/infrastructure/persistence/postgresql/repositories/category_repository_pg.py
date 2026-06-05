# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from collections import defaultdict
from dataclasses import fields

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import select, union_all, literal_column, bindparam, text, or_
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
        gender: str | None = None,
        direction: str | None = None,
        business: str | None = None,
        brand: str | None = None,
        is_leaf: bool | None = None,
        article_group: list[str] | None = None,
        limit: int | None = None,
    ) -> list[Category]:
        stmt = select(CategoryModel)

        if article_group:
            stmt = stmt.where(
                or_(*(CategoryModel.article_group.contains([ag]) for ag in article_group))
            )
        if gender is not None:
            stmt = stmt.where(CategoryModel.gender == gender)
        if direction is not None:
            stmt = stmt.where(CategoryModel.direction == direction)
        if business is not None:
            stmt = stmt.where(CategoryModel.business == business)
        if brand is not None:
            stmt = stmt.where(CategoryModel.brand == brand)
        if is_leaf is not None:
            stmt = stmt.where(CategoryModel.is_leaf == is_leaf)
        if limit is not None:
            stmt = stmt.limit(limit)

        results = self.session.execute(stmt).scalars().all()
        return self._to_entities(results)

    def get_categories_by_cascade(
        self,
        *,
        business: str,
        brand: str | None = None,
        gender: str | None = None,
        article_group: list[str] | None = None,
        is_leaf: bool = True,
        per_strategy_limit: int | None = None,
    ) -> list[tuple[int, Category]]:

        base_filters = [CategoryModel.business == business, CategoryModel.is_leaf == is_leaf]
        if brand is not None:
            base_filters.append(CategoryModel.brand == brand)

        selects: list = []

        # Strategy 1: article_group + gender + brand + business
        if article_group and gender is not None and brand is not None:
            stmt_1 = select(
                CategoryModel.id.label("id"),
                CategoryModel.name.label("name"),
                CategoryModel.level.label("level"),
                CategoryModel.parent_id.label("parent_id"),
                CategoryModel.is_leaf.label("is_leaf"),
                CategoryModel.gender.label("gender"),
                CategoryModel.direction.label("direction"),
                CategoryModel.brand.label("brand"),
                CategoryModel.article_group.label("article_group"),
                CategoryModel.business.label("business"),
                CategoryModel.semantic_hash.label("semantic_hash"),
                CategoryModel.keywords.label("keywords"),
            ).where(
                *base_filters,
                or_(*(CategoryModel.article_group.contains([ag]) for ag in article_group)),
                CategoryModel.gender == gender,
            )
            stmt_1 = stmt_1.column_literal_value if False else stmt_1  # keep select
            selects.append((1, stmt_1.add_columns()) if False else (1, stmt_1))  # type: ignore[arg-type]

        # Strategy 2: article_group + brand + business
        if article_group and brand is not None:
            stmt_2 = (
                select(
                    CategoryModel.id,
                    CategoryModel.name,
                    CategoryModel.level,
                    CategoryModel.parent_id,
                    CategoryModel.is_leaf,
                    CategoryModel.gender,
                    CategoryModel.direction,
                    CategoryModel.brand,
                    CategoryModel.article_group,
                    CategoryModel.business,
                    CategoryModel.semantic_hash,
                    CategoryModel.keywords,
                )
                .where(*base_filters, or_(*(CategoryModel.article_group.contains([ag]) for ag in article_group)))
            )
            selects.append((2, stmt_2))

        # Strategy 3: gender + brand + business
        if gender is not None and brand is not None:
            stmt_3 = (
                select(
                    CategoryModel.id,
                    CategoryModel.name,
                    CategoryModel.level,
                    CategoryModel.parent_id,
                    CategoryModel.is_leaf,
                    CategoryModel.gender,
                    CategoryModel.direction,
                    CategoryModel.brand,
                    CategoryModel.article_group,
                    CategoryModel.business,
                    CategoryModel.semantic_hash,
                    CategoryModel.keywords,
                )
                .where(*base_filters, CategoryModel.gender == gender)
            )
            selects.append((3, stmt_3))

        # Strategy 4: brand + business
        if brand is not None:
            stmt_4 = (
                select(
                    CategoryModel.id,
                    CategoryModel.name,
                    CategoryModel.level,
                    CategoryModel.parent_id,
                    CategoryModel.is_leaf,
                    CategoryModel.gender,
                    CategoryModel.direction,
                    CategoryModel.brand,
                    CategoryModel.article_group,
                    CategoryModel.business,
                    CategoryModel.semantic_hash,
                    CategoryModel.keywords,
                )
                .where(*base_filters)
            )
            selects.append((4, stmt_4))

        # Strategy 5: business only (broadest, only when no brand)
        if brand is None:
            stmt_5 = (
                select(
                    CategoryModel.id,
                    CategoryModel.name,
                    CategoryModel.level,
                    CategoryModel.parent_id,
                    CategoryModel.is_leaf,
                    CategoryModel.gender,
                    CategoryModel.direction,
                    CategoryModel.brand,
                    CategoryModel.article_group,
                    CategoryModel.business,
                    CategoryModel.semantic_hash,
                    CategoryModel.keywords,
                )
                .where(
                    CategoryModel.business == business,
                    CategoryModel.is_leaf == is_leaf,
                )
            )
            selects.append((5, stmt_5))

        if not selects:
            return []

        # Single connection round-trip with UNION ALL for all strategies.
        annotated: list = []

        for priority, stmt in selects:
            priority_col = literal_column(str(priority)).label("priority")
            annotated.append(stmt.add_columns(priority_col))

        union_stmt = union_all(*annotated)
        results = self.session.execute(union_stmt).all()

        # Dedupe by id, keep the lowest priority (best) match.
        best: dict[str, tuple[int, Category]] = {}
        for row in results:
            priority = int(row.priority)
            cat = self._row_to_entity(row)
            existing = best.get(cat.id)
            if existing is None or priority < existing[0]:
                best[cat.id] = (priority, cat)

        ordered = sorted(best.values(), key=lambda x: (x[0], x[1].id))

        if per_strategy_limit is not None:
            # keep at most N per priority level
            per_level: dict[int, list[Category]] = defaultdict(list)
            for priority, cat in ordered:
                if len(per_level[priority]) < per_strategy_limit:
                    per_level[priority].append(cat)
            flat: list[tuple[int, Category]] = []
            for priority, _ in sorted({p for p, _ in ordered}):
                flat.extend((priority, c) for c in per_level[priority])
            return flat

        return ordered

    def get_all_category_paths(self) -> dict[str, str]:
        sql = text(
            """
            WITH RECURSIVE cat_tree AS (
                SELECT
                    id,
                    name,
                    parent_id,
                    name::text AS path,
                    1 AS depth
                FROM categories
                WHERE parent_id IS NULL
                UNION ALL
                SELECT
                    c.id,
                    c.name,
                    c.parent_id,
                    ct.path || ' > ' || c.name,
                    ct.depth + 1
                FROM categories c
                JOIN cat_tree ct ON c.parent_id = ct.id
            )
            SELECT id, path FROM cat_tree
            """
        )

        rows = self.session.execute(sql).all()
        return {row.id: row.path for row in rows}

    def get_category_paths_by_ids(
        self, category_ids: list[str]
    ) -> dict[str, str]:
        if not category_ids:
            return {}

        sql = text(
            """
            WITH RECURSIVE cat_tree AS (
                SELECT
                    id,
                    name,
                    parent_id,
                    name::text AS path,
                    1 AS depth
                FROM categories
                WHERE parent_id IS NULL
                UNION ALL
                SELECT
                    c.id,
                    c.name,
                    c.parent_id,
                    ct.path || ' > ' || c.name,
                    ct.depth + 1
                FROM categories c
                JOIN cat_tree ct ON c.parent_id = ct.id
            )
            SELECT id, path FROM cat_tree
            WHERE id IN :ids
            """
        ).bindparams(bindparam("ids", expanding=True))

        rows = self.session.execute(sql, {"ids": list(category_ids)}).all()
        return {row.id: row.path for row in rows}

    @staticmethod
    def _row_to_entity(row) -> Category:
        try:
            model = row
            return Category(
                id=model.id,
                name=model.name,
                level=model.level,
                parent_id=model.parent_id,
                is_leaf=model.is_leaf,
                gender=model.gender,
                direction=model.direction,
                brand=model.brand,
                article_group=list(model.article_group) if model.article_group else None,
                business=model.business,
                semantic_hash=model.semantic_hash,
                keywords=tuple(model.keywords) if model.keywords else (),
            )
        except Exception:
            data = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
            return Category(
                id=data.get("id"),
                name=data.get("name"),
                level=data.get("level"),
                parent_id=data.get("parent_id"),
                is_leaf=data.get("is_leaf"),
                gender=data.get("gender"),
                direction=data.get("direction"),
                brand=data.get("brand"),
                article_group=list(data.get("article_group") or []) or None,
                business=data.get("business"),
                semantic_hash=data.get("semantic_hash") or "",
                keywords=tuple(data.get("keywords") or ()),
            )

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
            if field.name == "article_group":
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