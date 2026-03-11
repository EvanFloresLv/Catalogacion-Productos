#!/usr/bin/env python3
"""
Example script demonstrating brand business policy usage.

This shows how to check if specific brands are allowed in different businesses.
"""

from domain.specifications.brand_business_policy import BrandBusinessPolicy
from application.use_cases.products.validate_product_business import (
    ValidateProductBusinessCommand,
    ValidateProductBusinessUseCase
)


def main():
    print("=" * 80)
    print("BRAND BUSINESS POLICY - EXAMPLES")
    print("=" * 80)
    print()

    # Example 1: Check if specific brands are excluded from Suburbia
    print("1. Checking brand exclusions from Suburbia:")
    print("-" * 80)

    brands_to_check = ["ADIDAS", "CALVIN KLEIN", "NIKE", "ZARA", "H&M"]

    for brand in brands_to_check:
        is_excluded = BrandBusinessPolicy.is_brand_excluded_from_business(
            brand=brand,
            business="suburbia"
        )
        status = "❌ EXCLUDED" if is_excluded else "✅ ALLOWED"
        print(f"  {status}: {brand}")

    print()

    # Example 2: Check if specific brands are excluded from Liverpool
    print("2. Checking brand exclusions from Liverpool:")
    print("-" * 80)

    brands_to_check = ["COACH", "CHANEL", "GUCCI", "NIKE", "ZARA"]

    for brand in brands_to_check:
        is_excluded = BrandBusinessPolicy.is_brand_excluded_from_business(
            brand=brand,
            business="liverpool"
        )
        status = "❌ EXCLUDED" if is_excluded else "✅ ALLOWED"
        print(f"  {status}: {brand}")

    print()

    # Example 3: Get all excluded brands for both businesses
    print("3. All brands excluded by business:")
    print("-" * 80)

    suburbia_excluded = BrandBusinessPolicy.get_excluded_brands_for_business("suburbia")
    print(f"  Suburbia - Total: {len(suburbia_excluded)}")
    print(f"  Sample: {', '.join(list(suburbia_excluded)[:5])}...")

    print()

    liverpool_excluded = BrandBusinessPolicy.get_excluded_brands_for_business("liverpool")
    print(f"  Liverpool - Total: {len(liverpool_excluded)}")
    print(f"  Sample: {', '.join(list(liverpool_excluded)[:5])}...")

    print()

    # Example 4: Get allowed businesses for a brand
    print("4. Where can different brands be sold?")
    print("-" * 80)

    test_brands = ["ADIDAS", "COACH", "NIKE"]

    for brand in test_brands:
        allowed_businesses = BrandBusinessPolicy.get_allowed_businesses_for_brand(brand)
        print(f"  {brand}: {', '.join(sorted(allowed_businesses))}")

    print()

    # Example 5: Using the use case
    print("5. Using ValidateProductBusinessUseCase:")
    print("-" * 80)

    use_case = ValidateProductBusinessUseCase()

    test_cases = [
        ("ADIDAS", "suburbia"),
        ("ADIDAS", "liverpool"),
        ("COACH", "suburbia"),
        ("COACH", "liverpool"),
        ("NIKE", "suburbia"),
        ("CHANEL", "liverpool"),
    ]

    for brand, business in test_cases:
        cmd = ValidateProductBusinessCommand(brand=brand, business=business)
        is_allowed = use_case.execute(cmd)
        reason = use_case.get_reason(cmd)

        status = "✅ ALLOWED" if is_allowed else "❌ EXCLUDED"
        print(f"  {status}: {brand} in {business}")
        print(f"    Reason: {reason}")
        print()


if __name__ == "__main__":
    main()
