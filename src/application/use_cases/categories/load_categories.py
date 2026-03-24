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

        xls = pd.ExcelFile(cmd.file_path)
        all_categories = {}

        parsed_results = []

        # Stage 1 — Parallel sheet parsing
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

        # Stage 2 — Sequential commit
        for sheet_name, categories in parsed_results:

            if not categories:
                continue

            print(f"Sheet: {sheet_name} | {len(categories)} categories")

            self._validate_parent_integrity(categories)
            categories = self._deduplicate_categories(categories)

            # Enhance categories with keywords from their parent chain (excluding root)
            categories = self._enhance_with_parent_keywords(categories)

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

    # Sheet processing
    def _process_sheet(
        self,
        xls: pd.ExcelFile,
        sheet_name: str,
    ) -> List[Category]:

        print(f"Processing sheet: {sheet_name}")

        df: pd.DataFrame | None = self._prepare_dataframe(xls, sheet_name)

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

    # Dataframe preparation
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
        if not all(col in lower_cols for col in ["catid", "url"]):
            print(f"Skipping sheet {sheet_name} (no 'catid' or 'url').")
            return None

        cat_id_index = lower_cols.index("catid")
        level_count = cat_id_index

        levels = [f"level {i}" for i in range(1, level_count + 1)]
        remaining = list(df.columns[level_count:])

        df.columns = levels + remaining

        df.dropna(axis=1, how="all", inplace=True)

        return df

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
    ) -> Category | None:

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

    # Helpers
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
        unique = {}
        for c in categories:
            unique[c.id] = c
        return list(unique.values())

    def _enhance_with_parent_keywords(
        self,
        categories: List[Category],
    ) -> List[Category]:

        category_map = {cat.id: cat for cat in categories}

        enhanced_categories = []

        for cat in categories:
            # Skip root categories - they don't get enhanced
            if cat.level == 1:
                enhanced_categories.append(cat)
                continue

            # Start with the category's own keywords
            all_keywords = set(cat.keywords) if cat.keywords else set()
            original_count = len(all_keywords)

            # Collect keywords from parent chain (excluding root)
            parent_keywords = self._collect_parent_keywords(
                cat.parent_id,
                category_map
            )
            all_keywords.update(parent_keywords)

            # Create new category with enhanced keywords
            enhanced_cat = Category.create(
                id=cat.id,
                name=cat.name,
                level=cat.level,
                parent_id=cat.parent_id,
                description=cat.description,
                url=cat.url,
                keywords=tuple(sorted(all_keywords))  # Sort for consistency
            )

            enhanced_categories.append(enhanced_cat)

            if len(all_keywords) > original_count:
                print(f"  Enhanced '{cat.name}' (L{cat.level}): {original_count} → {len(all_keywords)} keywords")

        return enhanced_categories

    def _collect_parent_keywords(
        self,
        parent_id: str | None,
        category_map: Dict[str, Category],
    ) -> set[str]:

        keywords = set()

        # Base case: no parent or parent not found
        if not parent_id or parent_id not in category_map:
            return keywords

        parent = category_map[parent_id]

        # Stop at root level (level 1) - don't include root keywords
        if parent.level == 1:
            return keywords

        # Add parent's keywords
        if parent.keywords:
            keywords.update(parent.keywords)

        # Recursively get grandparent keywords
        grandparent_keywords = self._collect_parent_keywords(
            parent.parent_id,
            category_map
        )

        keywords.update(grandparent_keywords)

        return keywords

    def _commit_sheet(
        self,
        sheet_name: str,
        categories: List[Category],
    ) -> List[Category]:

        try:
            saved = self.category_repository.save_batch(categories)
            self.session.commit()
            print(f"✓ Sheet {sheet_name}: {len(saved)} categories saved")
            return saved

        except Exception as e:
            self.session.rollback()
            print(f"✗ Rollback sheet {sheet_name}: {e}")
            raise
