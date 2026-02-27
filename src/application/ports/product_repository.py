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
from domain.entities.products.product import Product


class ProductRepository(ABC):

    @abstractmethod
    def save(
        self,
        product: Product
    ) -> None:
        """Saves a category to the repository."""
        raise NotImplementedError


    @abstractmethod
    def save_batch(
        self,
        products: list[Product]
    ) -> None:
        """Saves a batch of products to the repository."""
        raise NotImplementedError


    @abstractmethod
    def get_by_id(
        self,
        product_id: UUID
    ) -> Product | None:
        """Retrieves a product by its ID from the repository."""
        raise NotImplementedError


    @abstractmethod
    def get_by_ids(
        self,
        product_ids: list[UUID]
    ) -> list[Product | None]:
        """Retrieves products by their IDs from the repository."""
        raise NotImplementedError


    @abstractmethod
    def get_all(
        self
    ) -> list[Product]:
        """Retrieves all products from the repository."""
        raise NotImplementedError