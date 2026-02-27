# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from application.ports.category_repository import CategoryRepository
from application.ports.category_profile_repository import CategoryProfileRepository


@dataclass(frozen=True)
class UpsertCategoryProfileCommand:
    category_id: UUID
    keywords: list[str]
    allowed_genders: set[str] | None
    allowed_business_types: set[str] | None


class UpsertCategoryProfileUseCase:

    def __init__(self, categories: CategoryRepository, profiles: CategoryProfileRepository):
        self.categories = categories
        self.profiles = profiles


    def execute(self, cmd: UpsertCategoryProfileCommand) -> dict:
        cat = self.categories.get_by_id(cmd.category_id)

        if cat is None:
            raise ValueError("Category not found")

        self.profiles.upsert_profile(
            category_id=cmd.category_id,
            keywords=cmd.keywords,
            allowed_genders=cmd.allowed_genders,
            allowed_business_types=cmd.allowed_business_types,
        )

        return {"ok": True}
