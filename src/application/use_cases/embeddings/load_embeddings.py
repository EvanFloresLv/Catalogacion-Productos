# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from typing import List
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.category import Category
from domain.entities.embedding import Embedding
from domain.repositories.embedding_repository import EmbeddingRepository
from domain.services.embedding_service import EmbeddingService
from domain.aggregates.embedding_catalog import EmbeddingCatalog

from shared.kernel.unit_of_work import UnitOfWork


# ---------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------
@dataclass
class LoadEmbeddingsCommand:
    categories: List[Category]


# ---------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------
class LoadEmbeddingsUseCase:
    """
    Generates and persists embeddings for categories.

    Architecture:
      - Uses UnitOfWork for transactional commit + event dispatch
    """

    EMBEDDING_WORKERS = 4
    BATCH_SIZE = 32

    def __init__(
        self,
        repo: EmbeddingRepository,
        service: EmbeddingService,
        uow: UnitOfWork,
    ):
        self.repo = repo
        self.service = service
        self.uow = uow

    # =============================================================
    # PUBLIC
    # =============================================================
    def execute(self, cmd: LoadEmbeddingsCommand) -> List[Embedding]:

        catalog = EmbeddingCatalog()
        self.uow.register(catalog)

        if not cmd.categories:
            return []

        # Generate embedding texts from categories
        embedding_texts = [
            self._get_embedding_text(cat)
            for cat in cmd.categories
        ]

        # Generate embeddings in parallel
        embeddings = self._generate_embeddings_parallel(
            cmd.categories,
            embedding_texts,
        )

        # Deduplicate and save
        embeddings = self._deduplicate_embeddings(embeddings)

        catalog.add_embeddings_batch(embeddings)
        saved = self.repo.save_batch(catalog.embeddings)

        self.uow.commit()

        return saved

    # =============================================================
    # EMBEDDING GENERATION
    # =============================================================
    def _generate_embeddings_parallel(
        self,
        categories: List[Category],
        embedding_texts: List[str],
    ) -> List[Embedding]:

        if not categories:
            return []

        vectors: List[float] = []

        # Generate vectors in batches
        for i in range(0, len(categories), self.BATCH_SIZE):
            batch_texts = embedding_texts[i:i + self.BATCH_SIZE]
            batch_vectors = self.service.generate_batch(batch_texts)
            vectors.extend(batch_vectors)

        # Create Embedding entities
        embeddings = []
        for category, vector in zip(categories, vectors):
            embeddings.append(
                Embedding.create(
                    category_id=category.id,
                    vector=vector,
                    content_hash=category.semantic_hash,
                )
            )

        return embeddings

    # =============================================================
    # HELPERS
    # =============================================================
    @staticmethod
    def _get_embedding_text(category: Category) -> str:
        embedding_text = category.to_embedding_text()

        # Fallback if text is empty
        if not embedding_text or not embedding_text.strip():
            embedding_text = f"{category.id} {category.name}"

        return embedding_text

    @staticmethod
    def _deduplicate_embeddings(
        embeddings: List[Embedding],
    ) -> List[Embedding]:

        unique = {}
        for e in embeddings:
            unique[(e.category_id, e.content_hash)] = e
        return list(unique.values())