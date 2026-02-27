# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from dataclasses import dataclass
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.category_repository import CategoryRepository
from domain.entities.categories.category import Category


@dataclass
class CreateCategoryCommand:
    name: str
    parent_id: UUID | None


class CreateCategoryUseCase:

    def __init__(self, categories: CategoryRepository):
        self.categories = categories


    def execute(self, cmd: CreateCategoryCommand) -> Category:

        if cmd.parent_id is not None:
            parent = self.categories.get_by_id(cmd.parent_id)

            if parent is None:
                raise ValueError(f"Parent category with id {cmd.parent_id} does not exist.")

        category = Category.create(
            name=cmd.name,
            parent_id=cmd.parent_id,
        )

        self.categories.save(category)
        return category
