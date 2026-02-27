# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------
import time
from typing import Optional

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------


class CircuitBreaker:

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.opened_at: Optional[float] = None


    def record_success(self) -> None:
        self.failure_count = 0
        self.opened_at = None


    def record_failure(self) -> None:
        self.failure_count += 1

        if self.failure_count >= self.failure_threshold:
            self.opened_at = time.monotonic()


    def is_open(self) -> bool:

        if self.opened_at is not None:
            elapsed = time.monotonic() - self.opened_at
            if elapsed >= self.reset_timeout:
                self.failure_count = 0
                self.opened_at = None
                return False

        return self.failure_count >= self.failure_threshold