from infrastructure.embeddings.gemini.client import EmbeddingClientHTTP

import domain as dom
import application as app
import infrastructure.persistence.postgresql as pg

from infrastructure.persistence.postgresql.session import SessionLocal


def test_embedding_generation():

    embedding = EmbeddingClientHTTP()

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
        embedding = EmbeddingClientHTTP()
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
            print(f"Found embedding: {emb.content_hash}, Score: {score}")

        embedding.close()



if __name__ == "__main__":
    # test_embedding_generation()
    # test_hashing()
    test_unique_hashes()