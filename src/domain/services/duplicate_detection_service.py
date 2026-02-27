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
from domain.specifications.semantic_uniqueness_spec import (
    SemanticUniquenessSpecification,
)


class DuplicateDetectionService:


    def __init__(self, uniqueness_spec: SemanticUniquenessSpecification):
        self.uniqueness_spec = uniqueness_spec


    def validate(self, category: Category) -> None:
        self.uniqueness_spec.ensure_unique(category)