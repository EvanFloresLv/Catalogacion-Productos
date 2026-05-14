# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import re
import logging
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------
@dataclass
class LoadCategoriesFromFileCommand:
    file_path: str
    business: str         # Optional business field for all categories
    brand: str = None     # Brand name to (BLP - Brand Landing Page)


# ---------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------
class LoadCategoriesFromFileUseCase:

    ALLOWED = [
        "catid",
        "level",
        "keywords",
        "metadescripción",
        "contra",
        "género",
        "grupo",
    ]

    BUSINESS = [
        "liverpool",
        "suburbia",
        "liverpool-blp",
        "suburbia-blp",
    ]

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

            logger.info(f"Loading categories from file: {cmd.file_path} for business: {cmd.business}")

            xls = pd.ExcelFile(cmd.file_path)
            all_categories = []

            if str(cmd.business).strip().lower() not in self.BUSINESS:
                raise ValueError(f"Invalid business: {cmd.business}. Allowed: {self.BUSINESS}")

            for sheet_name in xls.sheet_names:
                logger.info(f"Processing sheet: {sheet_name}")

                sheet = pd.read_excel(xls, sheet_name=sheet_name)
                data = self._process_data(sheet, business=cmd.business, brand=cmd.brand)

                if data:
                    all_categories.extend(data)

            if not all_categories:
                return self._empty_result()

            categories = self.load_categories_uc.execute(
                LoadCategoriesCommand(categories=all_categories)
            )

            embeddings = self.load_embeddings_uc.execute(
                LoadEmbeddingsCommand(categories=categories)
            )

            logger.info(f"Successfully loaded categories: {len(categories)}")
            logger.info(f"Successfully loaded embeddings: {len(embeddings)}")

            return {
                "categories": categories,
                "embeddings": embeddings,
            }

        except Exception as e:
            self.uow.rollback()
            raise e

    @staticmethod
    def _empty_result():
        return {
            "categories": [],
            "embeddings": [],
        }

    def _process_data(self, df: pd.DataFrame, business: str, brand: str = None) -> List[Category]:

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
                is_leaf=False,  # Will be resolved after all categories are built

                description=descripcion,
                gender=row_dict.get(gend_key, None),
                direction=None,
                brand=brand,
                article_group=group_articles,
                business=business,

                keywords=self._extract_keywords(
                    titulo, descripcion, palabras
                )
            )

            if not category:
                continue

            # Deduplicate in O(1)
            seen[cat_id] = category

        # Resolve is_leaf: a category is a leaf if no other category has it as parent
        parent_ids = {c.parent_id for c in seen.values() if c.parent_id}
        result = []
        for cat in seen.values():
            if cat.id not in parent_ids:
                # Recreate with is_leaf=True
                cat = Category.create(
                    id=cat.id,
                    name=cat.name,
                    level=cat.level,
                    parent_id=cat.parent_id,
                    is_leaf=True,
                    description=cat.description,
                    gender=cat.gender,
                    direction=cat.direction,
                    brand=cat.brand,
                    article_group=cat.article_group,
                    business=cat.business,
                    keywords=cat.keywords,
                )
            result.append(cat)

        return result


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