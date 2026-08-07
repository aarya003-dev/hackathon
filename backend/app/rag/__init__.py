"""RAG pipeline: chunking, embeddings, vector storage, and retrieval.

The vector store and embedder are kept behind small interfaces so the local
development/demo slice (in-memory store + deterministic feature-hash embedder)
can be swapped for a production vector DB (pgvector) and the real embedding
gateway without touching the agents or API routes.
"""

from .chunking import Chunk, chunk_source, chunk_text
from .embeddings import Embedder, FeatureHashEmbedder
from .service import RagService
from .vector_store import InMemoryVectorStore, SearchHit

__all__ = [
    "Chunk",
    "Embedder",
    "FeatureHashEmbedder",
    "InMemoryVectorStore",
    "RagService",
    "SearchHit",
    "chunk_source",
    "chunk_text",
]
