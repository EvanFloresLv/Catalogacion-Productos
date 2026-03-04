
# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import re
import unicodedata
from typing import List
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy.orm import Session
import pandas as pd
import tqdm

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

    # -------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------
    def execute(self, cmd: LoadCategoriesCommand) -> None:

        xls = pd.ExcelFile(cmd.file_path)

        for sheet_name in xls.sheet_names:

            print(f"\nProcessing sheet: {sheet_name}")
            data = pd.read_excel(xls, sheet_name=sheet_name)

            # Ensure all columns are strings (prevents bool.lower() crash)
            data.columns = data.columns.map(lambda x: str(x).strip())
            lower_cols = [c.lower() for c in data.columns]
            cat_id_index = lower_cols.index("catid") if "catid" in lower_cols else None

            # -------------------------------------------------
            # Validate sheet
            # -------------------------------------------------
            if cat_id_index is None:
                print(f"Skipping sheet {sheet_name} (no 'catid').")
                continue

            if len(data.columns) < 3:
                print(f"Skipping sheet {sheet_name} (insufficient columns).")
                continue


            num_levels = min(cat_id_index, len(data.columns)) if cat_id_index else len(data.columns)
            levels = [f'level {i}' for i in range(1, num_levels + 1)]

            # Ensure the number of new column names matches the number of columns in the DataFrame
            remaining_columns = list(data.columns[len(levels):])
            data.columns = levels + remaining_columns

            # -------------------------------------------------
            # Containers per sheet
            # -------------------------------------------------
            categories: List[Category] = []
            embeddings: List[Embedding] = []
            profiles: List[CategoryProfile] = []

            last_inserted = {}

            # -------------------------------------------------
            # Process rows
            # -------------------------------------------------
            for index, row in tqdm.tqdm(
                data.iterrows(),
                total=data.shape[0],
                desc=f"Processing {sheet_name}",
            ):

                try:

                    row_dict = {
                        str(k).strip(): v
                        for k, v in row.to_dict().items()
                        if pd.notna(v)
                    }

                    if not row_dict:
                        continue

                    # ---------- Detect dynamic columns ----------
                    def find_key(keyword: str):
                        return next(
                            (k for k in row_dict.keys()
                             if keyword in k.lower()),
                            None
                        )

                    level_key = find_key("level")
                    id_key = find_key("catid")
                    name_key = find_key("level")
                    url_key = find_key("url")
                    titulo_key = find_key("título") or find_key("titulo")
                    descripcion_key = find_key("descripcion")
                    palabras_key = find_key("keyword")

                    if not level_key or not id_key:
                        continue

                    # ---------- Extract level ----------
                    level_match = re.search(r"\d+", level_key)
                    if not level_match:
                        continue

                    level = int(level_match.group())

                    name = str(row_dict.get(name_key)).strip()
                    cat_id = str(row_dict.get(id_key)).strip()

                    if not name or not cat_id:
                        continue

                    parent_id = last_inserted.get(level - 1)
                    last_inserted[level] = cat_id

                    # ---------- Clean text ----------
                    def clean_text(text):
                        text = unicodedata.normalize("NFKD", str(text))
                        text = re.sub(r"http\S+|www\S+|https\S+", "", text)
                        text = re.sub(r"\S*\.com\S*", "", text)
                        text = re.sub(r"[^a-zA-Z0-9\s_-]", "", text)
                        return text.strip()

                    titulo = clean_text(row_dict.get(titulo_key, ""))
                    descripcion = clean_text(row_dict.get(descripcion_key, ""))
                    palabras = row_dict.get(palabras_key, "")

                    if isinstance(palabras, str):
                        palabras = palabras.split(",")

                    titulo_keywords = titulo.lower().split()
                    descripcion_keywords = descripcion.lower().split()

                    all_keywords = palabras + titulo_keywords + descripcion_keywords
                    keywords = list({
                        w.strip()
                        for w in all_keywords
                        if isinstance(w, str) and w.strip()
                    })

                    # ---------- Create entities ----------
                    category = Category.create(
                        id=cat_id,
                        parent_id=parent_id,
                        name=name,
                        level=level,
                        description=descripcion,
                        url=row_dict.get(url_key),
                        brand=None,
                        direction=None,
                        business=None,
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
                        constraints=CategoryConstraints(
                            allowed_genders=[],
                            allowed_brands=[],
                            allowed_business_types=[],
                            allowed_directions=[],
                            required_keywords=keywords,
                        ),
                    )

                    categories.append(category)
                    embeddings.append(embedding)
                    profiles.append(profile)

                except Exception as e:
                    print(
                        f"Error at row {index} in {sheet_name}: {e}"
                    )
                    continue

            # -------------------------------------------------
            # GLOBAL SORT (parents first)
            # -------------------------------------------------
            print(f"Prepared {len(categories)} categories.")

            categories.sort(
                key=lambda c: (c.level, c.parent_id or "")
            )

            # Validate parents exist
            ids_set = {c.id for c in categories}
            for cat in categories:
                if cat.parent_id and cat.parent_id not in ids_set:
                    raise ValueError(
                        f"Missing parent {cat.parent_id} "
                        f"for category {cat.id}"
                    )

            # -------------------------------------------------
            # BULK INSERT (single transaction per sheet)
            # -------------------------------------------------
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

