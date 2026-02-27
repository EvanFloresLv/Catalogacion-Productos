# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------
from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
import nltk

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------

nltk.download("stopwords", quiet=True)

SPANISH_STOPWORDS = set(nltk.corpus.stopwords.words("spanish"))

def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    tokens = text.split()
    tokens = [t for t in tokens if t not in SPANISH_STOPWORDS]
    tokens.sort()
    return " ".join(tokens)


@dataclass(frozen=True, slots=True)
class SemanticHash:
    value: str

    @classmethod
    def from_text(cls, text: str) -> SemanticHash:
        normalized = normalize_text(text)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return cls(digest)