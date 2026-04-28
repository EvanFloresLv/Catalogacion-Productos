# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from dataclasses import dataclass
from typing import List

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.repositories.product_repository import ProductRepository
from domain.repositories.embedding_repository import EmbeddingRepository
from domain.services.embedding_service import EmbeddingService

from application.services.category_query_service import CategoryQueryService
from application.dto.queries.category_queries import GetCategoriesByConstraintsQuery

from domain.entities.result import ClassificationResult, CategoryMatch
from domain.aggregates.product_classification_catalog import ProductClassification

from shared.kernel.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class ClassifyProductCommand:
    product_sku: str
    top_k: int = 5


class ClassifyProductUseCase:
    """
    Classifies a product against eligible category profiles using embeddings.

    Architecture:
      - Uses CategoryQueryService (CQRS read-side) for profile and path queries
      - Uses ProductClassification aggregate to enforce business rules
      - Uses UnitOfWork to persist domain events
    """

    def __init__(
        self,
        products: ProductRepository,
        category_query_service: CategoryQueryService,
        embeddings: EmbeddingRepository,
        embeddings_service: EmbeddingService,
        uow: UnitOfWork,
    ):
        self.products = products
        self.category_query_service = category_query_service
        self.embeddings = embeddings
        self.embeddings_service = embeddings_service
        self.uow = uow

    def execute(self, cmd: ClassifyProductCommand) -> List[ClassificationResult]:

        try:
            product = self.products.get_by_sku(cmd.product_sku)

            if not product:
                raise ValueError(f"Product with SKU {cmd.product_sku} not found.")

            # Build the aggregate
            classification = ProductClassification(product)
            self.uow.register(classification)

            query_vector = self.embeddings_service.generate(product.to_embedding_text())

            # Delegate brand/business filtering to the aggregate
            valid_businesses = classification.get_valid_businesses()

            print(f"\nValid business: {valid_businesses}")

            results = []

            for business in valid_businesses:

                # CQRS read-side: query categories by constraints
                query = GetCategoriesByConstraintsQuery(
                    gender=product.gender,
                    business=business,
                    direction=product.direction,
                    brand=product.brand,
                    is_leaf=True,
                )

                matching_categories = self.category_query_service.get_categories_by_constraints(query)

                if not matching_categories:
                    continue

                allowed_category_ids = {c.id for c in matching_categories}

                raw_results = self.embeddings.search_similar(
                    query_vector=query_vector,
                    category_ids=list(allowed_category_ids),
                    limit=cmd.top_k,
                )

                if not raw_results:
                    continue

                top_k = [
                    CategoryMatch(
                        category_id=embedding.category_id,
                        score=float(abs(score)),
                        path=self.category_query_service.build_category_path(embedding.category_id),
                    )
                    for embedding, score in raw_results[:cmd.top_k]
                ]

                # Aggregate records the classification and emits event
                result = classification.record_classification(
                    business=business,
                    top_k=top_k,
                )
                results.append(result)

            if not results:
                raise Exception(
                    f"No eligible matches found for product {product.sku}"
                )

            # Commit: persist events to outbox, dispatch handlers
            self.uow.commit()

            return results

        except Exception as e:
            self.uow.rollback()
            print(f"Error occurred while classifying product {cmd.product_sku}:")
            print(str(e))
            return []