# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from dataclasses import dataclass
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.outbound.product_repository import ProductRepository
from application.ports.outbound.embedding_service import EmbeddingService
from application.ports.outbound.vector_index import VectorIndex
from domain.classification.result import ClassificationResult, CategoryMatch


@dataclass(frozen=True)
class ClassifyProductCommand:
    product_id: UUID
    top_k: int = 5



class ClassifyProductUseCase:

    def __init__(
        self,
        products: ProductRepository,
        embeddings: EmbeddingService,
        vector_index: VectorIndex
    ):
        self.products = products
        self.embeddings = embeddings
        self.vector_index = vector_index


    def execute(self, cmd: ClassifyProductCommand) -> ClassificationResult:

        product = self.products.get_by_id(cmd.product_id)
        if not product:
            raise ValueError(f"Product with ID {cmd.product_id} not found.")

        embedding = self.embeddings.embed_text(product.description)
        if not embedding:
            raise ValueError(f"Failed to create embedding for product ID {cmd.product_id}.")

        matches = self.vector_index.search(embedding, top_k=cmd.top_k)
        if not matches:
            raise ValueError(f"No matches found for product ID {cmd.product_id}.")

        best_id, best_score = matches[0]

        return ClassificationResult(
            product_id=cmd.product_id,
            best=CategoryMatch(category_id=best_id, score=best_score),
            matches=[
                CategoryMatch(category_id=cat_id, score=score)
                for cat_id, score in matches
            ]
        )