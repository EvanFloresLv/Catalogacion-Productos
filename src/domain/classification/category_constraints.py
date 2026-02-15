# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class CategoryConstraints:
    allowed_gender: set[str]
    allowed_business_types: set[str]