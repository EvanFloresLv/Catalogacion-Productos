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
from application.ports.product_repository import ProductRepository
from application.ports.category_profile_repository import CategoryProfileRepository
from application.ports.exclusion_repository import ExclusionRepository
from application.ports.embedding_repository import EmbeddingRepository

from domain.specifications.eligibility_policy import CategoryEligibilityPolicy
from domain.entities.products.product_context import ProductContext
from domain.entities.classification.result import ClassificationResult, CategoryMatch
from domain.entities.classification.errors import NoEligibleCategoriesError, NoEligibleMatchesError

from domain.value_objects.semantic_hash import SemanticHash


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
        embeddings: EmbeddingRepository,
        policy: CategoryEligibilityPolicy,
    ):
        self.products = products
        self.profiles = profiles
        self.exclusions = exclusions
        self.embeddings = embeddings
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

        query = SemanticHash.from_text(product.to_embedding_text()).value

        # Buscamos un top-N grande para que el filtrado no mate resultados
        raw = self.embeddings

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