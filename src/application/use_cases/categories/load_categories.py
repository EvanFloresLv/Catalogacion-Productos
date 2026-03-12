# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import re
import json
import unicodedata
from typing import List, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy.orm import Session
import pandas as pd

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.categories.category import Category
from application.ports.category_repository import CategoryRepository


# ---------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------
@dataclass
class LoadCategoriesCommand:
    file_path: str
    brand: bool = False  # If True, use sheet name as brand for all categories in that sheet


# ---------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------
class LoadCategoriesUseCase:
    """
    Loads categories from an Excel file into the database.
    Handles parsing, validation, and persistence of category entities.
    """

    SHEET_WORKERS = 4

    def __init__(
        self,
        session: Session,
        category_repository: CategoryRepository,
    ):
        self.session = session
        self.category_repository = category_repository

    # =============================================================
    # PUBLIC API
    # =============================================================
    def execute(self, cmd: LoadCategoriesCommand) -> List[Category]:
        """
        Load categories from Excel file and save to database.

        Args:
            cmd.file_path: Path to Excel file
            cmd.brand: If True, use sheet name as brand for all categories

        Returns dict with structure:
            {
                "sheet_name": {
                    "categories": [Category, ...],
                    "all_key_words": set(["keyword1", ...])
                }
            }
        """
        xls = pd.ExcelFile(cmd.file_path)
        all_categories = {}

        parsed_results = []

        # -----------------------------
        # Stage 1 — Parallel sheet parsing
        # -----------------------------
        with ThreadPoolExecutor(max_workers=self.SHEET_WORKERS) as executor:
            futures = {
                executor.submit(self._process_sheet, xls, sheet): sheet
                for sheet in xls.sheet_names
            }

            for future in as_completed(futures):
                sheet_name = futures[future]
                try:
                    parsed_results.append((sheet_name, future.result()))
                except Exception as e:
                    print(f"Error processing sheet {sheet_name}: {e}")

        # -----------------------------
        # Stage 2 — Sequential commit
        # -----------------------------
        for sheet_name, categories in parsed_results:

            if not categories:
                continue

            print(f"Sheet: {sheet_name} | {len(categories)} categories")

            self._validate_parent_integrity(categories)
            categories = self._deduplicate_categories(categories)

            saved = self._commit_sheet(sheet_name, categories)

            if sheet_name not in all_categories.keys():
                all_categories[sheet_name] = {
                    "categories": [],
                    "all_key_words": set()
                }

            all_categories[sheet_name]["categories"].extend(saved)
            # Flatten all keywords from all categories into the set
            for cat in saved:
                if cat.keywords:
                    all_categories[sheet_name]["all_key_words"].update(cat.keywords)

        print(f"\n\nTotal categories loaded: {len(all_categories)}")

        return all_categories

    # =============================================================
    # SHEET PROCESSING
    # =============================================================
    def _process_sheet(
        self,
        xls: pd.ExcelFile,
        sheet_name: str,
        use_brand: bool = False,
    ) -> List[Category]:
        """Process a single sheet and return parsed categories."""

        print(f"Processing sheet: {sheet_name}")

        df = self._prepare_dataframe(xls, sheet_name)
        if df is None:
            return []

        categories: List[Category] = []
        last_inserted: Dict[int, str] = {}

        for _, row in df.iterrows():

            row_dict = self._clean_row(row)
            if not row_dict:
                continue

            category = self._parse_row(
                row_dict,
                last_inserted,
            )
            if not category:
                continue

            categories.append(category)

        categories.sort(key=lambda c: (c.level, c.parent_id or ""))

        print(f"Prepared {len(categories)} categories for {sheet_name}")

        return categories

    # =============================================================
    # DATAFRAME PREPARATION
    # =============================================================
    def _prepare_dataframe(
        self,
        xls: pd.ExcelFile,
        sheet_name: str,
    ) -> pd.DataFrame | None:
        """Prepare and validate DataFrame from Excel sheet."""

        df = pd.read_excel(xls, sheet_name=sheet_name)

        if df.empty or len(df.columns) < 3:
            print(f"Skipping sheet {sheet_name} (invalid structure).")
            return None

        df.columns = df.columns.map(lambda x: str(x).strip())

        lower_cols = [c.lower() for c in df.columns]
        if not all(col in lower_cols for col in ["catid", "url"]):
            print(f"Skipping sheet {sheet_name} (no 'catid' or 'url').")
            return None

        cat_id_index = lower_cols.index("catid")
        level_count = cat_id_index

        levels = [f"level {i}" for i in range(1, level_count + 1)]
        remaining = list(df.columns[level_count:])

        df.columns = levels + remaining

        return df

    # =============================================================
    # ROW PARSING
    # =============================================================
    def _clean_row(self, row: pd.Series) -> Dict[str, Any]:
        """Clean and normalize row data."""
        return {
            str(k).strip(): v
            for k, v in row.to_dict().items()
            if pd.notna(v)
        }

    def _parse_row(
        self,
        row_dict: Dict[str, Any],
        last_inserted: Dict[int, str],
    ) -> Category | None:
        """Parse a single row into a Category entity."""

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
            self._find_key(row_dict, "meta") or "", ""
        ))

        descripcion = self._clean_text(row_dict.get(
            self._find_key(row_dict, "descripcion") or "", ""
        ))

        palabras = row_dict.get(self._find_key(row_dict, "keyword"), "")
        keywords = self._extract_keywords(titulo, descripcion, palabras)

        category = Category.create(
            id=cat_id,
            name=name,
            level=level,
            parent_id=parent_id,
            description=descripcion,
            url=row_dict.get(self._find_key(row_dict, "url")),
            keywords=tuple(keywords),
        )

        return category

    # =============================================================
    # HELPERS
    # =============================================================
    @staticmethod
    def _find_key(data: Dict[str, Any], keyword: str) -> str | None:
        """Find a key in dictionary by keyword (case-insensitive)."""
        return next(
            (k for k in data.keys() if keyword in k.lower()),
            None,
        )

    @staticmethod
    def _extract_level(key: str) -> int | None:
        """Extract level number from key string."""
        match = re.search(r"\d+", key)
        return int(match.group()) if match else None

    @staticmethod
    def _clean_text(text: Any) -> str:
        """Clean and normalize text content."""
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
        """Extract and normalize keywords from various sources."""

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
    def _validate_parent_integrity(categories: List[Category]) -> None:
        """Validate that all parent categories exist in the list."""
        ids_set = {c.id for c in categories}

        for cat in categories:
            if cat.parent_id and cat.parent_id not in ids_set:
                raise ValueError(
                    f"Missing parent {cat.parent_id} "
                    f"for category {cat.id}"
                )

    @staticmethod
    def _deduplicate_categories(
        categories: List[Category],
    ) -> List[Category]:
        """Remove duplicate categories by ID."""
        unique = {}
        for c in categories:
            unique[c.id] = c
        return list(unique.values())

    # =============================================================
    # TRANSACTION
    # =============================================================
    def _commit_sheet(
        self,
        sheet_name: str,
        categories: List[Category],
    ) -> List[Category]:
        """Save categories to database within a transaction."""

        try:
            saved = self.category_repository.save_batch(categories)
            self.session.commit()
            print(f"✓ Sheet {sheet_name}: {len(saved)} categories saved")
            return saved

        except Exception as e:
            self.session.rollback()
            print(f"✗ Rollback sheet {sheet_name}: {e}")
            raise
