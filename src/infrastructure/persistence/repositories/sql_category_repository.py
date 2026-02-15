# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy import select
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.categories.category import Category
from application.ports.outbound.category_repository import CategoryRepository
from infrastructure.persistence.models.category_model import CategoryModel
from infrastructure.persistence.utils.uuid import uuid_to_bytes, bytes_to_uuid


class SQLCategoryRepository(CategoryRepository):

    def __init__(self, session: Session):
        self.session = session


    def save(self, category: Category) -> None:

        model = CategoryModel(
            id=uuid_to_bytes(category.id),
            name=category.name,
            parent_id=uuid_to_bytes(category.parent_id) if category.parent_id else None
        )

        self.session.merge(model)
        self.session.commit()


    def get_all(self) -> list[Category]:

        stmt = select(CategoryModel)
        result = self.session.execute(stmt).scalars().all()

        return [
            Category(
                id=bytes_to_uuid(item.id),
                name=item.name,
                parent_id=bytes_to_uuid(item.parent_id) if item.parent_id else None
            )
            for item in result
        ]


    def get_by_id(self, category_id) -> Category | None:

        result = self.session.get(CategoryModel, uuid_to_bytes(category_id))

        if result is None:
            return None

        return Category(
            id=bytes_to_uuid(result.id),
            name=result.name,
            parent_id=bytes_to_uuid(result.parent_id) if result.parent_id else None
        )