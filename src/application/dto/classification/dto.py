# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from dataclasses import dataclass
from domain.entities.result import ClassificationResult

ClassificationMap = dict[str, dict[str, ClassificationResult | None]]
FailureMap = dict[str, str]


@dataclass(frozen=True)
class ClassifyBatchProductsCommand:
    product_skus: tuple[str, ...]
    top_k: int = 5
    enhance: bool = True


@dataclass(frozen=True)
class BatchClassificationResult:
    results: ClassificationMap
    failed: FailureMap

    @property
    def succeeded_count(self) -> int:
        return len(self.results)

    @property
    def failed_count(self) -> int:
        return len(self.failed)

    @property
    def total(self) -> int:
        return self.succeeded_count + self.failed_count