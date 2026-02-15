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


class ProductCategoryExceptionRepository(ABC):

    @abstractmethod
    def get_excluded_category_ids(self, product_id: UUID) -> set[UUID]:
        raise NotImplementedError