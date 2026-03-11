# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
from abc import ABC, abstractmethod
from typing import Any, Dict

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------


class PromptService(ABC):

    @abstractmethod
    def load_prompt(self) -> Dict[str, Any]:
        raise NotImplementedError


    @abstractmethod
    def get_prompt(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError