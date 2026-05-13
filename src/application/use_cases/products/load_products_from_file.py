# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import re
import logging
from typing import List, Any, Iterable
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
import pandas as pd

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.product import Product

from domain.repositories.product_repository import ProductRepository

from shared.kernel.unit_of_work import UnitOfWork

from application.use_cases.products.load_products import (
    LoadProductsUseCase,
    LoadProductsCommand,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------
@dataclass
class LoadProductsFromFileCommand:
    file_path: str


class LoadProductsFromFileUseCase:

    TARGETS = [
        "Código SKU", "Negocio", "Nombre", "Dirección", "Sección",
        "Grupo", "Marca", "Género", "Disciplina"
    ]

    def __init__(
        self,
        repo: ProductRepository,
        uow: UnitOfWork,
    ):
        self.repo = repo
        self.uow = uow

        self.load_products_uc = LoadProductsUseCase(
            repo=self.repo,
            uow=self.uow
        )


    def execute(self, cmd: LoadProductsFromFileCommand) -> List[Product]:

        try:

            logger.info(f"Loading products from file: {cmd.file_path}")

            data = pd.read_excel(cmd.file_path, sheet_name=0, engine="openpyxl")

            column_map = self.map_columns(data, self.TARGETS)
            merged = self.merge_columns(data, column_map)

            self.apply_numeric_extraction(merged, ["Grupo", "Sección", "Dirección"])
            merged = self.clean_dataframe(merged)

            all_products = []

            for index, row in merged.iterrows():
                try:
                    product = self.create_from_dataframe_row(row)
                    all_products.append(product)
                except Exception as e:
                    print(f"Error creating product from row {index}: {e}")
                    continue

            products = self.load_products_uc.execute(
                LoadProductsCommand(products=all_products)
            )

            logger.info(f"Successfully loaded products: {len(products)}")

            return [product.sku for product in products]

        except Exception as e:
            logger.error(f"Error loading products from file: {e}")
            self.uow.rollback()
            raise e


    def normalize(self, text: str) -> set[str]:
        return set(re.split(r"\s+|[.,_]", str(text).lower().strip()))


    def map_columns(self, df: pd.DataFrame, targets: list[str]) -> dict[str, list[str]]:

        col_map = {}
        for target in targets:
            target_tokens = self.normalize(target)
            matches = [
                col for col in df.columns
                if self.normalize(col) & target_tokens
            ]
            if matches:
                col_map[target] = matches

        return col_map


    def merge_columns(self, df: pd.DataFrame, col_map: dict[str, list[str]]) -> pd.DataFrame:
        merged = pd.DataFrame()

        for target, cols in col_map.items():
            if len(cols) == 1:
                merged[target] = df[cols[0]]
            else:
                merged[target] = df[cols].apply(self.merge_row_values, axis=1)

        return merged


    def merge_row_values(self, row: pd.Series) -> set[Any] | None:
        values = row.dropna().tolist()
        return set(values) if values else None


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
                result.update(set(self.extract_numbers(v)))
            return result

        return set(re.findall(r"\d+", str(value)))


    def apply_numeric_extraction(self, df: pd.DataFrame, columns: list[str]) -> None:
        for col in columns:
            if col in df.columns:
                df[col] = df[col].apply(self.extract_numbers)


    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        required = ["Código SKU", "Negocio", "Marca"]

        df = df.dropna(subset=required)

        df = df[
            df["Disciplina"].apply(
                lambda x: not isinstance(x, set) or len(x) <= 1
            )
        ]

        for col in ["Nombre", "Disciplina", "Género", "Marca", "Negocio", "Dirección"]:
            if col in df.columns:
                df[col] = df[col].apply(self.normalize_scalar)

        df["Género"] = df["Género"].apply(
            lambda x: None if str(x).lower() not in ("hombre", "mujer") else str(x).lower()
        )

        return df


    def normalize_scalar(self, value: Any) -> Any:
        if isinstance(value, set):
            return next(iter(value)) if value else None
        return value


    def create_from_dataframe_row(self, row: pd.Series) -> Product:
        return Product.create(
            sku=str(row.get("Código SKU", None)),
            name=str(row.get("Nombre", None)),
            brand=str(row.get("Marca", None)),
            direction=str(row.get("Dirección", None)),
            product_type=str(row.get("Negocio", None)),
            description=str(row.get("Disciplina", None)),
            gender=row.get("Género"),
            article_group=row.get("Grupo"),
        )