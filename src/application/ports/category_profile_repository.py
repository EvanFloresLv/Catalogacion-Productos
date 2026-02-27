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
from domain.entities.categories.category_profile import CategoryProfile


class CategoryProfileRepository(ABC):

    @abstractmethod
    def list_all_profiles(self) -> list[CategoryProfile]:
        raise NotImplementedError


    @abstractmethod
    def upsert_profile(
        self,
        category_id: UUID,
        keywords: list[str],
        allowed_genders: set[str] | None,
        allowed_business_types: set[str] | None,
    ) -> None:
        raise NotImplementedError