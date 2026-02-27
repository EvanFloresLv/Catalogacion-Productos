# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.category_repository import CategoryRepository
from application.ports.embedding_repository import EmbeddingRepository
from application.ports.embedding_service import EmbeddingService

from utils.vectors import normalize_vector


class CategorySemanticSearchService:

    def __init__(
        self,
        embedding_repo: EmbeddingRepository,
        category_repo: CategoryRepository,
        embedding_service: EmbeddingService,
        limit: int = 10
    ):
        self.embedding_repo = embedding_repo
        self.category_repo = category_repo
        self.embedding_service = embedding_service
        self.limit = limit


    def search(self, text: str):

        return self.embedding_repo.search_similar(
            query_vector=self.embedding_service.generate(text),
            limit=self.limit,
        )