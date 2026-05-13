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
from domain.products.product import Product


class ProductRepository(ABC):

    @abstractmethod
    def save(
        self,
        product: Product
    ) -> None:
        """Saves a category to the repository."""
        raise NotImplementedError


    @abstractmethod
    def get_by_id(
        self,
        product_id: UUID
    ) -> Product | None:
        """Retrieves a product by its ID from the repository."""
        raise NotImplementedError