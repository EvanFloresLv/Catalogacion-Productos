# -----------------------------------------------------------------
# Interfaces — CLI Controller
# -----------------------------------------------------------------
"""
CLI interface layer.

Rules:
  - Depends on Application layer (use cases, DTOs)
  - Depends on Config (composition root)
  - Does NOT depend on Domain or Infrastructure directly
"""
from __future__ import annotations

from infrastructure.persistence.postgresql.session import SessionLocal

from config.composition_root import (
    create_unit_of_work,
    create_load_categories_from_file_use_case,
    create_create_product_use_case,
    create_classify_product_use_case,
)

from application.use_cases.categories.load_categories_from_file import (
    LoadCategoriesFromFileCommand,
)
from application.use_cases.products.load_products import LoadProductsUseCase
from application.use_cases.classification.classify_product import ClassifyProductCommand


class CLIController:
    """
    Thin CLI controller that translates user input into use case commands.
    """

    # =============================================================
    # Load categories from file
    # =============================================================
    @staticmethod
    def load_categories(
        file_path: str,
        business: str,
        by_sheet: bool = False,
        brand: bool = False,
    ) -> None:
        cmd = LoadCategoriesFromFileCommand(
            file_path=file_path,
            business=business,
            by_sheet=by_sheet,
            brand=brand,
        )

        with SessionLocal() as session:
            uow = create_unit_of_work(session)
            use_case = create_load_categories_from_file_use_case(session, uow=uow)
            result = use_case.execute(cmd)

            print(f"\n✓ Categories: {len(result.get('categories', []))}")
            print(f"✓ Embeddings: {len(result.get('embeddings', []))}")

    # =============================================================
    # Create products
    # =============================================================
    @staticmethod
    def create_products(products: list[dict]) -> None:

        with SessionLocal() as session:
            uow = create_unit_of_work(session)
            cmd = LoadProductsUseCase(products=products, uow=uow)
            use_case = create_create_product_use_case(session, uow=uow)
            created = use_case.execute(cmd)

            print(f"\n✓ {len(created)} product(s) created")
            for product in created:
                print(f"  - SKU: {product.sku} | Name: {product.name}")
                print(f"    Brand: {product.brand} | Business: {product.business}")

    # =============================================================
    # Classify product
    # =============================================================
    @staticmethod
    def classify_product(product_sku: str, top_k: int = 5) -> None:
        cmd = ClassifyProductCommand(product_sku=product_sku, top_k=top_k)

        with SessionLocal() as session:
            uow = create_unit_of_work(session)
            use_case = create_classify_product_use_case(session, uow=uow)
            results = use_case.execute(cmd)

            print("\n" + "=" * 60)
            print("CLASSIFICATION RESULTS")
            print("=" * 60)

            for idx, result in enumerate(results, 1):
                print(f"\nResult #{idx}:")
                print(f"  Product SKU: {result.product_sku}")
                print(f"  Best match:  {result.best.category_id} "
                      f"(Score: {result.best.score:.4f})")
                print(f"  Path:        {result.best.path}")
                print("  Top K matches:")
                for match in result.top_k:
                    print(f"    - {match.category_id} | "
                          f"Score: {match.score:.4f} | "
                          f"Path: {match.path}")

            print("\n" + "=" * 60)
