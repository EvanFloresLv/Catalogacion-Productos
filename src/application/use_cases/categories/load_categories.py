# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from typing import List
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.category import Category

from domain.repositories.category_repository import CategoryRepository
from domain.aggregates.category_catalog import CategoryCatalog

from shared.kernel.unit_of_work import UnitOfWork


# -------------------------------------------------------------
# Command
# -------------------------------------------------------------
@dataclass
class LoadCategoriesCommand:
    categories: List[Category]


# -------------------------------------------------------------
# Use Case
# -------------------------------------------------------------
class LoadCategoriesUseCase:

    def __init__(self, repo: CategoryRepository, uow: UnitOfWork):
        self.repo = repo
        self.uow = uow

    # =========================================================
    # PUBLIC
    # =========================================================
    def execute(self, cmd: LoadCategoriesCommand) -> List[Category]:

        catalog = CategoryCatalog()
        self.uow.register(catalog)

        catalog.add_categories_batch(cmd.categories)

        catalog.enhance_keywords_from_parents()
        _ = self.repo.save_batch(catalog.categories)

        self.uow.commit()

        return catalog.categories
