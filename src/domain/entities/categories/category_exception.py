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


@dataclass(frozen=True)
class CategoryException:
    category_id: str
    reason: str


    @classmethod
    def from_exception(
        cls,
        category_id: str,
        exception: Exception
    ) -> CategoryException:

        if not category_id or not isinstance(category_id, str):
            raise TypeError("category_id must be a non-empty string")

        if not exception or not isinstance(exception, Exception):
            raise TypeError("exception must be a non-empty Exception instance")

        return cls(
            category_id=category_id,
            reason=str(exception),
        )