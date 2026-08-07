"""RAG ingestion and search endpoints.

``POST /api/v1/rag/index`` chunks and embeds documents (guidelines, historical
review comments) into the vector store. ``POST /api/v1/rag/search`` returns
top-k chunks for a query, optionally scoped to a source type and repository.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..deps import RagDep

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


class DocumentIn(BaseModel):
    source_type: str = Field(description="guideline | comment | commit")
    path: str
    content: str
    repo: str | None = None


class IndexIn(BaseModel):
    documents: list[DocumentIn]


class SearchIn(BaseModel):
    query: str
    k: int = Field(default=5, ge=1, le=20)
    source_type: str | None = None
    repo: str | None = None


@router.post("/index")
def index(body: IndexIn, rag: RagDep) -> dict:
    indexed = rag.index_documents(
        [document.model_dump() for document in body.documents]
    )
    return {"indexed_chunks": indexed, "total": rag.count()}


@router.post("/search")
def search(body: SearchIn, rag: RagDep) -> dict:
    hits = rag.search(
        body.query, k=body.k, source_type=body.source_type, repo=body.repo
    )
    return {
        "results": [
            {
                "doc_id": hit.doc_id,
                "score": round(hit.score, 4),
                "source_type": hit.metadata.get("source_type"),
                "path": hit.metadata.get("path"),
                "repo": hit.metadata.get("repo"),
                "content": hit.metadata.get("content"),
            }
            for hit in hits
        ]
    }
