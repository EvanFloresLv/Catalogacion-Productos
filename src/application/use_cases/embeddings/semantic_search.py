# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.embedding_service import EmbeddingService
from application.ports.category_repository import CategoryRepository
from application.ports.embedding_repository import EmbeddingRepository


class SemanticSearchUseCase:

    def __init__(
        self,
        embedding_service: EmbeddingService,
        embedding_repo: EmbeddingRepository,
        category_repo: CategoryRepository
    ):
        self.embedding_service = embedding_service
        self.embedding_repo = embedding_repo
        self.category_repo = category_repo


    def execute(self, query: str, limit: int = 5):

        query_vector = self.embedding_service.generate(query)

        embeddings = self.embedding_repo.semantic_search(
            query_vector,
            limit,
        )

        category_ids = [emb.category_id for emb in embeddings]

        return self.category_repo.get_by_ids(category_ids)