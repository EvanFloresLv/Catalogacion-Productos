# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from abc import ABC, abstractmethod

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------


class EmbeddingService(ABC):

    @abstractmethod
    def embed_text(
        self,
        text: str
    ) -> list[float]:
        """Embeds a text into a vector space."""
        raise NotImplementedError