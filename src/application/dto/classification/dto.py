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
    # When set, only products whose top1 cosine is below this threshold
    # are sent to the LLM re-ranker. ``None`` falls back to the
    # ``classification_settings.enhance_threshold`` default.
    enhance_threshold: float | None = None
    # When set, per-business results whose final top1 cosine is below
    # this value are reported as ``None``. ``None`` falls back to
    # ``classification_settings.min_confidence`` (default 0.55).
    min_confidence: float | None = None


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