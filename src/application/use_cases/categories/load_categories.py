# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import re
import json
import unicodedata
from typing import List, Dict, Any
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
import pandas as pd

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
    file_path: str


# -------------------------------------------------------------
# Use Case (Simplified)
# -------------------------------------------------------------
class LoadCategoriesUseCase:

    def __init__(self, repo: CategoryRepository, uow: UnitOfWork):
        self.repo = repo
        self.uow = uow

    # =========================================================
    # PUBLIC
    # =========================================================
    def execute(self, cmd: LoadCategoriesCommand) -> Dict[str, Any]:

        xls = pd.ExcelFile(cmd.file_path)

        catalog = CategoryCatalog()

        self.uow.register(catalog)

        all_categories: Dict[str, Dict[str, Any]] = {}

        for sheet in xls.sheet_names:
            categories = self._parse_sheet(xls, sheet)

            if not categories:
                continue

            catalog.add_categories_batch(categories)

            all_categories[sheet] = {
                "categories": categories,
                "all_key_words": {
                    kw for c in categories for kw in (c.keywords or [])
                },
            }

        # Aggregate-level logic
        catalog.enhance_keywords_from_parents()

        # Persist ordered
        sorted_categories = sorted(catalog.categories, key=lambda c: c.level)
        saved = self.repo.save_batch(sorted_categories)

        self.uow.commit()

        return saved

    # =========================================================
    # CORE PARSING (SIMPLIFIED)
    # =========================================================
    def _parse_sheet(self, xls: pd.ExcelFile, sheet: str) -> List[Category]:

        df = pd.read_excel(xls, sheet_name=sheet)
        df = df.dropna(how="all").dropna(how="all", axis=1)  # Drop empty rows and columns

        if df.empty:
            return []

        df.columns = [str(c).strip() for c in df.columns]

        lower_cols = [c.lower() for c in df.columns]
        if "catid" not in lower_cols:
            return []

        cat_idx = lower_cols.index("catid")
        df.columns = (
            [f"level_{i}" for i in range(1, cat_idx + 1)]
            + list(df.columns[cat_idx:])
        )

        last_parent: Dict[int, str] = {}
        seen: Dict[str, Category] = {}

        for row in df.itertuples(index=False):

            row_dict = {
                k: v for k, v in row._asdict().items() if pd.notna(v)
            }

            level_key = next((k for k in row_dict if "level" in k), None)
            id_key = next((k for k in row_dict if "catid" in k.lower()), None)

            if not level_key or not id_key:
                continue

            level = int(re.search(r"\d+", level_key).group())
            name = str(row_dict[level_key]).strip()
            cat_id = str(row_dict[id_key]).strip()

            if not name or not cat_id:
                continue

            parent_id = last_parent.get(level - 1)
            last_parent[level] = cat_id

            meta_key = self._find(row_dict, "meta")
            desc_key = self._find(row_dict, "descripcion")
            kw_key = self._find(row_dict, "keyword")

            titulo = self._clean(row_dict.get(meta_key, "")) if meta_key else ""
            descripcion = self._clean(row_dict.get(desc_key, "")) if desc_key else ""

            palabras = row_dict.get(kw_key, []) if kw_key else []
            if isinstance(palabras, str):
                try:
                    palabras = json.loads(palabras)
                except json.JSONDecodeError:
                    palabras = [palabras]

            category = Category.create(
                id=cat_id,
                name=name,
                level=level,
                parent_id=parent_id,
                description=descripcion,
                keywords=LoadCategoriesUseCase._extract_keywords(
                    titulo, descripcion, palabras
                ),
            )

            # Deduplicate in O(1)
            seen[cat_id] = category

        result = list(seen.values())
        print(f"{sheet}: {len(result)} categories")

        return result

    @staticmethod
    def _extract_keywords(
        titulo: str,
        descripcion: str,
        palabras: Any,
    ) -> List[str]:
        pattern = r"[A-Za-zÁÉÍÓÚáéíóúÑñ]+"
        extracted = []

        # Parse palabras (can be JSON string, list, etc.)
        if isinstance(palabras, str):
            try:
                palabras = json.loads(palabras)
            except Exception:
                palabras = [palabras]

        if isinstance(palabras, (list, tuple, set)):
            for p in palabras:
                if isinstance(p, str):
                    extracted.extend(re.findall(pattern, p.lower()))

        extracted.extend(re.findall(pattern, titulo.lower()))
        extracted.extend(re.findall(pattern, descripcion.lower()))

        return list(dict.fromkeys(extracted))

    @staticmethod
    def _clean(x):
        x = unicodedata.normalize("NFKD", str(x))
        x = re.sub(r"http\S+|www\S+", "", x)
        x = re.sub(r"[^a-zA-Z0-9\s_-]", "", x)
        return x.strip().lower()

    @staticmethod
    def _find(row_dict, keyword):
        return next(
            (k for k in row_dict if keyword in k.lower()), None
        )