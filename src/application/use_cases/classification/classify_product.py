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
from application.ports.outbound.category_profile_repository import CategoryProfileRepository
from application.ports.outbound.exclusion_repository import ExclusionRepository
from application.ports.outbound.embedding_service import EmbeddingService
from application.ports.outbound.vector_index import VectorIndex

from domain.classification.eligibility_policy import CategoryEligibilityPolicy
from domain.classification.product_context import ProductContext
from domain.classification.result import ClassificationResult, CategoryMatch
from domain.classification.errors import NoEligibleCategoriesError, NoEligibleMatchesError


@dataclass(frozen=True)
class ClassifyProductCommand:
    product_id: UUID
    top_k: int = 5


class ClassifyProductUseCase:

    def __init__(
        self,
        products: ProductRepository,
        profiles: CategoryProfileRepository,
        exclusions: ExclusionRepository,
        embeddings: EmbeddingService,
        index: VectorIndex,
        policy: CategoryEligibilityPolicy,
    ):
        self.products = products
        self.profiles = profiles
        self.exclusions = exclusions
        self.embeddings = embeddings
        self.index = index
        self.policy = policy


    def execute(self, cmd: ClassifyProductCommand) -> ClassificationResult:

        product = self.products.get_by_id(cmd.product_id)
        if not product:
            raise ValueError(f"Product with ID {cmd.product_id} not found.")


        ctx = ProductContext(
            gender=product.gender,
            business_type=product.business_type
        )

        profiles = self.profiles.list_all_profiles()
        excluded = self.exclusions.get_excluded_category_ids(product.id)

        allowed_ids = set()
        for prof in profiles:
            cid = prof.category.id
            if cid in excluded:
                continue
            if self.policy.is_allowed(ctx, prof):
                allowed_ids.add(cid)

        if not allowed_ids:
            raise NoEligibleCategoriesError("No eligible categories for this product")

        query = self.embeddings.embed_text(product.to_embedding_text())

        # Buscamos un top-N grande para que el filtrado no mate resultados
        raw = self.index.search(query, top_k=max(cmd.top_k * 10, 50))

        filtered = [(cid, abs(score)) for cid, score in raw if cid in allowed_ids]
        if not filtered:
            raise NoEligibleMatchesError("No eligible matches found")

        filtered = filtered[: cmd.top_k]
        best_id, best_score = filtered[0]

        return ClassificationResult(
            product_id=product.id,
            best=CategoryMatch(category_id=best_id, score=float(best_score)),
            top_k=[CategoryMatch(category_id=cid, score=float(score)) for cid, score in filtered],
        )