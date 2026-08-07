"""RagService: chunk -> embed -> store -> retrieve.

Guidelines, historical review comments, and commit diffs all flow through the
same pipeline. Every chunk carries ``source_type``, ``path``, and ``repo``
metadata so retrieval can be scoped to a repository and provenance is never
lost.
"""

from __future__ import annotations

from typing import Any

from .chunking import chunk_source
from .embeddings import Embedder
from .vector_store import InMemoryVectorStore, SearchHit


class RagService:
    def __init__(
        self,
        store: InMemoryVectorStore,
        embedder: Embedder,
        *,
        max_chars: int = 1500,
        overlap: int = 200,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._max_chars = max_chars
        self._overlap = overlap

    def index_document(
        self,
        *,
        source_type: str,
        path: str,
        content: str,
        repo: str | None = None,
    ) -> int:
        """Chunk and index one document; returns the number of chunks stored."""
        chunks = chunk_source(
            content, path, max_chars=self._max_chars, overlap=self._overlap
        )
        for chunk in chunks:
            doc_id = f"{source_type}:{path}:{chunk.index}"
            self._store.add(
                doc_id,
                self._embedder.embed(chunk.text),
                {
                    "source_type": source_type,
                    "path": path,
                    "repo": repo,
                    "chunk_index": chunk.index,
                    "content": chunk.text,
                },
            )
        return len(chunks)

    def index_documents(self, documents: list[dict[str, Any]]) -> int:
        return sum(self.index_document(**document) for document in documents)

    def search(
        self,
        query: str,
        *,
        k: int = 5,
        source_type: str | None = None,
        repo: str | None = None,
    ) -> list[SearchHit]:
        where: dict[str, Any] = {}
        if source_type is not None:
            where["source_type"] = source_type
        if repo is not None:
            where["repo"] = repo
        return self._store.search(self._embedder.embed(query), k=k, where=where or None)

    def count(self) -> int:
        return self._store.count()
