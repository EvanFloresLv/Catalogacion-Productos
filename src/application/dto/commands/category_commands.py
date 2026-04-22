# -----------------------------------------------------------------
# Application DTO — Commands — Category
# -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoadCategoriesCommand:
    """Command to load categories from an Excel file."""
    file_path: str


@dataclass(frozen=True)
class LoadCategoriesFromFileCommand:
    """Command to load categories, embeddings, and profiles from an Excel file."""
    file_path: str
    brand: bool = False
    business: str = "liverpool"
