# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from typing import List
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.categories.category import Category
from domain.entities.embeddings.embedding import Embedding
from application.ports.embedding_repository import EmbeddingRepository
from application.ports.embedding_service import EmbeddingService


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
    Handles parallel embedding generation and deduplication.
    """

    EMBEDDING_WORKERS = 4
    BATCH_SIZE = 32

    def __init__(
        self,
        session: Session,
        embedding_repository: EmbeddingRepository,
        embedding_service: EmbeddingService,
    ):
        self.session = session
        self.embedding_repository = embedding_repository
        self.embedding_service = embedding_service

    # =============================================================
    # PUBLIC API
    # =============================================================
    def execute(self, cmd: LoadEmbeddingsCommand) -> List[Embedding]:
        """
        Generate embeddings for categories and save to database.
        Returns list of saved embeddings.
        """
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

        return self._commit_embeddings(embeddings)

    # =============================================================
    # EMBEDDING GENERATION
    # =============================================================
    def _generate_embeddings_parallel(
        self,
        categories: List[Category],
        embedding_texts: List[str],
    ) -> List[Embedding]:
        """Generate embeddings for all categories in parallel batches."""

        if not categories:
            return []

        vectors: List[float] = []

        # Generate vectors in batches
        for i in range(0, len(categories), self.BATCH_SIZE):
            batch_texts = embedding_texts[i:i + self.BATCH_SIZE]
            batch_vectors = self.embedding_service.generate_batch(batch_texts)
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
        """Get embedding text from category, with fallback."""
        embedding_text = category.to_embedding_text()

        # Fallback if text is empty
        if not embedding_text or not embedding_text.strip():
            embedding_text = f"{category.id} {category.name}"

        return embedding_text

    @staticmethod
    def _deduplicate_embeddings(
        embeddings: List[Embedding],
    ) -> List[Embedding]:
        """Remove duplicate embeddings by (category_id, content_hash)."""
        unique = {}
        for e in embeddings:
            unique[(e.category_id, e.content_hash)] = e
        return list(unique.values())

    # =============================================================
    # TRANSACTION
    # =============================================================
    def _commit_embeddings(
        self,
        embeddings: List[Embedding],
    ) -> List[Embedding]:
        """Save embeddings to database within a transaction."""

        try:
            self.embedding_repository.save_batch(embeddings)
            self.session.commit()
            print(f"✓ {len(embeddings)} embeddings saved")
            return embeddings

        except Exception as e:
            self.session.rollback()
            print(f"✗ Rollback embeddings: {e}")
            raise
