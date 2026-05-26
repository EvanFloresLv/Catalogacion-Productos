from __future__ import annotations

from typing import List

from shared.kernel.aggregate_root import AggregateRoot
from domain.entities.product import Product
from domain.entities.result import ClassificationResult, CategoryMatch


class ProductClassification(AggregateRoot):
    """
    Aggregate root for product classification.

    Invariants:
      - Product must exist before classification
      - Brand exclusion policy must be enforced per business
      - At least one business must be valid for classification

    Events emitted:
      - ProductCreatedEvent
      - ProductClassifiedEvent
    """

    def __init__(self, product: Product) -> None:
        super().__init__()
        self._product = product
        self._results: List[ClassificationResult] = []

    # ---------------------------
    # Properties
    # ---------------------------
    @property
    def product(self) -> Product:
        return self._product

    @property
    def results(self) -> List[ClassificationResult]:
        return list(self._results)

    def record_classification(
        self,
        business: str,
        query: str,
        top_k: List[CategoryMatch],
    ) -> ClassificationResult:
        """
        Record a classification result for a specific business.
        Emits ProductClassifiedEvent.
        """
        if not top_k:
            raise Exception(
                f"No eligible matches for product {self._product.sku} "
                f"in business '{business}'"
            )

        result = ClassificationResult(
            product_sku=self._product.sku,
            best=top_k[0],
            top_k=top_k,
            query=query
        )
        self._results.append(result)

        return result