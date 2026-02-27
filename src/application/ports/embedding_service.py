# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from abc import ABC, abstractmethod
from typing import List, Sequence

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------


class EmbeddingService(ABC):

    @abstractmethod
    def generate(self, text: str) -> List[float]:
        raise NotImplementedError


    @abstractmethod
    def generate_batch(self, texts: Sequence[str]) -> List[List[float]]:
        raise NotImplementedError