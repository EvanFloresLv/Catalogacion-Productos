# -----------------------------------------------------------------
# Application DTO — Commands — Product
# -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class LoadProductsCommand:
    """Command to create one or more products."""
    products: List[Dict[str, Any]]
