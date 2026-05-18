# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import logging
import re
from dataclasses import dataclass
from typing import Any, Iterable, List

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
import pandas as pd
import nltk
from nltk.corpus import stopwords

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.use_cases.products.load_products import (
    LoadProductsCommand,
    LoadProductsUseCase,
)
from domain.entities.product import Product
from domain.repositories.product_repository import ProductRepository
from shared.kernel.unit_of_work import UnitOfWork

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


nltk.download("stopwords")


# ---------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------
@dataclass
class LoadProductsFromFileCommand:
    file_path: str


# ---------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------
class LoadProductsFromFileUseCase:

    TARGETS = [
        "Código SKU",
        "Negocio",
        "Nombre",
        "Dirección",
        "Sección",
        "Grupo",
        "Marca",
        "Género",
        "Disciplina",
        "Título corto",
        "Keywords",
        "ProductTypeSAP",
    ]

    STOPWORDS = set(stopwords.words("spanish"))

    # -----------------------------------------------------------------
    # Constructor
    # -----------------------------------------------------------------
    def __init__(
        self,
        repo: ProductRepository,
        uow: UnitOfWork,
    ):
        self.repo = repo
        self.uow = uow

        self.load_products_uc = LoadProductsUseCase(
            repo=self.repo,
            uow=self.uow,
        )

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def execute(self, cmd: LoadProductsFromFileCommand) -> List[Product]:

        try:
            logger.info(f"Loading products from file: {cmd.file_path}")

            data = pd.read_excel(
                cmd.file_path,
                sheet_name=0,
                engine="openpyxl",
            )

            column_map = self.map_columns(data, self.TARGETS)
            merged = self.merge_columns(data, column_map)

            self.apply_numeric_extraction(
                merged,
                ["grupo", "sección", "dirección"],
            )

            merged = self.clean_dataframe(merged)

            all_products = []

            for index, row in merged.iterrows():
                try:
                    product = self.create_from_dataframe_row(row)
                    all_products.append(product)
                except Exception as e:
                    logger.error(
                        f"Error creating product from row {index}: {e}"
                    )
                    continue

            products = self.load_products_uc.execute(
                LoadProductsCommand(products=all_products)
            )

            logger.info(
                f"Successfully loaded products: {len(products)}"
            )

            return [product.sku for product in products]

        except Exception as e:
            logger.error(
                f"Error loading products from file: {e}"
            )
            self.uow.rollback()
            raise e

    # -----------------------------------------------------------------
    # Column Mapping
    # -----------------------------------------------------------------
    def normalize(self, text: str) -> set[str]:
        return set(
            re.split(
                r"\s+|[.,_]",
                str(text).lower().strip(),
            )
        )

    def map_columns(
        self,
        df: pd.DataFrame,
        targets: list[str],
    ) -> dict[str, list[str]]:

        col_map = {}

        for target in targets:

            target_tokens = self.normalize(target)

            matches = [
                col
                for col in df.columns
                if self.normalize(col) & target_tokens
            ]

            if matches:
                col_map[target] = matches

        return col_map

    def merge_columns(
        self,
        df: pd.DataFrame,
        col_map: dict[str, list[str]],
    ) -> pd.DataFrame:

        merged = pd.DataFrame()

        for target, cols in col_map.items():

            if len(cols) == 1:
                merged[target] = df[cols[0]]

            else:
                merged[target] = df[cols].apply(
                    self.merge_row_values,
                    axis=1,
                )

        # Rename columns to lowercased target names for consistency
        merged.columns = [str(col).strip().lower() for col in merged.columns]

        return merged

    def merge_row_values(
        self,
        row: pd.Series,
    ) -> set[Any] | None:

        values = row.dropna().tolist()

        return set(values) if values else None

    # -----------------------------------------------------------------
    # Extraction
    # -----------------------------------------------------------------
    def extract_numbers(self, value: Any) -> set[str]:

        if pd.isna(value):
            return set()

        if isinstance(value, (int, float)):
            return {str(int(value))}

        if isinstance(value, str):
            return set(re.findall(r"\d+", value))

        if isinstance(value, Iterable):

            result = set()

            for v in value:
                result.update(
                    self.extract_numbers(v)
                )

            return result

        return set(re.findall(r"\d+", str(value)))

    def extract_keywords_from_row(
        self,
        row: pd.Series,
    ) -> set[str]:

        keywords = set()

        # Parse keywords column (may be a string repr of a list, e.g. "['word1', 'word2']")
        kw_value = row.get("keywords")
        if kw_value and isinstance(kw_value, str):
            # Try parsing as a Python list literal
            import ast
            try:
                parsed = ast.literal_eval(kw_value)
                if isinstance(parsed, list):
                    for w in parsed:
                        keywords.update(self.normalize(str(w)))
            except (ValueError, SyntaxError):
                keywords.update(self.normalize(kw_value))
        elif kw_value and isinstance(kw_value, (list, set)):
            for w in kw_value:
                keywords.update(self.normalize(str(w)))

        # Add tokens from name and type columns
        for col in ["título corto", "nombre", "disciplina", "género", "producttypesap"]:
            value = row.get(col)
            if value and isinstance(value, str):
                keywords.update(self.normalize(value))

        return {kw for kw in keywords if kw and kw not in self.STOPWORDS}

    def apply_numeric_extraction(
        self,
        df: pd.DataFrame,
        columns: list[str],
    ) -> None:

        for col in columns:

            if col in df.columns:
                df[col] = df[col].apply(
                    self.extract_numbers
                )

    # -----------------------------------------------------------------
    # Data Cleaning
    # -----------------------------------------------------------------
    def clean_dataframe(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:

        required = [
            "código sku",
            "negocio",
            "marca",
        ]

        df = df.dropna(subset=required)

        df = df.drop_duplicates(
            subset=["código sku"]
        )

        if "disciplina" in df.columns:

            df = df[
                df["disciplina"].apply(
                    lambda x:
                    not isinstance(x, set)
                    or len(x) <= 1
                )
            ]

        for col in [
            "nombre",
            "disciplina",
            "género",
            "marca",
            "negocio",
            "dirección",
            "título corto",
        ]:

            if col in df.columns:
                df[col] = df[col].apply(
                    self.normalize_scalar
                )

        if "género" in df.columns:

            df["género"] = df["género"].apply(
                lambda x:
                None
                if str(x).lower()
                not in ("hombre", "mujer")
                else str(x).lower()
            )

        return df

    def normalize_scalar(
        self,
        value: Any,
    ) -> Any:

        if isinstance(value, set):
            return next(iter(value)) if value else None

        return value

    # -----------------------------------------------------------------
    # Entity Factory
    # -----------------------------------------------------------------
    def create_from_dataframe_row(
        self,
        row: pd.Series,
    ) -> Product:

        # Prefer "título corto", fall back to "nombre"
        name = row.get("título corto") or row.get("nombre")

        # article_group may be a set after numeric extraction
        article_group = row.get("grupo")
        if isinstance(article_group, set):
            article_group = sorted(article_group)

        # SKU: convert float (e.g. 4.016589e+06) to int string
        sku_raw = row.get("código sku")
        sku = str(int(float(sku_raw))) if pd.notna(sku_raw) else ""

        return Product.create(
            sku=sku,
            name=str(name) if name else "",
            brand=str(row.get("marca")),
            direction=str(row.get("dirección")),
            product_type=str(row.get("negocio")),
            category=str(row.get("producttypesap")),
            description=str(row.get("disciplina") or ""),
            gender=row.get("género"),
            article_group=article_group,
            keywords=self.extract_keywords_from_row(row),
        )