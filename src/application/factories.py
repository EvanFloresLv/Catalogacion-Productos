# -----------------------------------------------------------------
# Application — DTO Factory Methods
# -----------------------------------------------------------------
"""
Centralised factory for creating every Application-layer DTO
(commands and queries).

Usage
-----
    from application.factories import DTOFactory

    cmd = DTOFactory.create_load_categories_command(file_path="data/Suburbia.xlsx")
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# ── Commands ─────────────────────────────────────────────────────
from application.dto.commands.category_commands import (
    LoadCategoriesCommand,
    LoadCategoriesFromFileCommand,
)
from application.dto.commands.product_commands import LoadProductsCommand
from application.dto.commands.classification_commands import ClassifyProductCommand

# ── Queries ──────────────────────────────────────────────────────
from application.dto.queries.category_queries import (
    GetCategoryTreeQuery,
    GetCategoriesByConstraintsQuery,
)
from application.dto.queries.product_queries import (
    GetProductBySkuQuery,
    GetProductsBySkusQuery,
)


class DTOFactory:
    """Static factory methods for all application DTOs."""

    # =============================================================
    #  COMMANDS
    # =============================================================

    # ── Category Commands ────────────────────────────────────────
    @staticmethod
    def create_load_categories_command(
        *, file_path: str,
    ) -> LoadCategoriesCommand:
        """Create a LoadCategoriesCommand."""
        return LoadCategoriesCommand(file_path=file_path)

    @staticmethod
    def create_load_categories_from_file_command(
        *,
        file_path: str,
        brand: bool = False,
        business: str = "liverpool",
    ) -> LoadCategoriesFromFileCommand:
        """Create a LoadCategoriesFromFileCommand with optional brand/business."""
        return LoadCategoriesFromFileCommand(
            file_path=file_path,
            brand=brand,
            business=business,
        )

    # ── Product Commands ─────────────────────────────────────────
    @staticmethod
    def create_create_product_command(
        *, products: List[Dict[str, Any]],
    ) -> LoadProductsCommand:
        """Create a LoadProductsCommand from a list of product dictionaries."""
        return LoadProductsCommand(products=products)

    # ── Classification Commands ──────────────────────────────────
    @staticmethod
    def create_classify_product_command(
        *,
        product_sku: str,
        top_k: int = 5,
    ) -> ClassifyProductCommand:
        """Create a ClassifyProductCommand."""
        return ClassifyProductCommand(
            product_sku=product_sku,
            top_k=top_k,
        )

    # =============================================================
    #  QUERIES
    # =============================================================

    # ── Category Queries ─────────────────────────────────────────
    @staticmethod
    def create_get_category_tree_query(
        *, root_category_id: Optional[str] = None,
    ) -> GetCategoryTreeQuery:
        """Create a GetCategoryTreeQuery."""
        return GetCategoryTreeQuery(
            root_category_id=root_category_id,
        )

    @staticmethod
    def create_get_categories_by_constraints_query(
        *,
        gender: Optional[str] = None,
        direction: Optional[str] = None,
        brand: Optional[str] = None,
        business: Optional[str] = None,
        is_leaf: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> GetCategoriesByConstraintsQuery:
        """Create a GetCategoriesByConstraintsQuery with optional filters."""
        return GetCategoriesByConstraintsQuery(
            gender=gender,
            direction=direction,
            brand=brand,
            business=business,
            is_leaf=is_leaf,
            limit=limit,
        )

    # ── Product Queries ──────────────────────────────────────────
    @staticmethod
    def create_get_product_by_sku_query(
        *, sku: str,
    ) -> GetProductBySkuQuery:
        """Create a GetProductBySkuQuery."""
        return GetProductBySkuQuery(sku=sku)

    @staticmethod
    def create_get_products_by_skus_query(
        *, skus: List[str],
    ) -> GetProductsBySkusQuery:
        """Create a GetProductsBySkusQuery."""
        return GetProductsBySkusQuery(skus=skus)
