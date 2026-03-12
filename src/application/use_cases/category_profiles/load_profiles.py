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

        # Build metadata lookups
        metadata_by_sheet = {}      # For normal mode (sheet_name lookup)
        metadata_by_category = {}   # For brand mode (category_id lookup)

        if cmd.metadata:
            # Get metadata indexed by sheet (normal mode)
            if "by_sheet" in cmd.metadata:
                metadata_by_sheet = cmd.metadata["by_sheet"]

            # Get metadata indexed by category (brand mode)
            if "by_category" in cmd.metadata:
                metadata_by_category = cmd.metadata["by_category"]

            # Legacy: Parse from data list if new structure not available
            if not metadata_by_sheet and not metadata_by_category and not is_brand_mode:
                try:
                    # Parse JSON string if needed
                    if isinstance(cmd.metadata.get("data"), str):
                        metadata_list = json.loads(cmd.metadata.get("data", "[]"))
                    else:
                        metadata_list = cmd.metadata.get("data", [])

                    # Create lookup dict by sheet_name
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

            for category in categories:
                # Get metadata based on mode
                if is_brand_mode:
                    # Brand mode: lookup by category_id
                    category_metadata = metadata_by_category.get(category.id, {})
                else:
                    # Normal mode: lookup by sheet_name
                    category_metadata = metadata_by_sheet.get(sheet_name, {})

                profile = self._create_profile(
                    category=category,
                    sheet_name=sheet_name,
                    category_metadata=category_metadata,
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
        category_metadata: Dict[str, Optional[str]],
        global_business: Optional[str],
        is_brand_mode: bool,
    ) -> CategoryProfile:
        """
        Create profile with constraints based on category type and mode:

        Priority order:
        1. If global_business is set -> apply to all profiles
        2. If is_brand_mode is True -> use category.brand (from sheet name)
           AND apply brand business policy to set allowed businesses
        3. Use LLM metadata (direccion -> direction, genero -> gender)
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

        # Apply LLM metadata if available
        if category_metadata:
            genero = category_metadata.get("genero")
            direccion_meta = category_metadata.get("direccion")

            # Filter out "Nulo" values
            gender = genero if genero and genero.lower() != "nulo" else None
            direccion = direccion_meta if direccion_meta and direccion_meta.lower() != "nulo" else None

            if gender or direccion:
                print(f"  ✓ Metadata applied: {category.id} -> gender={gender}, direccion={direccion}")

        # Create constraints with all fields
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
