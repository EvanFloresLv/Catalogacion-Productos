# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations


class ProductError(Exception):
    """Base class for all product-related errors."""


class ProductTitleError(ProductError):
    """Raised when a product title is invalid."""
