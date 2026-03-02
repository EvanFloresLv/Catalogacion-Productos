# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from abc import ABC, abstractmethod
from typing import Iterable

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.categories.category_constraints import CategoryConstraints
from domain.entities.categories.category_profile import CategoryProfile


class CategoryProfileRepository(ABC):

    @abstractmethod
    def list_all_profiles(self) -> list[CategoryProfile]:
        raise NotImplementedError


    @abstractmethod
    def get_profiles_by_constraints(self, constraints: CategoryConstraints) -> list[CategoryProfile]:
        raise NotImplementedError


    @abstractmethod
    def save(
        self,
        profile: CategoryProfile
    ) -> None:
        raise NotImplementedError


    @abstractmethod
    def save_batch(
        self,
        profiles: Iterable[CategoryProfile]
    ) -> None:
        raise NotImplementedError