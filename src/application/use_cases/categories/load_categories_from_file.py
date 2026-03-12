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

            # Prepare metadata structure
            metadata = {
                "data": [],           # Raw LLM responses
                "by_category": {},    # Lookup by category_id (for brand mode)
                "by_sheet": {},       # Lookup by sheet_name (for normal mode)
                "business": cmd.business,
                "brand": cmd.brand
            }

            if cmd.brand:
                # Brand mode: Process ALL CATEGORIES per sheet using predict_category_sheet_data
                print("\nBrand mode: Processing categories per sheet...\n")

                for sheet_name in sheet_categories:
                    print(f"Processing sheet: {sheet_name}")

                    # Get all categories for this sheet
                    sheet_cats = sheet_categories[sheet_name]["categories"]

                    # Build input data with category_id and keywords
                    input_data = {}
                    for cat in sheet_cats:
                        category_keywords = list(cat.keywords) if cat.keywords else []
                        if cat.description:
                            category_keywords.extend(cat.description.split())

                        input_data[cat.id] = {
                            "palabras_clave": category_keywords
                        }

                    # Get metadata from LLM for all categories in this sheet
                    self.prompt_service.load_prompt(path="./src/prompts/predict_category_sheet_data.yaml")
                    prompt = self.prompt_service.get_prompt(input_data=input_data)

                    sheet_metadata = self.llm_service.chat(
                        prompt,
                        schema=prompt.get("schema", {}),
                        mime_type="application/json"
                    )

                    # Ensure metadata is a list or dict (parse if it's a string)
                    if isinstance(sheet_metadata, str):
                        import json
                        sheet_metadata = json.loads(sheet_metadata)

                    # Store metadata both in raw list and indexed by category_id
                    if isinstance(sheet_metadata, list):
                        metadata["data"].extend(sheet_metadata)
                        # Index by category_id for easy lookup
                        for item in sheet_metadata:
                            if isinstance(item, dict) and "category_id" in item:
                                metadata["by_category"][item["category_id"]] = item
                    elif isinstance(sheet_metadata, dict):
                        metadata["data"].append(sheet_metadata)
                        if "category_id" in sheet_metadata:
                            metadata["by_category"][sheet_metadata["category_id"]] = sheet_metadata

                    print(f"  ✓ Sheet '{sheet_name}' processed ({len(sheet_cats)} categories)")

                print(f"\nTotal metadata entries: {len(metadata['data'])}\n")
            else:
                # Normal mode: Generate metadata per SHEET using predict_sheet_data
                print("\nNormal mode: Processing each sheet...\n")

                for sheet_name in sheet_categories:
                    print(f"Processing sheet: {sheet_name}")

                    # Get keywords for this sheet
                    input_data = {
                        sheet_name: {
                            "palabras_clave": list(sheet_categories[sheet_name]["all_key_words"])
                        }
                    }

                    # Get metadata from LLM for this sheet
                    self.prompt_service.load_prompt(path="./src/prompts/predict_sheet_data.yaml")
                    prompt = self.prompt_service.get_prompt(input_data=input_data)

                    sheet_metadata = self.llm_service.chat(
                        prompt,
                        schema=prompt.get("schema", {}),
                        mime_type="application/json"
                    )

                    # Ensure metadata is a list or dict (parse if it's a string)
                    if isinstance(sheet_metadata, str):
                        import json
                        sheet_metadata = json.loads(sheet_metadata)

                    # Store metadata both in raw list and indexed by sheet_name
                    if isinstance(sheet_metadata, list):
                        metadata["data"].extend(sheet_metadata)
                        # Index by sheet_name for easy lookup
                        for item in sheet_metadata:
                            if isinstance(item, dict) and "sheet_name" in item:
                                metadata["by_sheet"][item["sheet_name"]] = item
                    elif isinstance(sheet_metadata, dict):
                        metadata["data"].append(sheet_metadata)
                        if "sheet_name" in sheet_metadata:
                            metadata["by_sheet"][sheet_metadata["sheet_name"]] = sheet_metadata

                    print(f"  ✓ Sheet '{sheet_name}' processed")

                print(f"\nTotal metadata entries: {len(metadata['data'])}\n")

            print("Final metadata: ")
            for entry in metadata['data']:
                print(f"  - {entry}")

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