from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Tuple

from utils.domain_validatons import validate_entity_fields


# -------------------------------------------------------------
# Domain constants
# -------------------------------------------------------------
BUSINESS: frozenset[str] = frozenset({
    "liverpool",
    "suburbia",
    "liverpool-blp",
    "suburbia-blp",
})


# -------------------------------------------------------------
# Entity (Value Object)
# -------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Brand:

    # Required
    name: str

    # Immutable + deterministic
    business: Tuple[str, ...] = field(default_factory=tuple)

    # ---------------------------------------------------------
    # Factory
    # ---------------------------------------------------------
    @classmethod
    def create(cls, **data: Any) -> Brand:

        validated = validate_entity_fields(
            cls,
            data,
            required_fields={"name", "business"},
        )

        business_values = validated.get("business", ())

        if isinstance(business_values, str):
            raise TypeError(
                "business must be an iterable (e.g. tuple/list), not str"
            )

        invalid = [b for b in business_values if b not in BUSINESS]
        if invalid:
            raise ValueError(f"Invalid business values: {invalid}")

        business_tuple = tuple(sorted(set(business_values)))

        return cls(
            name=validated["name"],
            business=business_tuple,
        )


# -------------------------------------------------------------
# Usage
# -------------------------------------------------------------
if __name__ == "__main__":

    brand = Brand.create(
        name="Adidas",
        business=("LIVERPOOL",)
    )

    print(brand)