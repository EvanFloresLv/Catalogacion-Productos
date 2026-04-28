# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from dataclasses import dataclass
from typing import Dict, Any

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
import pandas as pd

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.brand import Brand

from domain.repositories.category_repository import CategoryRepository
from domain.repositories.brand_repository import BrandRepository
from domain.repositories.embedding_repository import EmbeddingRepository
from domain.services.embedding_service import EmbeddingService

from shared.kernel.unit_of_work import UnitOfWork

from application.use_cases.categories.load_categories import (
    LoadCategoriesUseCase,
    LoadCategoriesCommand,
)

from application.use_cases.embeddings.load_embeddings import (
    LoadEmbeddingsUseCase,
    LoadEmbeddingsCommand,
)
# ---------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------
@dataclass
class LoadCategoriesFromFileCommand:
    file_path: str
    brand: Brand = None  # Optional brand to assign to all categories in the file


# ---------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------
class LoadCategoriesFromFileUseCase:
    """
    Orchestrator use case that coordinates loading categories and embeddings.

    Architecture:
      - Delegates to LoadCategoriesUseCase.execute() per sheet
      - Final embedding generation aggregates all saved categories
    """

    def __init__(
        self,
        category_repository: CategoryRepository,
        brand_repository: BrandRepository,
        embedding_repository: EmbeddingRepository,
        embedding_service: EmbeddingService,
        uow: UnitOfWork,
    ):
        self.uow = uow
        self.brand_repo = brand_repository

        self.load_categories_uc = LoadCategoriesUseCase(
            repo=category_repository,
            uow=uow,
        )

        self.load_embeddings_uc = LoadEmbeddingsUseCase(
            repo=embedding_repository,
            service=embedding_service,
            uow=uow,
        )

    def execute(self, cmd: LoadCategoriesFromFileCommand) -> Dict[str, Any]:
        try:

            xls = pd.ExcelFile(cmd.file_path)
            all_categories = []

            for sheet_name in xls.sheet_names:
                sheet_cmd = LoadCategoriesCommand(
                    data=pd.read_excel(xls, sheet_name=sheet_name),
                    brand=cmd.brand,
                )

                saved = self.load_categories_uc.execute(sheet_cmd)

                if saved:
                    all_categories.extend(saved)
                    print(f"  {sheet_name}: {len(saved)} categories")

            if not all_categories:
                return self._empty_result()

            embeddings = self.load_embeddings_uc.execute(
                LoadEmbeddingsCommand(categories=all_categories)
            )

            return {
                "categories": all_categories,
                "embeddings": embeddings,
            }

        except Exception:
            self.uow.rollback()
            raise

    @staticmethod
    def _empty_result():
        return {
            "categories": [],
            "embeddings": [],
        }