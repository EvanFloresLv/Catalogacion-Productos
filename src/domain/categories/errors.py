# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations


class CategoryError(Exception):
    """Base class for all category-related errors."""


class CategoryNameError(CategoryError):
    """Raised when a category name is invalid."""
