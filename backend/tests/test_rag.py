"""Phase 4 RAG tests: chunking, embeddings, vector store, and retrieval."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.config import get_settings
from app.domain.events import CommitRef, RepositoryInfo
from app.domain.models import ReviewRun
from app.orchestration.orchestrator import ReviewOrchestrator
from app.orchestration.prompts import build_core_messages, build_security_messages
from app.persistence.memory import InMemoryRunRepository
from app.rag import chunk_source, chunk_text
from app.rag.embeddings import FeatureHashEmbedder
from app.rag.service import RagService
from app.rag.vector_store import InMemoryVectorStore
from app.services.event_bus import EventBus
from app.services.llm_gateway import LLMResponse

from .helpers import diff_clean, post_event, wait_for

# -- chunking -------------------------------------------------------------


def test_chunk_python_source_splits_on_function_boundaries() -> None:
    source = (
        "import os\n\ndef helper():\n    return 1\n\ndef main():\n    return helper()\n"
    )
    chunks = [c.text for c in chunk_source(source, "app.py")]
    assert len(chunks) == 2
    assert chunks[0].startswith("def helper")
    assert chunks[1].startswith("def main")


def test_chunk_plain_fallback_respects_max_chars() -> None:
    text = "a" * 100 + " " + "b" * 100
    chunks = chunk_text(text, max_chars=80, overlap=20)
    assert len(chunks) >= 2
    assert all(len(c.text) <= 80 for c in chunks)


def test_chunk_empty_source_returns_no_chunks() -> None:
    assert chunk_source("", "app.py") == []


# -- embeddings -----------------------------------------------------------


def test_embedder_is_deterministic_and_normalized() -> None:
    embedder = FeatureHashEmbedder(dim=64)
    first = embedder.embed("parameterized queries prevent sql injection")
    second = embedder.embed("parameterized queries prevent sql injection")
    assert first == second
    assert abs(sum(v * v for v in first) - 1.0) < 1e-6


def test_embedder_similarity_ranks_shared_tokens() -> None:
    embedder = FeatureHashEmbedder(dim=256)
    base = embedder.embed("sql injection parameterized queries")
    similar = embedder.embed("prevent sql injection with parameterized queries")
    unrelated = embedder.embed("frontend dashboard color palette")

    def cosine(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    assert cosine(base, similar) > cosine(base, unrelated)


# -- vector store ---------------------------------------------------------


def test_vector_store_search_is_scoped_by_metadata() -> None:
    store = InMemoryVectorStore()
    embedder = FeatureHashEmbedder(dim=64)
    store.add(
        "a", embedder.embed("sql injection"), {"repo": "r1", "source_type": "guideline"}
    )
    store.add(
        "b", embedder.embed("sql injection"), {"repo": "r2", "source_type": "guideline"}
    )

    hits = store.search(embedder.embed("sql injection"), k=5, where={"repo": "r1"})
    assert [h.doc_id for h in hits] == ["a"]


def test_vector_store_reindexing_replaces_same_doc_id() -> None:
    store = InMemoryVectorStore()
    store.add("x", [1.0], {"content": "first"})
    store.add("x", [1.0], {"content": "second"})
    assert store.count() == 1


# -- service roundtrip ----------------------------------------------------


def test_rag_service_index_and_search_roundtrip() -> None:
    service = RagService(InMemoryVectorStore(), FeatureHashEmbedder(dim=128))
    count = service.index_document(
        source_type="guideline",
        path="security.md",
        content="sql injection: always use parameterized queries",
        repo="acme",
    )
    assert count == 1

    hits = service.search("parameterized sql queries", k=3, repo="acme")
    assert hits and hits[0].metadata["path"] == "security.md"

    # Repository scoping never leaks across boundaries.
    assert service.search("parameterized sql queries", k=3, repo="other") == []


# -- API ------------------------------------------------------------------


def test_rag_index_and_search_api(client: TestClient) -> None:
    document = {
        "source_type": "guideline",
        "path": "g.md",
        "content": "secrets must never be committed; load them from environment",
        "repo": "demo",
    }
    indexed = client.post("/api/v1/rag/index", json={"documents": [document]})
    assert indexed.status_code == 200
    assert indexed.json()["indexed_chunks"] >= 1

    searched = client.post(
        "/api/v1/rag/search",
        json={"query": "commit an api key to source code", "k": 3, "repo": "demo"},
    )
    assert searched.status_code == 200
    results = searched.json()["results"]
    assert results
    assert results[0]["path"] == "g.md"


def test_seeded_guidelines_are_searchable(client: TestClient) -> None:
    """create_app() indexes data/guidelines/*.md at startup."""
    response = client.post(
        "/api/v1/rag/search",
        json={"query": "eval untrusted input", "k": 3, "source_type": "guideline"},
    )
    assert response.status_code == 200
    paths = {result["path"] for result in response.json()["results"]}
    assert "security.md" in paths


# -- prompts + orchestrator wiring ---------------------------------------


def _make_run() -> ReviewRun:
    return ReviewRun(
        id="r-rag",
        provider="local_git",
        repository=RepositoryInfo(name="demo", path="/tmp/demo"),
        commit=CommitRef(
            sha="c" * 40, base_sha="d" * 40, files=["app.py"], diff="diff"
        ),
    )


def test_core_messages_include_rag_context() -> None:
    messages = build_core_messages(
        _make_run(),
        ["app.py"],
        rag_context="[guideline] security.md: use parameterized queries",
    )
    assert "Retrieved guidance" in messages[-1]["content"]
    assert "parameterized queries" in messages[-1]["content"]


def test_messages_unchanged_without_rag_context() -> None:
    assert (
        "Retrieved guidance"
        not in build_core_messages(_make_run(), ["app.py"])[-1]["content"]
    )
    assert (
        "Retrieved guidance"
        not in build_security_messages(_make_run(), ["app.py"])[-1]["content"]
    )


class RecordingGateway:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> LLMResponse:
        self.calls.append(messages)
        if "triage" in model:
            content = '{"core": ["app.py"], "security": ["app.py"]}'
        elif "gemini" in model:
            content = '{"summary": "ok"}'
        else:
            content = '{"findings": []}'
        return LLMResponse(content=content, model=model, latency_ms=1)


def test_orchestrator_injects_rag_context_into_agent_prompts() -> None:
    repo = InMemoryRunRepository()
    bus = EventBus()
    rag = RagService(InMemoryVectorStore(), FeatureHashEmbedder(dim=64))
    rag.index_document(
        source_type="guideline",
        path="security.md",
        content="never pass untrusted input to eval()",
        repo="demo",
    )
    gateway = RecordingGateway()
    run = _make_run()
    repo.create_run(run)

    orchestrator = ReviewOrchestrator(
        repo=repo, bus=bus, gateway=gateway, settings=get_settings(), rag=rag
    )
    asyncio.run(orchestrator.run_review(run.id))

    persisted = repo.get_run(run.id)
    assert persisted is not None
    assert persisted.status.value == "succeeded"
    # call order: triage, core, security, summarizer
    core_messages = gateway.calls[1]
    security_messages = gateway.calls[2]
    assert "Retrieved guidance" in core_messages[-1]["content"]
    assert "Retrieved guidance" in security_messages[-1]["content"]


def test_full_review_with_rag_wiring(client: TestClient) -> None:
    """The end-to-end demo path still completes with RAG active."""
    run_id = post_event(client, diff=diff_clean())
    run = wait_for(client, run_id, {"succeeded", "failed"})
    assert run["status"] == "succeeded"
