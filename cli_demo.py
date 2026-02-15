# src/cli_demo.py
from sqlalchemy.orm import Session

from infrastructure.persistence.db import create_sqlite_engine, create_session_factory, Base
from infrastructure.persistence.repositories.sql_category_repository import SQLCategoryRepository
from infrastructure.persistence.repositories.sql_product_repository import SQLProductRepository
from infrastructure.persistence.repositories.sql_category_embedding_repository import SQLCategoryEmbeddingRepository

from infrastructure.embeddings.fake_embedding_service import FakeEmbeddingService
from infrastructure.vectors.faiss_index import FaissVectorIndex

from application.use_cases.categories.create_category import CreateCategoryUseCase, CreateCategoryCommand
from application.use_cases.products.create_product import CreateProductUseCase, CreateProductCommand
from application.use_cases.categories.rebuild_category_embeddings import RebuildCategoryEmbeddingsUseCase
from application.use_cases.classification.classify_product import ClassifyProductUseCase, ClassifyProductCommand


def main():
    # 1) DB setup
    engine = create_sqlite_engine("app.db")
    SessionLocal = create_session_factory(engine)

    # 2) Crear tablas
    Base.metadata.create_all(bind=engine)

    # 3) Dependencias concretas (infra)
    embeddings = FakeEmbeddingService(dim=64)
    faiss_index = FaissVectorIndex()

    # 4) Abrir sesión SQLAlchemy
    with SessionLocal() as db:
        db: Session

        # Repos (adaptadores de salida)
        categories_repo = SQLCategoryRepository(db)
        products_repo = SQLProductRepository(db)
        category_embeddings_repo = SQLCategoryEmbeddingRepository(db)

        # Use cases (core)
        create_category_uc = CreateCategoryUseCase(categories_repo)
        create_product_uc = CreateProductUseCase(products_repo)

        rebuild_uc = RebuildCategoryEmbeddingsUseCase(
            categories=categories_repo,
            embedding_repo=category_embeddings_repo,
            embedding_service=embeddings,
            vector_index=faiss_index,
        )

        classify_uc = ClassifyProductUseCase(
            products=products_repo,
            embeddings=embeddings,
            vector_index=faiss_index,
        )

        # ============================================================
        # 5) Crear categorías (árbol)
        # ============================================================

        print("\n== Creating categories ==")

        electronics = create_category_uc.execute(
            CreateCategoryCommand(name="Electrónica", parent_id=None)
        )

        audio = create_category_uc.execute(
            CreateCategoryCommand(name="Audio", parent_id=electronics.id)
        )

        headphones = create_category_uc.execute(
            CreateCategoryCommand(name="Audífonos", parent_id=audio.id)
        )

        laptops = create_category_uc.execute(
            CreateCategoryCommand(name="Laptops", parent_id=electronics.id)
        )

        print("Electronics:", electronics)
        print("Audio:", audio)
        print("Headphones:", headphones)
        print("Laptops:", laptops)

        # ============================================================
        # 6) Rebuild embeddings + indexar en FAISS
        # ============================================================

        print("\n== Rebuilding category embeddings (SQLite + FAISS) ==")
        n = rebuild_uc.execute()
        print("Indexed categories:", n)

        # ============================================================
        # 7) Crear producto
        # ============================================================

        print("\n== Creating product ==")
        product = create_product_uc.execute(
            CreateProductCommand(
                title="Audífonos Bluetooth Sony WH-1000XM5",
                description="Audífonos inalámbricos con cancelación activa de ruido",
                keywords=["sony", "bluetooth", "audio", "noise cancelling", "headphones"],
            )
        )
        print("Product:", product)

        # ============================================================
        # 8) Clasificar producto
        # ============================================================

        print("\n== Classifying product ==")
        result = classify_uc.execute(ClassifyProductCommand(product_id=product.id, top_k=4))

        print("\n--- Classification result ---")
        print("Product ID:", result.product_id)
        print("Best match:", result.best.category_id, "score=", result.best.score)

        print("\nTop-K:")
        for m in result.matches:
            print(" -", m.category_id, "score=", m.score)

        print("\nDONE.\n")


if __name__ == "__main__":
    main()
