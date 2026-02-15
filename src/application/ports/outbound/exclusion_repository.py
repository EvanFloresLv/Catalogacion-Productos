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


class ExclusionRepository(ABC):

    @abstractmethod
    def get_excluded_category_ids(self, product_id: UUID) -> set[UUID]:
        raise NotImplementedError


    @abstractmethod
    def add_exclusion(self, product_id: UUID, category_id: UUID, reason: str) -> None:
        raise NotImplementedError