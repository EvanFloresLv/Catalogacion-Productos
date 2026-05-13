# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.outbound.category_repository import CategoryRepository
from application.ports.outbound.category_embedding_repository import CategoryEmbeddingRepository
from application.ports.outbound.embedding_service import EmbeddingService
from application.ports.outbound.vector_index import VectorIndex


class RebuildCategoryEmbeddingsUseCase:

    def __init__(
        self,
        categories: CategoryRepository,
        embedding_repo: CategoryEmbeddingRepository,
        embedding_service: EmbeddingService,
        vector_index: VectorIndex
    ):
        self.categories = categories
        self.embedding_repo = embedding_repo
        self.embedding_service = embedding_service
        self.vector_index = vector_index


    def execute(self) -> int:

        cats = self.categories.get_all()

        if not cats:
            return 0


        vectors: list[tuple] = []

        for cat in cats:
            text = f"CATEGORY: {cat.name}"
            vector = self.embedding_service.embed_text(text)
            vectors.append((cat.id, vector))

        dim = len(vectors[0][1])
        self.vector_index.reset(dim)

        for cat_id, vector in vectors:
            self.embedding_repo.upsert(cat_id, vector)
            self.vector_index.upsert(cat_id, vector)


        return len(vectors)