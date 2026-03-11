# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------
from domain.specifications.brand_business_policy import BrandBusinessPolicy


@dataclass(frozen=True)
class ValidateProductBusinessCommand:
    """Command to validate if a product can be sold in a business."""
    brand: str | None
    business: str


class ValidateProductBusinessUseCase:
    """
    Validates if a product brand is allowed in a specific business.

    Uses BrandBusinessPolicy to check brand exclusions.
    """

    def execute(self, cmd: ValidateProductBusinessCommand) -> bool:
        """
        Check if a product can be sold in the specified business.

        Args:
            cmd: Command with brand and business information

        Returns:
            bool: True if product is allowed, False if excluded
        """
        is_excluded = BrandBusinessPolicy.is_brand_excluded_from_business(
            brand=cmd.brand,
            business=cmd.business
        )

        return not is_excluded

    def get_reason(self, cmd: ValidateProductBusinessCommand) -> str:
        """
        Get the reason why a product is allowed or excluded.

        Args:
            cmd: Command with brand and business information

        Returns:
            str: Explanation of validation result
        """
        is_excluded = BrandBusinessPolicy.is_brand_excluded_from_business(
            brand=cmd.brand,
            business=cmd.business
        )

        if is_excluded:
            return f"Brand '{cmd.brand}' is excluded from business '{cmd.business}' by brand business policy"

        return f"Brand '{cmd.brand}' is allowed in business '{cmd.business}'"
