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
from application.ports.category_repository import CategoryRepository
from application.ports.category_profile_repository import CategoryProfileRepository

from domain.entities.categories.category_constraints import CategoryConstraints
from domain.entities.classification.result import ClassificationResult, CategoryMatch
from domain.entities.classification.errors import NoEligibleMatchesError

from domain.specifications.brand_business_policy import BrandBusinessPolicy


@dataclass(frozen=True)
class ClassifyProductCommand:
    product_sku: str
    top_k: int = 5


class ClassifyProductUseCase:

    def __init__(
        self,
        products: ProductRepository,
        profiles: CategoryProfileRepository,
        categories: CategoryRepository,
        embeddings: EmbeddingRepository,
        embeddings_service: EmbeddingService,
    ):
        self.products = products
        self.categories = categories
        self.profiles = profiles
        self.embeddings = embeddings
        self.embeddings_service = embeddings_service


    def execute(self, cmd: ClassifyProductCommand) -> List[ClassificationResult]:

        try:
            product = self.products.get_by_sku(cmd.product_sku)
            if not product:
                raise ValueError(f"Product with SKU {cmd.product_sku} not found.")

            query_vector = self.embeddings_service.generate(product.to_embedding_text())

            valid_businesses = []
            for business in product.business:
                if product.brand:
                    business_black_list = BrandBusinessPolicy.get_excluded_brands_for_business(business)

                    if str(product.brand).strip().upper() in business_black_list:
                        continue

                valid_businesses.append(business)

            print(f"\nValid business: {valid_businesses}")

            if not valid_businesses:
                raise NoEligibleMatchesError(
                    f"Brand '{product.brand}' is excluded from all businesses: {product.business}"
                )

            results = []

            for business in valid_businesses:

                constraints = CategoryConstraints.create(
                    gender=product.gender,
                    business=business,
                    direction=product.direction,
                    brand=product.brand,
                    is_leaf=True,  # Only consider leaf categories for product classification
                )

                matching_profiles = self.profiles.get_profiles_by_constraints(constraints)

                if not matching_profiles:
                    continue

                allowed_category_ids = {p.category.id for p in matching_profiles}

                raw_results = self.embeddings.search_similar(
                    query_vector=query_vector,
                    category_ids=allowed_category_ids,
                    limit=cmd.top_k
                )

                if not raw_results:
                    continue

                top_k = [
                    CategoryMatch(
                        category_id=embedding.category_id,
                        score=float(abs(score)),
                        path=self._build_category_path(embedding.category_id)
                    )
                    for embedding, score in raw_results[:cmd.top_k]
                ]

                results.append(ClassificationResult(
                    product_sku=product.sku,
                    best=top_k[0],
                    top_k=top_k
                ))

            if not results:
                raise NoEligibleMatchesError(
                    f"No eligible matches found for product {product.sku}"
                )

            return results
        except Exception as e:
            print(f"Error occurred while classifying product {cmd.product_sku}:")
            print(str(e))
            return []

    def _build_category_path(self, category_id: str) -> str:

        path_parts = []
        current_id = category_id
        max_depth = 10  # Prevent infinite loops
        depth = 0

        while current_id and depth < max_depth:
            category = self.categories.get_by_id(current_id)
            if not category:
                break

            path_parts.append(category.name)
            current_id = category.parent_id
            depth += 1

        # Reverse to get root to leaf order
        path_parts.reverse()

        return " > ".join(path_parts)