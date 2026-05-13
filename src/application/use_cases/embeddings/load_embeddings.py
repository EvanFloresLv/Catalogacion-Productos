# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import logging
from typing import List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.category import Category
from domain.entities.embedding import Embedding
from domain.repositories.embedding_repository import EmbeddingRepository
from domain.services.embedding_service import EmbeddingService
from domain.aggregates.embedding_catalog import EmbeddingCatalog

from shared.kernel.unit_of_work import UnitOfWork


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    EMBEDDING_WORKERS = 4
    BATCH_SIZE = 50

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

        try:

            logger.info(f"Loading embeddings for categories: {len(cmd.categories)}")

            catalog = EmbeddingCatalog()
            self.uow.register(catalog)

            if not cmd.categories:
                return []

            # Skip categories that already have embeddings with same hash
            categories = self._filter_new_categories(cmd.categories)
            logger.info(f"Categories needing embeddings: {len(categories)} (skipped {len(cmd.categories) - len(categories)} existing)")

            if not categories:
                logger.info("All categories already have up-to-date embeddings")
                return []

            # Generate embedding texts from categories
            embedding_texts = [
                self._get_embedding_text(cat)
                for cat in categories
            ]

            # Generate embeddings in parallel
            embeddings = self._generate_embeddings_parallel(
                categories,
                embedding_texts,
            )

            # Deduplicate and save
            embeddings = self._deduplicate_embeddings(embeddings)

            catalog.add_embeddings_batch(embeddings)
            saved = self.repo.save_batch(catalog.embeddings)

            self.uow.commit()

            logger.info(f"Saved embeddings for categories: {len(saved)}")

            return saved

        except Exception as e:
            logger.error(f"Error loading embeddings: {e}")
            self.uow.rollback()
            raise e

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

        total_batches = (len(categories) + self.BATCH_SIZE - 1) // self.BATCH_SIZE
        logger.info(
            f"Generating embeddings: {len(categories)} categories, "
            f"{total_batches} batches of {self.BATCH_SIZE}, "
            f"{self.EMBEDDING_WORKERS} workers"
        )

        # Split into batches
        batches = []
        for i in range(0, len(categories), self.BATCH_SIZE):
            batch_cats = categories[i:i + self.BATCH_SIZE]
            batch_texts = embedding_texts[i:i + self.BATCH_SIZE]
            batches.append((batch_cats, batch_texts))

        embeddings: List[Embedding] = []

        def process_batch(batch_idx, cats, texts):
            vectors = self.service.generate_batch(texts)
            result = []
            for category, vector in zip(cats, vectors):
                result.append(
                    Embedding.create(
                        category_id=category.id,
                        vector=vector,
                        content_hash=category.semantic_hash,
                    )
                )
            logger.info(f"Batch {batch_idx + 1}/{total_batches} done ({len(result)} embeddings)")
            return result

        with ThreadPoolExecutor(max_workers=self.EMBEDDING_WORKERS) as executor:
            futures = {
                executor.submit(process_batch, idx, cats, texts): idx
                for idx, (cats, texts) in enumerate(batches)
            }
            for future in as_completed(futures):
                embeddings.extend(future.result())

        return embeddings

    # =============================================================
    # HELPERS
    # =============================================================
    def _filter_new_categories(self, categories: List[Category]) -> List[Category]:
        """Skip categories whose embeddings already exist with the same content hash."""
        cat_ids = [cat.id for cat in categories]
        existing = self.repo.get_by_category_ids(cat_ids)
        existing_map = {e.category_id: e.content_hash for e in existing}

        new_categories = []
        for cat in categories:
            cached_hash = existing_map.get(cat.id)
            if cached_hash and cached_hash == cat.semantic_hash:
                continue
            new_categories.append(cat)
        return new_categories

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