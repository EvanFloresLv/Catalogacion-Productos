# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.category_repository import CategoryRepository
from application.ports.category_profile_repository import CategoryProfileRepository
from application.ports.embedding_repository import EmbeddingRepository
from application.ports.embedding_service import EmbeddingService

from application.use_cases.categories.load_categories import (
    LoadCategoriesUseCase,
    LoadCategoriesCommand,
)
from application.use_cases.embeddings.load_embeddings import (
    LoadEmbeddingsUseCase,
    LoadEmbeddingsCommand,
)
from application.use_cases.category_profiles.load_profiles import (
    LoadCategoryProfilesUseCase,
    LoadCategoryProfilesCommand,
)

from application.ports.llm_service import LLMService
from application.ports.prompt_service import PromptService


# ---------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------
@dataclass
class LoadCategoriesFromFileCommand:
    file_path: str
    business: str        # Business name to apply to all profiles
    brand: bool = False  # If True, use sheet name as brand


# ---------------------------------------------------------------------
# Orchestrator Use Case
# ---------------------------------------------------------------------
class LoadCategoriesFromFileUseCase:
    """
    Orchestrates the loading of categories, embeddings, and profiles from an Excel file.
    This use case coordinates three sub-use cases:
    1. LoadCategoriesUseCase - Parse and save categories
    2. LoadEmbeddingsUseCase - Generate and save embeddings
    3. LoadCategoryProfilesUseCase - Create and save profiles
    """

    def __init__(
        self,
        session: Session,
        category_repository: CategoryRepository,
        profiles_repository: CategoryProfileRepository,
        embedding_repository: EmbeddingRepository,
        embedding_service: EmbeddingService,
        llm_service: LLMService,
        prompt_service: PromptService
    ):
        self.session = session

        # Initialize sub-use cases
        self.load_categories_use_case = LoadCategoriesUseCase(
            session=session,
            category_repository=category_repository,
        )

        self.load_embeddings_use_case = LoadEmbeddingsUseCase(
            session=session,
            embedding_repository=embedding_repository,
            embedding_service=embedding_service,
        )

        self.load_profiles_use_case = LoadCategoryProfilesUseCase(
            session=session,
            profiles_repository=profiles_repository,
        )

        self.llm_service = llm_service
        self.prompt_service = prompt_service

    # =============================================================
    # PUBLIC API
    # =============================================================
    def execute(self, cmd: LoadCategoriesFromFileCommand) -> dict:
        """
        Load categories from Excel file and create embeddings and profiles.

        Args:
            cmd.file_path: Path to Excel file
            cmd.business: Business name to apply to all profiles (e.g., "Liverpool")
            cmd.brand: If True, use sheet names as brand names for categories

        Returns:
            dict with keys: categories, embeddings, profiles
        """
        try:
            # Step 1: Load categories
            print("\n" + "="*60)
            print("STEP 1: Loading Categories")
            print("="*60)
            sheet_categories: dict = self.load_categories_use_case.execute(
                LoadCategoriesCommand(
                    file_path=cmd.file_path,
                )
            )

            categories = [cat for sheet in sheet_categories.values() for cat in sheet["categories"]]

            # Prepare input data for LLM (keywords by sheet)
            input_data = {
                sheet_name: list(sheet_categories[sheet_name]["all_key_words"])
                for sheet_name in sheet_categories
            }

            # Get metadata from LLM (only if not using brand mode)
            metadata = {
                "data": [],
                "business": cmd.business,
                "brand": cmd.brand
            }

            if not cmd.brand:
                # Only call LLM if not in brand mode
                prompt = self.prompt_service.get_prompt(input_data=input_data)
                metadata["data"] = self.llm_service.chat(
                    prompt,
                    schema=prompt.get("schema", {}),
                    mime_type="application/json"
                )
                print(f"\nMetadata by sheet: {metadata['data']}\n")
            else:
                print("\nBrand mode: Using sheet names as brands\n")

            if not categories:
                print("No categories loaded. Exiting.")
                return {
                    "categories": [],
                    "embeddings": [],
                    "profiles": [],
                }

            # Step 2: Generate embeddings
            print("\n" + "="*60)
            print("STEP 2: Generating Embeddings")
            print("="*60)
            embeddings = self.load_embeddings_use_case.execute(
                LoadEmbeddingsCommand(categories=categories)
            )

            # Step 3: Create profiles with metadata
            print("\n" + "="*60)
            print("STEP 3: Creating Profiles")
            print("="*60)
            profiles = self.load_profiles_use_case.execute(
                LoadCategoryProfilesCommand(
                    categories_by_sheet=sheet_categories,
                    metadata=metadata
                )
            )

            print("\n" + "="*60)
            print("COMPLETED SUCCESSFULLY")
            print("="*60)
            print(f"Total: {len(categories)} categories, {len(embeddings)} embeddings, {len(profiles)} profiles")

            return {
                "categories": categories,
                "embeddings": embeddings,
                "profiles": profiles,
            }

        except Exception as e:
            self.session.rollback()
            print(f"\n✗ ERROR: {e}")
            raise