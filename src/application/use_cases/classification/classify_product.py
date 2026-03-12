# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from dataclasses import dataclass
from typing import List

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.product_repository import ProductRepository
from application.ports.embedding_service import EmbeddingService
from application.ports.embedding_repository import EmbeddingRepository
from application.ports.category_profile_repository import CategoryProfileRepository

from domain.entities.categories.category_constraints import CategoryConstraints
from domain.entities.classification.result import ClassificationResult, CategoryMatch
from domain.entities.classification.errors import NoEligibleMatchesError


@dataclass(frozen=True)
class ClassifyProductCommand:
    product_sku: str
    top_k: int = 5


class ClassifyProductUseCase:

    def __init__(
        self,
        products: ProductRepository,
        profiles: CategoryProfileRepository,
        embeddings: EmbeddingRepository,
        embeddings_service: EmbeddingService,
    ):
        self.products = products
        self.profiles = profiles
        self.embeddings = embeddings
        self.embeddings_service = embeddings_service


    def execute(self, cmd: ClassifyProductCommand) -> List[ClassificationResult]:

        # Get product by SKU
        product = self.products.get_by_sku(cmd.product_sku)

        if not product:
            raise ValueError(f"Product with SKU {cmd.product_sku} not found.")

        results = []

        for business in product.business:
            # Create constraints from product attributes for current business
            constraints = CategoryConstraints.create(
                gender=product.gender,
                business=business,
                direction=product.direction,
                brand=product.brand
            )

            print(f"\n{'='*50}")
            print(f"Processing business: {business}")
            print(f"{'='*50}")
            print("Product constraints:")
            print(f"  - SKU: {product.sku}")
            print(f"  - Gender: {product.gender}")
            print(f"  - Business: {business}")
            print(f"  - Direction: {product.direction}")
            print(f"  - Brand: {product.brand}")

            # Get profiles that match the product constraints
            matching_profiles = self.profiles.get_profiles_by_constraints(
                constraints=constraints
            )

            print(f"\nMatching profiles found: {len(matching_profiles)}")

            # Extract category IDs from matching profiles
            allowed_category_ids = {profile.category.id for profile in matching_profiles}

            if not allowed_category_ids:
                # Show helpful error message
                print(f"\nWARNING: No categories match the product constraints for business '{business}'")
                print(f"  gender={product.gender}, business={business}, "
                      f"direction={product.direction}, brand={product.brand}")
                print("Skipping this business and continuing with next...\n")
                continue

            # Generate semantic hash from product
            query_product = self.embeddings_service.generate(product.to_embedding_text())

            # Search for similar embeddings
            raw_results = self.embeddings.search_similar(
                query_vector=query_product,
                category_ids=allowed_category_ids,
                limit=cmd.top_k * 3  # Get more results for filtering
            )

            # Extract category IDs and scores from embedding results
            # raw_results is List[Tuple[Embedding, float]]
            filtered = [
                (embedding.category_id, abs(score))
                for embedding, score in raw_results
                if embedding.category_id in allowed_category_ids
            ]

            if not filtered:
                print(f"\nWARNING: No eligible matches found after filtering for business '{business}'")
                print("Skipping this business and continuing with next...\n")
                continue

            # Get top K results
            filtered = filtered[:cmd.top_k]
            best_id, best_score = filtered[0]

            results.append(ClassificationResult(
                product_sku=product.sku,
                best=CategoryMatch(category_id=best_id, score=float(best_score)),
                top_k=[
                    CategoryMatch(category_id=cid, score=float(score))
                    for cid, score in filtered
                ],
            ))

        # If no results were generated for any business, raise an error
        if not results:
            raise NoEligibleMatchesError(
                f"No eligible matches found for product {product.sku} across all businesses: {product.business}"
            )

        return results