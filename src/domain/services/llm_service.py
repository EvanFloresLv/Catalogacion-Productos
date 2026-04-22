# -----------------------------------------------------------------
# Domain Service — LLM (Port)
# -----------------------------------------------------------------
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class LLMService(ABC):
    """Port for Large Language Model interactions."""

    @abstractmethod
    def chat(
        self,
        messages: Any,
        schema: Optional[Dict] = None,
        mime_type: Optional[str] = None,
    ) -> str:
        raise NotImplementedError
