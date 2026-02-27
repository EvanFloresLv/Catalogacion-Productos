# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from abc import ABC, abstractmethod
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.products.product_category_exclusion import ProductCategoryExclusion


class ExclusionRepository(ABC):

    @abstractmethod
    def get_excluded_category_ids(self, product_id: UUID) -> set[UUID]:
        raise NotImplementedError


    @abstractmethod
    def add_exclusion(self, product_id: UUID, category_id: UUID, reason: str) -> None:
        raise NotImplementedError


    @abstractmethod
    def add_exclusions_batch(self, exclusions: list[ProductCategoryExclusion]) -> None:
        raise NotImplementedError