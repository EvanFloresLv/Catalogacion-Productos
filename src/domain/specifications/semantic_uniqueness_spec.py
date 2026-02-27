# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.categories.category import Category
from application.ports.category_repository import CategoryRepository
from domain.entities.categories.errors import CategoryDuplicateSemanticContentError


class SemanticUniquenessSpecification:

    def __init__(self, repository: CategoryRepository):
        self.repository = repository


    def ensure_unique(self, category: Category) -> None:
        existing = self.repository.find_by_semantic_hash(
            category.semantic_hash.value
        )

        if existing:
            raise CategoryDuplicateSemanticContentError(
                "Category with same semantic hash already exists."
            )