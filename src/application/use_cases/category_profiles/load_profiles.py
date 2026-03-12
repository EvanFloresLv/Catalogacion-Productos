# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import json
from typing import List, Dict, Optional
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
from domain.specifications.brand_business_policy import BrandBusinessPolicy
from application.ports.category_profile_repository import CategoryProfileRepository


# ---------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------
@dataclass
class LoadCategoryProfilesCommand:
    categories_by_sheet: Dict
    metadata: Optional[Dict[str, str]] = None


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

        Logic:
        1. If business is provided in metadata -> apply to all profiles
        2. If brand mode is enabled -> use sheet names as brands
        3. Otherwise -> use LLM metadata (direccion, genero) to create constraints

        Returns list of saved profiles.
        """
        if not cmd.categories_by_sheet:
            return []

        # Extract business and brand settings from metadata
        global_business = None
        is_brand_mode = False

        if cmd.metadata:
            global_business = cmd.metadata.get("business")
            is_brand_mode = cmd.metadata.get("brand", False)

        # Build metadata lookup by sheet name
        metadata_by_sheet = {}
        if cmd.metadata and not is_brand_mode:
            try:
                # Parse JSON string if needed
                if isinstance(cmd.metadata.get("data"), str):
                    metadata_list = json.loads(cmd.metadata.get("data", "[]"))
                else:
                    metadata_list = cmd.metadata.get("data", [])

                # Create lookup dict
                for item in metadata_list:
                    sheet_name = item.get("sheet_name")
                    if sheet_name:
                        metadata_by_sheet[sheet_name] = {
                            "direccion": item.get("direccion"),
                            "genero": item.get("genero"),
                        }
            except Exception as e:
                print(f"⚠ Warning: Could not parse metadata: {e}")

        # Create profiles for all categories
        all_profiles = []
        for sheet_name, sheet_data in cmd.categories_by_sheet.items():
            categories = sheet_data.get("categories", [])
            sheet_metadata = metadata_by_sheet.get(sheet_name, {})

            for category in categories:
                profile = self._create_profile(
                    category=category,
                    sheet_name=sheet_name,
                    sheet_metadata=sheet_metadata,
                    global_business=global_business,
                    is_brand_mode=is_brand_mode,
                )
                all_profiles.append(profile)

        # Deduplicate and save
        all_profiles = self._deduplicate_profiles(all_profiles)

        return self._commit_profiles(all_profiles)

    # =============================================================
    # PROFILE CREATION
    # =============================================================
    def _create_profile(
        self,
        category: Category,
        sheet_name: str,
        sheet_metadata: Dict[str, Optional[str]],
        global_business: Optional[str],
        is_brand_mode: bool,
    ) -> CategoryProfile:
        """
        Create profile with constraints based on category type and mode:

        Priority order:
        1. If global_business is set -> apply to all profiles
        2. If is_brand_mode is True -> use category.brand (from sheet name)
           AND apply brand business policy to set allowed businesses
        3. Otherwise -> use LLM metadata (direccion -> business, genero -> gender)
        """

        # Initialize all constraint fields to None
        gender = None
        direccion = None
        brand = None
        business = None

        if global_business:
            business = str(global_business).lower().strip()

        if is_brand_mode:
            brand = str(sheet_name).lower().strip()

        if sheet_metadata:
            genero = sheet_metadata.get("genero")
            direccion = sheet_metadata.get("direccion")

            # Filter out "Nulo" values
            gender = genero if genero and genero.lower() != "nulo" else None
            direction = direccion if direccion and direccion.lower() != "nulo" else None

            if gender or direction:
                print(f"  LLM metadata: {category.name} (gender: {gender}, direction: {direction})")

        # Create constraints with all fields (convert None to empty string)
        constraints = CategoryConstraints.create(
            gender=gender,
            business=business,
            brand=brand,
            direction=direccion
        )

        return CategoryProfile.create(
            category=category,
            constraints=constraints,
        )

    # =============================================================
    # HELPERS
    # =============================================================
    @staticmethod
    def _deduplicate_profiles(
        profiles: List[CategoryProfile],
    ) -> List[CategoryProfile]:
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
        try:
            saved = self.profiles_repository.save_batch(profiles)
            self.session.commit()
            print(f"✓ {len(saved)} profiles saved")
            return saved

        except Exception as e:
            self.session.rollback()
            print(f"✗ Rollback profiles: {e}")
            raise
