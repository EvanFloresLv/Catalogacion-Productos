from infrastructure.embeddings.gemini.client import EmbeddingClient

import domain as dom
import application as app
import infrastructure.persistence.postgresql as pg
from domain.specifications.eligibility_policy import CategoryEligibilityPolicy

from infrastructure.persistence.postgresql.session import SessionLocal
from infrastructure.prompts import Prompt
from infrastructure.llm.gemini import LLMClient

from application.use_cases.categories.load_categories_from_file import (
    LoadCategoriesFromFileUseCase,
    LoadCategoriesFromFileCommand,
)

def test_embedding_generation():

    embedding = EmbeddingClient()

    category = dom.Category.create(
        name="Test Category",
        description="A category for testing purposes.",
        keywords=["test", "category", "embedding"],
    )

    vec = embedding.generate(category.to_embedding_text())
    print("Embedding length:", len(vec))

    embedding.close()


def test_hashing():

    text1 = "This is a test category for embedding generation."
    text2 = "This is a test category for embedding generation with a slight change."

    hash1 = dom.SemanticHash.from_text(text1)
    hash2 = dom.SemanticHash.from_text(text2)

    print("Hash 1:", hash1.value)
    print("Hash 2:", hash2.value)


def test_unique_hashes():

    with SessionLocal() as session:
        embedding = EmbeddingClient()
        cat_repository = pg.CategoryRepositoryPG(session)
        emb_repository = pg.EmbeddingRepositoryPG(session)

        category_1 = dom.Category.create(
            name="Category 1",
            description="A category for testing purposes.",
            keywords=["test", "category", "embedding"],
        )

        category_2 = dom.Category.create(
            name="Category 2",
            description="Another category for testing experiment purposes.",
            keywords=["test", "category", "embedding"],
        )

        persisted_id_1 = cat_repository.save(category_1).id
        persisted_id_2 = cat_repository.save(category_2).id

        category_1 = category_1.with_id(persisted_id_1)
        category_2 = category_2.with_id(persisted_id_2)

        emb_1 = dom.Embedding.create(
            category_id=persisted_id_1,
            vector=embedding.generate(category_1.to_embedding_text()),
            content_hash=dom.SemanticHash.from_text(category_1.to_embedding_text()).value,
        )

        emb_2 = dom.Embedding.create(
            category_id=persisted_id_2,
            vector=embedding.generate(category_2.to_embedding_text()),
            content_hash=dom.SemanticHash.from_text(category_2.to_embedding_text()).value,
        )

        emb_repository.save(emb_1)
        emb_repository.save(emb_2)

        product = dom.Product.create(
            title="Test Product",
            description="A product for experimenting with category search.",
            keywords=["test", "product", "search"],
        )

        result = emb_repository.search_similar(
            query_vector=embedding.generate(product.to_embedding_text())
        )

        for emb, score in result:
            print(f"Found embedding: {emb.category_id}, Score: {score}")


        embedding.close()


def test_constraints():

    with SessionLocal() as session:

        embedding = EmbeddingClient()
        cat_repository = pg.CategoryRepositoryPG(session)
        prof_repository = pg.CategoryProfileRepositoryPG(session)
        emb_repository = pg.EmbeddingRepositoryPG(session)


        category_1 = dom.Category.create(
            id="cat_01",
            name="Category 1",
            url="https://example.com/cat_01",
            level=1,
            description="A category for testing purposes.",
            keywords=["test", "category", "embedding"],
        )

        category_2 = dom.Category.create(
            id="cat_02",
            name="Category 2",
            url="https://example.com/cat_02",
            level=1,
            description="Another category for testing experiment purposes.",
            keywords=["test", "category", "embedding"],
        )


        persisted_id_1 = cat_repository.save(category_1).id
        persisted_id_2 = cat_repository.save(category_2).id

        category_1 = category_1.with_id(persisted_id_1)
        category_2 = category_2.with_id(persisted_id_2)

        emb_1 = dom.Embedding.create(
            category_id=persisted_id_1,
            vector=embedding.generate(category_1.to_embedding_text()),
            content_hash=dom.SemanticHash.from_text(category_1.to_embedding_text()).value,
        )

        emb_2 = dom.Embedding.create(
            category_id=persisted_id_2,
            vector=embedding.generate(category_2.to_embedding_text()),
            content_hash=dom.SemanticHash.from_text(category_2.to_embedding_text()).value,
        )

        emb_repository.save(emb_1)
        emb_repository.save(emb_2)

        prof_1 = dom.CategoryProfile.create(
            category=category_1,
            constraints=dom.CategoryConstraints.create(
                allowed_genders=["hombre"],
                allowed_business_types=["B2B", "B2C"]
            )
        )

        prof_2 = dom.CategoryProfile.create(
            category=category_2,
            constraints=dom.CategoryConstraints.create(
                allowed_genders=["mujer"],
                allowed_business_types=["B2B"]
            )
        )

        prof_repository.save(prof_1)
        prof_repository.save(prof_2)

        product = dom.Product.create(
            title="Test Product",
            description="A product for experimenting with category search.",
            keywords=["test", "product", "search"],
            gender="hombre",
            business_type="B2B"
        )

        profiles = prof_repository.get_profiles_by_constraints(
            dom.CategoryConstraints.create(
                allowed_genders=[product.gender],
                allowed_business_types=[product.business_type],
                allowed_directions=[],
                allowed_brands=[],
                required_keywords=[]
            )
        )

        for profile in profiles:
            print(f"Found profile for category: {profile.category.name} - {profile.category.id} - {profile.constraints.allowed_genders} - {profile.constraints.allowed_business_types}")


        result = emb_repository.search_similar(
            query_vector=embedding.generate(product.to_embedding_text()),
            profiles=profiles
        )

        for emb, score in result:
            print(f"Found embedding: {emb.category_id}, Score: {score}")

        embedding.close()


def test_elegibility_policy():

    with SessionLocal() as session:

        embedding = EmbeddingClient()

        cat_repository = pg.CategoryRepositoryPG(session)
        prof_repository = pg.CategoryProfileRepositoryPG(session)
        emb_repository = pg.EmbeddingRepositoryPG(session)

        # -----------------------------
        # Create categories
        # -----------------------------
        category_1 = dom.Category.create(
            name="Category 1",
            description="Testing category 1.",
            keywords=["test", "category"],
        )

        category_2 = dom.Category.create(
            name="Category 2",
            description="Testing category 2.",
            keywords=["experiment"],
        )

        category_1 = cat_repository.save(category_1)
        category_2 = cat_repository.save(category_2)

        # -----------------------------
        # Create embeddings
        # -----------------------------
        emb_repository.save(
            dom.Embedding.create(
                category_id=category_1.id,
                vector=embedding.generate(category_1.to_embedding_text()),
                content_hash=dom.SemanticHash.from_text(
                    category_1.to_embedding_text()
                ).value,
            )
        )

        emb_repository.save(
            dom.Embedding.create(
                category_id=category_2.id,
                vector=embedding.generate(category_2.to_embedding_text()),
                content_hash=dom.SemanticHash.from_text(
                    category_2.to_embedding_text()
                ).value,
            )
        )

        # -----------------------------
        # Create profiles
        # -----------------------------
        prof_1 = prof_repository.save(
            dom.CategoryProfile.create(
                category=category_1,
                constraints=dom.CategoryConstraints.create(
                    allowed_genders=["hombre"],
                    allowed_business_types=["B2B", "B2C"]
                )
            )
        )

        prof_2 = prof_repository.save(
            dom.CategoryProfile.create(
                category=category_2,
                constraints=dom.CategoryConstraints.create(
                    allowed_genders=["mujer"],
                    allowed_business_types=["B2B"]
                )
            )
        )

        # -----------------------------
        # Product context
        # -----------------------------
        product = dom.Product.create(
            title="Test Product",
            description="Product for routing validation.",
            keywords=["test"],
            gender="hombre",
            business_type="B2B"
        )

        ctx = dom.ProductContext(
            gender=product.gender,
            business_type=product.business_type
        )

        # -----------------------------
        # Evaluate eligibility
        # -----------------------------
        policy = CategoryEligibilityPolicy()

        eligible_profiles = [
            p for p in [prof_1, prof_2]
            if policy.is_allowed(ctx, p)
        ]

        # -----------------------------
        # Assertions (REAL TEST)
        # -----------------------------
        print("Eligible profiles:")
        for profile in eligible_profiles:
            print(f" - {profile.category.name}")


        result = emb_repository.search_similar(
            query_vector=embedding.generate(product.to_embedding_text()),
            profiles=eligible_profiles
        )

        for emb, score in result:
            print(f"Found embedding: {emb.category_id}, Score: {score}")

        embedding.close()


def test_load_tree_policy():
    cmd = LoadCategoriesFromFileCommand(
        file_path="./data/suburbia.xlsx",
        business="Liverpool",
        brand=False
    )

    with SessionLocal() as session:

        embedding = EmbeddingClient()
        cat_repository = pg.CategoryRepositoryPG(session)
        prof_repository = pg.CategoryProfileRepositoryPG(session)
        emb_repository = pg.EmbeddingRepositoryPG(session, expected_dimension=768)
        llm_service = LLMClient()
        prompt_service = Prompt(
            file_path="./src/prompts/predict_sheet_data.yaml"
        )

        use_case = LoadCategoriesFromFileUseCase(
            session=session,
            category_repository=cat_repository,
            profiles_repository=prof_repository,
            embedding_repository=emb_repository,
            embedding_service=embedding,
            llm_service=llm_service,
            prompt_service=prompt_service,
        )

        use_case.execute(cmd)


def test():

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    DATABASE_URL = "postgresql+psycopg://postgres:admin@localhost:5432/product_routing"

    engine = create_engine(DATABASE_URL, echo=False)

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=True,
        bind=engine
    )

    with SessionLocal() as session:

        stmt = session.execute(
            text("""
                SELECT * FROM category_profiles
            """)
        )

        result = stmt.fetchall()

        for row in result:
            print(row)

        print("Result size:", len(result))


if __name__ == "__main__":
    # test_embedding_generation()
    # test_hashing()
    # test_unique_hashes()
    # test_constraints()
    # test_elegibility_policy()
    test_load_tree_policy()
    # test()