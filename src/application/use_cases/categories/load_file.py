# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import re
import unicodedata
from typing import List, Dict, Any
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy.orm import Session
import pandas as pd
from tqdm import tqdm

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.categories.category import Category
from domain.entities.categories.category_constraints import CategoryConstraints
from domain.entities.categories.category_profile import CategoryProfile
from domain.entities.embeddings.embedding import Embedding
from domain.value_objects.semantic_hash import SemanticHash

from application.ports.category_repository import CategoryRepository
from application.ports.category_profile_repository import CategoryProfileRepository
from application.ports.embedding_repository import EmbeddingRepository
from application.ports.embedding_service import EmbeddingService

from utils.json import json_to_set


# ---------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------
@dataclass
class LoadCategoriesCommand:
    file_path: str


# ---------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------
class LoadCategoriesFileUseCase:

    def __init__(
        self,
        session: Session,
        category_repository: CategoryRepository,
        profiles_repository: CategoryProfileRepository,
        embedding_repository: EmbeddingRepository,
        embedding_service: EmbeddingService,
    ):
        self.session = session
        self.category_repository = category_repository
        self.profiles_repository = profiles_repository
        self.embedding_repository = embedding_repository
        self.embedding_service = embedding_service

    # =============================================================
    # PUBLIC API
    # =============================================================
    def execute(self, cmd: LoadCategoriesCommand) -> None:

        xls = pd.ExcelFile(cmd.file_path)

        for sheet_name in xls.sheet_names:
            print(f"\nProcessing sheet: {sheet_name}")

            df = self._prepare_dataframe(xls, sheet_name)

            if df is None:
                continue

            categories, embeddings, profiles = self._process_sheet(df)

            self._validate_parent_integrity(categories)

            self._commit_sheet(
                sheet_name,
                categories,
                embeddings,
                profiles,
            )

    # =============================================================
    # PREPARATION
    # =============================================================
    def _prepare_dataframe(
        self,
        xls: pd.ExcelFile,
        sheet_name: str,
    ) -> pd.DataFrame | None:

        df = pd.read_excel(xls, sheet_name=sheet_name)

        if df.empty or len(df.columns) < 3:
            print(f"Skipping sheet {sheet_name} (invalid structure).")
            return None

        df.columns = df.columns.map(lambda x: str(x).strip())

        lower_cols = [c.lower() for c in df.columns]
        if "catid" not in lower_cols:
            print(f"Skipping sheet {sheet_name} (no 'catid').")
            return None

        cat_id_index = lower_cols.index("catid")
        level_count = cat_id_index

        levels = [f"level {i}" for i in range(1, level_count + 1)]
        remaining = list(df.columns[level_count:])

        df.columns = levels + remaining

        return df

    # =============================================================
    # SHEET PROCESSING
    # =============================================================
    def _process_sheet(
        self,
        df: pd.DataFrame,
    ) -> tuple[List[Category], List[Embedding], List[CategoryProfile]]:

        categories: List[Category] = []
        embeddings: List[Embedding] = []
        profiles: List[CategoryProfile] = []

        last_inserted: Dict[int, str] = {}

        for _, row in tqdm(
            df.iterrows(),
            total=df.shape[0],
            desc="Processing rows",
        ):
            row_dict = self._clean_row(row)
            if not row_dict:
                continue

            parsed = self._parse_row(row_dict, last_inserted)
            if not parsed:
                continue

            category, embedding, profile = parsed

            categories.append(category)
            embeddings.append(embedding)
            profiles.append(profile)

        categories.sort(key=lambda c: (c.level, c.parent_id or ""))

        print(f"Prepared {len(categories)} categories.")
        return categories, embeddings, profiles

    # =============================================================
    # ROW PARSING
    # =============================================================
    def _clean_row(self, row: pd.Series) -> Dict[str, Any]:
        return {
            str(k).strip(): v
            for k, v in row.to_dict().items()
            if pd.notna(v)
        }

    def _parse_row(
        self,
        row_dict: Dict[str, Any],
        last_inserted: Dict[int, str],
    ) -> tuple[Category, Embedding, CategoryProfile] | None:

        level_key = self._find_key(row_dict, "level")
        id_key = self._find_key(row_dict, "catid")

        if not level_key or not id_key:
            return None

        level = self._extract_level(level_key)
        if not level:
            return None

        name = str(row_dict.get(level_key)).strip()
        cat_id = str(row_dict.get(id_key)).strip()

        if not name or not cat_id:
            return None

        parent_id = last_inserted.get(level - 1)
        last_inserted[level] = cat_id

        titulo = self._clean_text(row_dict.get(
            self._find_key(row_dict, "titulo") or "", ""
        ))
        descripcion = self._clean_text(row_dict.get(
            self._find_key(row_dict, "descripcion") or "", ""
        ))

        palabras = row_dict.get(self._find_key(row_dict, "keyword"), "")
        keywords = self._extract_keywords(titulo, descripcion, palabras)

        category = Category.create(
            id=cat_id,
            parent_id=parent_id,
            name=name,
            level=level,
            description=descripcion,
            url=row_dict.get(self._find_key(row_dict, "url")),
            keywords_json=json_to_set(keywords),
        )

        embedding_text = category.to_embedding_text()

        embedding = Embedding.create(
            category_id=cat_id,
            vector=self.embedding_service.generate(embedding_text),
            content_hash=SemanticHash.from_text(
                embedding_text
            ).value,
        )

        profile = CategoryProfile.create(
            category=category,
            constraints=CategoryConstraints(),
        )

        return category, embedding, profile

    # =============================================================
    # HELPERS
    # =============================================================
    @staticmethod
    def _find_key(data: Dict[str, Any], keyword: str) -> str | None:
        return next(
            (k for k in data.keys() if keyword in k.lower()),
            None,
        )

    @staticmethod
    def _extract_level(key: str) -> int | None:
        match = re.search(r"\d+", key)
        return int(match.group()) if match else None

    @staticmethod
    def _clean_text(text: Any) -> str:
        text = unicodedata.normalize("NFKD", str(text))
        text = re.sub(r"http\S+|www\S+|https\S+", "", text)
        text = re.sub(r"\S*\.com\S*", "", text)
        text = re.sub(r"[^a-zA-Z0-9\s_-]", "", text)
        return text.strip()

    @staticmethod
    def _extract_keywords(
        titulo: str,
        descripcion: str,
        palabras: Any,
    ) -> List[str]:

        if isinstance(palabras, str):
            palabras = palabras.split(",")

        palabras = palabras or []

        all_words = (
            palabras
            + titulo.lower().split()
            + descripcion.lower().split()
        )

        return list({
            w.strip()
            for w in all_words
            if isinstance(w, str) and w.strip()
        })

    @staticmethod
    def _validate_parent_integrity(categories: List[Category]) -> None:
        ids_set = {c.id for c in categories}

        for cat in categories:
            if cat.parent_id and cat.parent_id not in ids_set:
                raise ValueError(
                    f"Missing parent {cat.parent_id} "
                    f"for category {cat.id}"
                )

    # =============================================================
    # TRANSACTION
    # =============================================================
    def _commit_sheet(
        self,
        sheet_name: str,
        categories: List[Category],
        embeddings: List[Embedding],
        profiles: List[CategoryProfile],
    ) -> None:

        try:
            self.category_repository.save_batch(categories)
            self.embedding_repository.save_batch(embeddings)
            self.profiles_repository.save_batch(profiles)

            self.session.commit()
            print(f"Sheet {sheet_name} committed successfully.")

        except Exception as e:
            self.session.rollback()
            print(f"Rollback sheet {sheet_name}: {e}")
            raise