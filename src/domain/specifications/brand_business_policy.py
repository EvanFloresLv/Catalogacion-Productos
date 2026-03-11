# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from typing import Set

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------


class BrandBusinessPolicy:
    """
    Business policy for brand exclusions by business type.

    Defines which brands are excluded from certain business operations.
    All brand comparisons are case-insensitive.

    Business channels:
    - Suburbia: ~80 excluded brands (premium athletic, designer, fashion)
    - Liverpool: ~25 excluded brands (luxury, designer, specialty retail)
    """

    # Brands excluded from Suburbia (stored in uppercase for consistency)
    SUBURBIA_EXCLUDED_BRANDS: Set[str] = {
        "ADIDAS",
        "ADIDAS GOLF",
        "ADIDAS ORIGINALS",
        "ADIDAS PADEL",
        "ALMA EN PENA",
        "AMERICAN EAGLE",
        "BARI SWIMWEAR",
        "BEATRIZ MEADE",
        "CALVIN KLEIN",
        "CALVIN KLEIN JEANS",
        "CALVIN KLEIN HOME",
        "CALVIN",
        "CAMPER",
        "CLOE",
        "CLOE AGATHA",
        "CLOE CARE",
        "DANTE",
        "DKNY",
        "EASY SPIRIT",
        "FOKUS NAVY",
        "G BY GUESS",
        "GIOSEPPO",
        "GUESS",
        "GUESS JEANS",
        "HOT POTATOES",
        "HUGO BOSS",
        "HUSH PUPPIES",
        "H PUPPIES",
        "JOHN LEOPARD",
        "KALTEX HOME",
        "KASVU",
        "KEDS",
        "KURJENPOLVI",
        "LACOSTE",
        "MARIMEKKO",
        "MARIMEKKO KURJENPOLVI",
        "MURU",
        "NATURALIZER",
        "NINE WEST",
        "NIUH",
        "PIAGUI",
        "PITAS",
        "RITVA",
        "ROCKPORT",
        "RUUTU UNIKKO",
        "SCAPPINO",
        "SILVER BIRCH",
        "SITRUUNAPUU",
        "SONAATTI",
        "SPERRY",
        "SPEEDO",
        "TIARA",
        "TIMBERLAND",
        "TOMMY HILFIGER",
        "TOMMY JEANS",
        "TOMMY",
        "TOMMY GIRL",
        "UNIKKO TRUE BLUE",
        "VERA WANG",
        "VUORILAAKSO",
        "W-GIRLS",
        "CK",
        "CK JEANS",
        "CK SUITS",
        "SALOMON",
        "PRADA",
        "AY GÜEY",
        "LLENA ERES DE GRACIA",
        "MONASTERY COUTURE",
        "ALTURA SIETE",
        "KATE SPADE",
        "REGINA ROMERO",
    }

    # Brands excluded from Liverpool (stored in uppercase for consistency)
    LIVERPOOL_EXCLUDED_BRANDS: Set[str] = {
        "CLAIRES",
        "SCALPERS",
        "BIMBA Y LOLA",
        "COACH",
        "COACH NY",
        "TUDOR",
        "CHANEL",
        "HERMES",
        "LONGCHAMP",
        "THE ORDINARY",
        "BANANA REPUBLIC",
        "GAP",
        "AEROPOSTALE",
        "ETAM",
        "PUNT ROMA",
        "MARC JACOBS",
        "MICHAEL KORS",
        "SOL DE JANEIRO",
        "GUCCI",
        "GIVENCHY",
        "CAROLINA HERRERA",
        "FILORGA",
        "CONVERSE",
        "CAT & JACK",
    }

    @classmethod
    def is_brand_excluded_from_business(cls, brand: str | None, business: str) -> bool:
        """
        Check if a brand is excluded from a specific business.

        Args:
            brand: Brand name to check (case-insensitive)
            business: Business type (e.g., "suburbia", "liverpool")

        Returns:
            bool: True if the brand is excluded from the business

        Examples:
            >>> BrandBusinessPolicy.is_brand_excluded_from_business("adidas", "suburbia")
            True
            >>> BrandBusinessPolicy.is_brand_excluded_from_business("COACH", "liverpool")
            True
            >>> BrandBusinessPolicy.is_brand_excluded_from_business("nike", "suburbia")
            False
        """
        if not brand:
            return False

        brand_normalized = brand.strip().upper()
        business_normalized = business.strip().lower()

        if business_normalized == "suburbia":
            return brand_normalized in cls.SUBURBIA_EXCLUDED_BRANDS

        elif business_normalized == "liverpool":
            return brand_normalized in cls.LIVERPOOL_EXCLUDED_BRANDS

        return False

    @classmethod
    def get_excluded_brands_for_business(cls, business: str) -> Set[str]:
        """
        Get all brands excluded for a specific business.

        Args:
            business: Business type

        Returns:
            Set[str]: Set of excluded brand names (uppercase)

        Examples:
            >>> brands = BrandBusinessPolicy.get_excluded_brands_for_business("suburbia")
            >>> len(brands) > 0
            True
            >>> "ADIDAS" in brands
            True
        """
        business_normalized = business.strip().lower()

        if business_normalized == "suburbia":
            return cls.SUBURBIA_EXCLUDED_BRANDS.copy()

        elif business_normalized == "liverpool":
            return cls.LIVERPOOL_EXCLUDED_BRANDS.copy()

        return set()

    @classmethod
    def get_allowed_businesses_for_brand(cls, brand: str) -> Set[str]:
        """
        Get all businesses where a brand is allowed (not excluded).

        Args:
            brand: Brand name (case-insensitive)

        Returns:
            Set[str]: Set of business types where brand is allowed

        Examples:
            >>> allowed = BrandBusinessPolicy.get_allowed_businesses_for_brand("ADIDAS")
            >>> "suburbia" not in allowed
            True
            >>> "liverpool" in allowed
            True
        """
        if not brand:
            return {"suburbia", "liverpool"}

        brand_normalized = brand.strip().upper()
        all_businesses = {"suburbia", "liverpool"}
        excluded_from = set()

        if brand_normalized in cls.SUBURBIA_EXCLUDED_BRANDS:
            excluded_from.add("suburbia")

        if brand_normalized in cls.LIVERPOOL_EXCLUDED_BRANDS:
            excluded_from.add("liverpool")

        return all_businesses - excluded_from
