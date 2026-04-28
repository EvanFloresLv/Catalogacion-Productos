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
from domain.entities.brand import Brand

from domain.repositories.category_repository import CategoryRepository
from domain.aggregates.category_catalog import CategoryCatalog

from shared.kernel.unit_of_work import UnitOfWork


# -------------------------------------------------------------
# Command
# -------------------------------------------------------------
@dataclass
class LoadCategoriesCommand:
    data: pd.DataFrame
    brand: Brand = None


# -------------------------------------------------------------
# Use Case
# -------------------------------------------------------------
class LoadCategoriesUseCase:

    ALLOWED = [
        "catid",
        "level",
        "keywords",
        "metadescripción",
        "contra",
        "género",
        "grupo",
    ]

    def __init__(self, repo: CategoryRepository, uow: UnitOfWork):
        self.repo = repo
        self.uow = uow

    # =========================================================
    # PUBLIC
    # =========================================================
    def execute(self, cmd: LoadCategoriesCommand) -> Dict[str, Any]:
        categories = self._process_data(cmd.data, cmd.brand)
        if not categories:
            return None
        return self.persist(categories)

    def persist(self, categories: List[Category]) -> List[Category]:

        catalog = CategoryCatalog()
        self.uow.register(catalog)

        catalog.add_categories_batch(categories)
        catalog.enhance_keywords_from_parents()

        sorted_categories = sorted(catalog.categories, key=lambda c: c.level)
        saved = self.repo.save_batch(sorted_categories)

        self.uow.commit()

        return saved

    # =========================================================
    # CORE PARSING
    # =========================================================
    def _process_data(self, df: pd.DataFrame, brand: Brand = None) -> List[Category]:

        df = df.dropna(how="all").dropna(how="all", axis=1)  # Drop empty rows and columns

        if df.empty:
            return []

        df.columns = [str(c).replace(" ", "_").strip() for c in df.columns]

        lower_cols = [c.lower() for c in df.columns]

        if "catid" not in lower_cols:
            return []

        cat_idx = lower_cols.index("catid")
        df.columns = (
            [f"level_{i}" for i in range(1, cat_idx + 1)]
            + list(df.columns[cat_idx:])
        )

        df.columns = [c.lower() for c in df.columns]

        columns_to_delete = [
            col for col in df.columns
            if not any(keyword in col for keyword in self.ALLOWED)
        ]

        df.drop(columns=columns_to_delete, inplace=True)

        max_level = max(
                int(col.split("_")[-1]) for col in df.columns
                if col.startswith("level_")
            ) if df.columns.str.startswith("level_").any() else 0

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
            ga_key = self._find(row_dict, "artículos")
            gend_key = self._find(row_dict, "género")

            group_articles = self._get_group_articles(row_dict.get(ga_key, None)) if ga_key else None

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
                keywords=LoadCategoriesUseCase._extract_keywords(
                    titulo, descripcion, palabras
                ),
                gender=row_dict.get(gend_key, None),
                group_articles=group_articles,
                direction=None,
                brand=brand,
                is_leaf=(level == max_level)
            )

            # Deduplicate in O(1)
            seen[cat_id] = category

        result = list(seen.values())

        return result

    # =============================================================
    # HELPERS
    # =============================================================

    @staticmethod
    def _extract_keywords(
        titulo: str,
        descripcion: str,
        palabras: Any,
    ) -> List[str]:
        pattern = r"[A-Za-zÁÉÍÓÚáéíóúÑñ]+"
        extracted = []

        # Words parsing (can be JSON string, list, etc.)
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
    def _get_group_articles(groups):
        groups = groups.split(",")
        group_nums = []
        seen = set()

        for g in groups:
            num = re.search(r'\d+', g.strip())
            if num and num.group() not in seen:
                seen.add(num.group())
                group_nums.append(num.group())

        return group_nums

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