# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from typing import List, Dict, Any
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
import pandas as pd

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.brand import Brand

from domain.repositories.brand_repository import BrandRepository
from domain.aggregates.brand_catalog import BrandCatalog

from shared.kernel.unit_of_work import UnitOfWork


# -------------------------------------------------------------
# Command
# -------------------------------------------------------------
@dataclass
class LoadBrandsCommand:
    data: pd.DataFrame


# -------------------------------------------------------------
# Use Case
# -------------------------------------------------------------
class LoadBrandsUseCase:

    def __init__(self, repo: BrandRepository, uow: UnitOfWork):
        self.repo = repo
        self.uow = uow


    # =========================================================
    # PUBLIC
    # =========================================================
    def execute(self, cmd: LoadBrandsCommand) -> Dict[str, Any]:
        brands = self._process_data(cmd.data)

        if not brands:
            return None

        catalog = BrandCatalog()
        self.uow.register(catalog)

        catalog.add_brands_batch(brands)
        saved = self.repo.save_batch(list(catalog.brands))

        self.uow.commit()

        return saved

    # =========================================================
    # CORE PARSING
    # =========================================================
    def _process_data(self, df: pd.DataFrame) -> List[Brand]:

        df.columns = [col.strip().lower() for col in df.columns]
        df = df.apply(
            lambda col: col.map(lambda v: v.strip().lower() if isinstance(v, str) else v)
        )

        df = df.drop_duplicates(subset=[df.columns[0]], keep="first")

        df = df.replace({pd.NA: None})
        df = df.replace({
            "sí": True,
            "si": True,
            "no": False
        })

        print("Processing brand data...")
        print(df)

        brands = []

        for _, row in df.iterrows():

            name = row.iloc[0]

            if not isinstance(name, str):
                continue

            business = [
                col.replace(" ", "_") for col in df.columns[1:]
                if row[col] is True
            ]

            brand = Brand(
                name=name,
                business=business
            )

            brands.append(brand)

        print("Brands processed:")
        for b in brands:
            print(f" - {b.name} (Negocios: {', '.join(b.business)})")

        return brands