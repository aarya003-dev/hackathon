"""Embedding interface and a deterministic offline implementation.

``FeatureHashEmbedder`` is a hashing-vectorizer (like scikit-learn's
HashingVectorizer): a stable, normalized bag-of-tokens vector. It is
deterministic, credential-free, and gives meaningful cosine similarity for
guideline retrieval in the demo/tests. The real gateway embedding model
(``model_embeddings``) plugs into the same interface for production.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

_TOKEN = re.compile(r"[a-zA-Z0-9_]+")


class Embedder(Protocol):
    @property
    def dim(self) -> int:
        """Dimensionality of produced vectors."""

    def embed(self, text: str) -> list[float]:
        """Return a normalized vector for ``text``."""


class FeatureHashEmbedder:
    def __init__(self, dim: int = 256) -> None:
        if dim < 8:
            raise ValueError("embedding dimension must be >= 8")
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dim
        for token in _TOKEN.findall(text.lower()):
            digest = hashlib.md5(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self._dim
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
