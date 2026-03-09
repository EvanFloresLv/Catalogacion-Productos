# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from typing import List
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.entities.categories.category import Category
from domain.entities.categories.category_constraints import CategoryConstraints
from domain.entities.categories.category_profile import CategoryProfile
from application.ports.category_profile_repository import CategoryProfileRepository


# ---------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------
@dataclass
class LoadCategoryProfilesCommand:
    categories: List[Category]


# ---------------------------------------------------------------------
# Use Case
# ---------------------------------------------------------------------
class LoadCategoryProfilesUseCase:
    """
    Creates and persists category profiles with constraints.
    """

    def __init__(
        self,
        session: Session,
        profiles_repository: CategoryProfileRepository,
    ):
        self.session = session
        self.profiles_repository = profiles_repository

    # =============================================================
    # PUBLIC API
    # =============================================================
    def execute(self, cmd: LoadCategoryProfilesCommand) -> List[CategoryProfile]:
        """
        Create profiles for categories and save to database.
        Returns list of saved profiles.
        """
        if not cmd.categories:
            return []

        # Create default profiles for all categories
        profiles = [
            self._create_profile(category)
            for category in cmd.categories
        ]

        # Deduplicate and save
        profiles = self._deduplicate_profiles(profiles)

        return self._commit_profiles(profiles)

    # =============================================================
    # PROFILE CREATION
    # =============================================================
    @staticmethod
    def _create_profile(category: Category) -> CategoryProfile:
        """Create a default profile for a category."""
        return CategoryProfile.create(
            category=category,
            constraints=CategoryConstraints(),
        )

    # =============================================================
    # HELPERS
    # =============================================================
    @staticmethod
    def _deduplicate_profiles(
        profiles: List[CategoryProfile],
    ) -> List[CategoryProfile]:
        """Remove duplicate profiles by category_id."""
        unique = {}
        for profile in profiles:
            unique[profile.category.id] = profile
        return list(unique.values())

    # =============================================================
    # TRANSACTION
    # =============================================================
    def _commit_profiles(
        self,
        profiles: List[CategoryProfile],
    ) -> List[CategoryProfile]:
        """Save profiles to database within a transaction."""

        try:
            saved = self.profiles_repository.save_batch(profiles)
            self.session.commit()
            print(f"✓ {len(saved)} profiles saved")
            return saved

        except Exception as e:
            self.session.rollback()
            print(f"✗ Rollback profiles: {e}")
            raise
