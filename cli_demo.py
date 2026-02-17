# src/cli_demo.py
from pathlib import Path
from sqlalchemy.orm import Session

from infrastructure.persistence.db import (
    create_sqlite_engine,
    create_session_factory,
    Base,
)

from infrastructure.persistence import models

from infrastructure.persistence.repositories.sql_category_repository import SQLCategoryRepository
from infrastructure.persistence.repositories.sql_product_repository import SQLProductRepository
from infrastructure.persistence.repositories.sql_category_profile_repository import (
    SQLCategoryProfileRepository,
)
from infrastructure.persistence.repositories.sql_exclusion_repository import (
    SQLExclusionRepository,
)
from infrastructure.persistence.repositories.sql_faiss_id_map_repository import (
    SQLFaissIdMapperRepository,
)

from infrastructure.embeddings.fake_embedding_service import FakeEmbeddingService
from infrastructure.vectors.faiss_index import FaissVectorIndex

from domain.classification.eligibility_policy import CategoryEligibilityPolicy

from application.use_cases.categories.create_category import (
    CreateCategoryUseCase,
    CreateCategoryCommand,
)

from application.use_cases.products.create_product import (
    CreateProductUseCase,
    CreateProductCommand,
)

from application.use_cases.classification.rebuild_category_index import (
    RebuildCategoryIndexUseCase,
    RebuildCategoryIndexCommand,
)

from application.use_cases.classification.classify_product import (
    ClassifyProductUseCase,
    ClassifyProductCommand,
)

from application.use_cases.category_profiles.upsert_category_profile import (
    UpsertCategoryProfileUseCase,
    UpsertCategoryProfileCommand,
)

from application.use_cases.exclusions.add_exclusion import (
    AddExclusionUseCase,
    AddExclusionCommand,
)


DATA_DIR = Path("./data")
FAISS_PATH = DATA_DIR / "faiss.index"


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # 1) DB setup
    # ============================================================
    engine = create_sqlite_engine("app.db")
    SessionLocal = create_session_factory(engine)

    # Crear tablas (SQLAlchemy ORM)
    Base.metadata.create_all(bind=engine)

    # ============================================================
    # 2) Infra dependencies
    # ============================================================
    embeddings = FakeEmbeddingService(dim=64)

    # ============================================================
    # 3) Abrir sesión SQLAlchemy
    # ============================================================
    with SessionLocal() as db:
        db: Session

        # Repos (SQLAlchemy)
        categories_repo = SQLCategoryRepository(db)
        products_repo = SQLProductRepository(db)
        profiles_repo = SQLCategoryProfileRepository(db)
        exclusions_repo = SQLExclusionRepository(db)
        id_map_repo = SQLFaissIdMapperRepository(db)

        # FAISS index con persistencia + mapper estable
        faiss_index = FaissVectorIndex(
            index_path=str(FAISS_PATH),
            mapper=id_map_repo,
        )

        if not faiss_index.load():
            faiss_index.reset(embeddings.dimension())

        # Domain policy
        policy = CategoryEligibilityPolicy()

        # Use cases
        create_category_uc = CreateCategoryUseCase(categories_repo)
        create_product_uc = CreateProductUseCase(products_repo)

        upsert_profile_uc = UpsertCategoryProfileUseCase(
            categories=categories_repo,
            profiles=profiles_repo,
        )

        add_exclusion_uc = AddExclusionUseCase(
            products=products_repo,
            categories=categories_repo,
            exclusions=exclusions_repo,
        )

        rebuild_index_uc = RebuildCategoryIndexUseCase(
            profiles=profiles_repo,
            embeddings=embeddings,
            index=faiss_index,
        )

        classify_uc = ClassifyProductUseCase(
            products=products_repo,
            profiles=profiles_repo,
            exclusions=exclusions_repo,
            embeddings=embeddings,
            index=faiss_index,
            policy=policy,
        )

        # ============================================================
        # 4) Crear categorías (árbol)
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

        # ============================================================
        # 5) Profiles: keywords + constraints por categoría
        # ============================================================
        print("\n== Creating category profiles (constraints + keywords) ==")

        upsert_profile_uc.execute(
            UpsertCategoryProfileCommand(
                category_id=electronics.id,
                keywords=["gadgets", "technology", "devices", "electronics"],
                allowed_genders=None,
                allowed_business_types=None,
            )
        )

        upsert_profile_uc.execute(
            UpsertCategoryProfileCommand(
                category_id=audio.id,
                keywords=["audio", "sound", "speakers", "headphones"],
                allowed_genders=None,
                allowed_business_types=None,
            )
        )

        upsert_profile_uc.execute(
            UpsertCategoryProfileCommand(
                category_id=headphones.id,
                keywords=["headphones", "earbuds", "noise cancelling", "bluetooth"],
                allowed_genders=None,
                allowed_business_types={"b2c"},
            )
        )

        upsert_profile_uc.execute(
            UpsertCategoryProfileCommand(
                category_id=laptops.id,
                keywords=["laptop", "notebook", "computer", "macbook", "windows"],
                allowed_genders=None,
                allowed_business_types={"b2c", "b2b"},
            )
        )

        print("Electronics:", electronics)
        print("Audio:", audio)
        print("Headphones:", headphones)
        print("Laptops:", laptops)

        # ============================================================
        # 6) Rebuild index FAISS + persistir
        # ============================================================
        print("\n== Rebuilding category index (SQLite + FAISS persisted) ==")

        stats = rebuild_index_uc.execute(RebuildCategoryIndexCommand())
        print("Indexed categories:", stats["indexed_categories"])

        faiss_index.save()

        # ============================================================
        # 7) Crear producto
        # ============================================================
        print("\n== Creating product ==")

        product = create_product_uc.execute(
            CreateProductCommand(
                title="Audífonos Bluetooth Sony WH-1000XM5",
                description="Audífonos inalámbricos con cancelación activa de ruido",
                keywords=["sony", "bluetooth", "audio", "noise cancelling", "headphones"],
                gender=None,
                business_type="b2c",
            )
        )

        print("Product:", product)

        # ============================================================
        # 8) Exclusión manual por producto
        # ============================================================
        print("\n== Adding manual exclusions ==")

        add_exclusion_uc.execute(
            AddExclusionCommand(
                product_id=product.id,
                category_id=audio.id,
                reason="Blocked by catalog manager for this SKU",
            )
        )

        print("Excluded category:", audio.id)

        # ============================================================
        # 9) Clasificar producto
        # ============================================================
        print("\n== Classifying product ==")

        result = classify_uc.execute(
            ClassifyProductCommand(product_id=product.id, top_k=4)
        )

        print("\n--- Classification result ---")
        print("Product ID:", result.product_id)
        print("Best match:", result.best.category_id, "score=", result.best.score)

        print("\nTop-K:")
        for m in result.top_k:
            print(" -", m.category_id, "score=", m.score)

        print("\nDONE.\n")


if __name__ == "__main__":
    main()
