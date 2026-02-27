# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------
from uuid import UUID
from typing import List, Tuple, Dict

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.embeddings.embedding import Embedding
from domain.entities.categories.category import Category
from application.ports.embedding_repository import EmbeddingRepository
from application.ports.embedding_service import EmbeddingService
from application.ports.category_repository import CategoryRepository
from domain.value_objects.semantic_hash import SemanticHash


class GenerateEmbeddingsUseCase:

    def __init__(
        self,
        embedding_service: EmbeddingService,
        embedding_repo: EmbeddingRepository,
        category_repo: CategoryRepository,
    ):
        self.embedding_service = embedding_service
        self.embedding_repo = embedding_repo
        self.category_repo = category_repo


    def execute(self) -> List[Embedding]:

        categories: List[Category] = self.category_repo.get_all()

        if not categories:
            return []

        category_ids = [category.id for category in categories]

        existing_embeddings = self.embedding_repo.get_by_category_ids(category_ids)

        if not existing_embeddings:
            print("No existing embeddings found.")
            return []

        existing_map: Dict[UUID, Embedding] = {
            emb.category_id: emb for emb in existing_embeddings
        }

        categories_to_generate: List[Tuple[Category, str]] = []
        valid_existing_embeddings: List[Embedding] = []

        for category in categories:

            current_hash = SemanticHash.from_text(category.to_embedding_text()).value
            existing: Embedding = existing_map.get(category.id)

            if not existing:
                categories_to_generate.append((category, current_hash))
                continue

            if existing.content_hash != current_hash:
                categories_to_generate.append((category, current_hash))
                continue

            valid_existing_embeddings.append(existing)

        new_embeddings: List[Embedding] = []

        if categories_to_generate:

            generated_vectors = self.embedding_service.generate_batch(
                [c.description for c, _ in categories_to_generate]
            )

            for (category, content_hash), vector in zip(
                categories_to_generate,
                generated_vectors,
            ):
                embedding = Embedding.create(
                    category_id=category.id,
                    vector=vector,
                    content_hash=content_hash,
                )
                new_embeddings.append(embedding)

            self.embedding_repo.save_batch(new_embeddings)

        return valid_existing_embeddings + new_embeddings