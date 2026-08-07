"""Vector store interface and an in-memory implementation.

``InMemoryVectorStore`` keeps every chunk (embedding + metadata) in RAM and
answers top-k cosine-similarity queries. Repository/source-type metadata stays
attached to each chunk so retrieval can be scoped and never leaks across
repositories. Production would swap this for pgvector behind the same methods.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class StoredDoc:
    doc_id: str
    vector: list[float]
    metadata: dict[str, Any]


@dataclass
class SearchHit:
    doc_id: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStore(Protocol):
    def add(
        self, doc_id: str, vector: list[float], metadata: dict[str, Any]
    ) -> None: ...

    def search(
        self, vector: list[float], k: int, where: dict[str, Any] | None = None
    ) -> list[SearchHit]: ...

    def clear(self) -> None: ...

    def count(self) -> int: ...


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (norm_a * norm_b)


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._docs: dict[str, StoredDoc] = {}

    def add(self, doc_id: str, vector: list[float], metadata: dict[str, Any]) -> None:
        # Same doc_id re-added -> replaced (idempotent re-indexing).
        self._docs[doc_id] = StoredDoc(doc_id=doc_id, vector=vector, metadata=metadata)

    def clear(self) -> None:
        self._docs.clear()

    def count(self) -> int:
        return len(self._docs)

    def search(
        self, vector: list[float], k: int, where: dict[str, Any] | None = None
    ) -> list[SearchHit]:
        hits: list[SearchHit] = []
        for doc in self._docs.values():
            if where is not None and any(
                doc.metadata.get(key) != value for key, value in where.items()
            ):
                continue
            hits.append(
                SearchHit(
                    doc_id=doc.doc_id,
                    score=_cosine(vector, doc.vector),
                    metadata=dict(doc.metadata),
                )
            )
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:k]
