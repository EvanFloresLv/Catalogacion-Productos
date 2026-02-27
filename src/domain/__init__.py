# Entities
from .entities.categories.category import Category
from .entities.categories.category_profile import CategoryProfile
from .entities.categories.category_constraints import CategoryConstraints
from .entities.categories.category_exception import CategoryException
from .entities.categories.errors import CategoryError, CategoryNameError, CategoryDuplicateSemanticContentError

from .entities.classification.result import ClassificationResult, CategoryMatch
from .entities.classification.errors import ClassificationError, NoEligibleMatchesError, NoEligibleCategoriesError

from .entities.products.product import Product
from .entities.products.product_context import ProductContext
from .entities.products.product_category_exclusion import ProductCategoryExclusion
from .entities.products.errors import ProductError, ProductTitleError

from .entities.embeddings.embedding import Embedding

# Services
from .services.duplicate_detection_service import DuplicateDetectionService
from .services.category_semantic_search_service import CategorySemanticSearchService

# Specifications
from .specifications.eligibility_policy import CategoryEligibilityPolicy
from .specifications.semantic_uniqueness_spec import SemanticUniquenessSpecification

# Value objects
from .value_objects.semantic_hash import SemanticHash

__all__ = [
    "Category",
    "CategoryProfile",
    "CategoryConstraints",
    "CategoryException",
    "CategoryError",
    "CategoryNameError",
    "CategoryDuplicateSemanticContentError",
    "ClassificationResult",
    "CategoryMatch",
    "CategorySemanticSearchService",
    "ClassificationError",
    "NoEligibleMatchesError",
    "NoEligibleCategoriesError",
    "Product",
    "ProductCategoryExclusion",
    "ProductError",
    "ProductTitleError",
    "Embedding",
    "DuplicateDetectionService",
    "CategoryEligibilityPolicy",
    "SemanticUniquenessSpecification",
    "SemanticHash",
    "ProductContext",
    "ProductCategoryExclusion"
]