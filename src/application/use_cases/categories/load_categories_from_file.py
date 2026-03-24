# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import json
from dataclasses import dataclass
from typing import Dict, Any, List

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
from application.ports.llm_service import LLMService
from application.ports.prompt_service import PromptService

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


# ---------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------
@dataclass
class LoadCategoriesFromFileCommand:
    file_path: str
    business: str
    by_sheet: bool = False
    brand: bool = False  # If True, use sheet name as brand for all categories in that sheet


# ---------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------
class LoadCategoriesFromFileUseCase:

    def __init__(
        self,
        session: Session,
        category_repository: CategoryRepository,
        profiles_repository: CategoryProfileRepository,
        embedding_repository: EmbeddingRepository,
        embedding_service: EmbeddingService,
        llm_service: LLMService,
        prompt_service: PromptService,
    ):
        self.session = session

        self.load_categories_uc = LoadCategoriesUseCase(
            session=session,
            category_repository=category_repository,
        )

        self.load_embeddings_uc = LoadEmbeddingsUseCase(
            session=session,
            embedding_repository=embedding_repository,
            embedding_service=embedding_service,
        )

        self.load_profiles_uc = LoadCategoryProfilesUseCase(
            session=session,
            profiles_repository=profiles_repository,
        )

        self.llm_service = llm_service
        self.prompt_service = prompt_service

    # =============================================================
    # PUBLIC API
    # =============================================================
    def execute(self, cmd: LoadCategoriesFromFileCommand) -> Dict[str, Any]:
        try:
            sheet_categories = self._load_categories(cmd.file_path)
            categories = self._flatten_categories(sheet_categories)

            if not categories:
                return self._empty_result()

            metadata = self._build_metadata(sheet_categories, cmd)

            embeddings = self._generate_embeddings(categories)
            profiles = self._create_profiles(sheet_categories, metadata)

            return {
                "categories": categories,
                "embeddings": embeddings,
                "profiles": profiles,
            }

        except Exception:
            self.session.rollback()
            raise

    # =============================================================
    # STEP 1: LOAD CATEGORIES
    # =============================================================
    def _load_categories(self, file_path: str) -> dict:
        return self.load_categories_uc.execute(
            LoadCategoriesCommand(file_path=file_path)
        )

    def _flatten_categories(self, sheet_categories: dict) -> List:
        return [
            cat
            for sheet in sheet_categories.values()
            for cat in sheet["categories"]
        ]

    # =============================================================
    # STEP 2: METADATA
    # =============================================================
    def _build_metadata(self, sheet_categories: dict, cmd: LoadCategoriesFromFileCommand) -> dict:
        metadata = self._init_metadata(cmd)

        if cmd.by_sheet:
            self._process_by_category_mode(sheet_categories, metadata, cmd.brand)
        else:
            self._process_by_sheet_mode(sheet_categories, metadata, cmd.brand)

        return metadata

    def _init_metadata(self, cmd: LoadCategoriesFromFileCommand) -> dict:
        return {
            "data": [],
            "by_category": {},
            "by_sheet": {},
            "business": cmd.business,
        }

    # -------------------------
    # Category Mode
    # -------------------------
    def _process_by_category_mode(self, sheet_categories: dict, metadata: dict, brand: bool):

        prompt_template = self._load_prompt(
            "./src/prompts/predict_category_sheet_data.yaml"
        )

        for sheet_name, sheet_data in sheet_categories.items():
            input_data = self._build_category_input(sheet_data["categories"])

            response = self._call_llm(prompt_template, input_data)

            self._store_metadata(
                response,
                metadata,
                key="category_id",
                sheet_name=sheet_name,
                brand=brand,
            )

    # -------------------------
    # Sheet Mode
    # -------------------------
    def _process_by_sheet_mode(self, sheet_categories: dict, metadata: dict, brand: bool):

        prompt_template = self._load_prompt(
            "./src/prompts/predict_sheet_data.yaml"
        )

        for sheet_name, sheet_data in sheet_categories.items():
            input_data = {
                sheet_name: {
                    "palabras_clave": list(sheet_data["all_key_words"])
                }
            }

            response = self._call_llm(prompt_template, input_data)

            self._store_metadata(
                response,
                metadata,
                key="sheet_name",
                sheet_name=sheet_name,
                brand=brand,
            )

    # =============================================================
    # INPUT BUILDERS
    # =============================================================
    def _build_category_input(self, categories) -> dict:
        result = {}

        for cat in categories:
            keywords = list(cat.keywords or [])

            if cat.description:
                keywords.extend(cat.description.split())

            result[cat.id] = {
                "palabras_clave": keywords
            }

        return result

    # =============================================================
    # LLM + PROMPT HANDLING
    # =============================================================
    def _load_prompt(self, path: str):
        self.prompt_service.load_prompt(path=path)
        return self.prompt_service

    def _call_llm(self, prompt_template, input_data: dict):
        prompt = prompt_template.get_prompt(input_data=input_data)

        response = self.llm_service.chat(
            prompt,
            schema=prompt.get("schema", {}),
            mime_type="application/json",
        )

        return self._parse_json(response)

    def _parse_json(self, data):
        if isinstance(data, str):
            return json.loads(data)
        return data

    # =============================================================
    # METADATA STORAGE
    # =============================================================
    def _store_metadata(
        self,
        response,
        metadata: dict,
        key: str,
        sheet_name: str | None = None,
        brand: bool = False,
    ):
        items = response if isinstance(response, list) else [response]

        for item in items:
            if not isinstance(item, dict):
                continue

            if brand and sheet_name:
                item["sheet_name"] = sheet_name

            metadata["data"].append(item)

            # Indexing
            if key == "category_id" and "category_id" in item:
                metadata["by_category"][item["category_id"]] = item

            if "sheet_name" in item:
                metadata["by_sheet"][item["sheet_name"]] = item

    # =============================================================
    # STEP 3: EMBEDDINGS
    # =============================================================
    def _generate_embeddings(self, categories):
        return self.load_embeddings_uc.execute(
            LoadEmbeddingsCommand(categories=categories)
        )

    # =============================================================
    # STEP 4: PROFILES
    # =============================================================
    def _create_profiles(self, sheet_categories, metadata):
        return self.load_profiles_uc.execute(
            LoadCategoryProfilesCommand(
                categories_by_sheet=sheet_categories,
                metadata=metadata,
            )
        )

    # =============================================================
    # HELPERS
    # =============================================================
    def _empty_result(self):
        return {
            "categories": [],
            "embeddings": [],
            "profiles": [],
        }