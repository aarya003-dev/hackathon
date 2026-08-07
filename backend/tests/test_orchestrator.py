"""Phase 3 orchestration tests driven by the deterministic DemoGateway."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.config import get_settings
from app.domain.events import CommitRef, RepositoryInfo
from app.domain.models import ReviewRun, RunStatus
from app.integrations.publisher import DryRunPublisher
from app.orchestration.orchestrator import ReviewOrchestrator
from app.persistence.memory import InMemoryRunRepository
from app.services.event_bus import EventBus
from app.services.llm_gateway import LLMResponse

from .helpers import (
    diff_clean,
    diff_with_security,
    post_event,
    push_event,
    wait_for,
)


class FailingGateway:
    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> LLMResponse:
        raise RuntimeError("gateway down")


class MalformedGateway:
    """Returns content that is not valid JSON."""

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> LLMResponse:
        return LLMResponse(content="this is not json", model=model, latency_ms=1)


def _make_run() -> ReviewRun:
    return ReviewRun(
        id="r-orch",
        provider="local_git",
        repository=RepositoryInfo(name="r", path="/tmp/r"),
        commit=CommitRef(
            sha="b" * 40, base_sha="a" * 40, files=["app.py"], diff="diff"
        ),
    )


def test_full_review_success_with_hitl_approve(client: TestClient) -> None:
    run_id = post_event(client, diff=diff_with_security())

    run = wait_for(client, run_id, {"waiting_hitl"})
    assert run["nodes"]["security"] == "paused"
    assert run["hitl_pending"] > 0
    approvals = run["approvals"]
    assert approvals

    for approval in approvals:
        response = client.post(
            f"/api/v1/hitl/{approval['id']}/decision",
            json={"decision": "approve", "by": "lead"},
        )
        assert response.status_code == 200, response.text

    run = wait_for(client, run_id, {"succeeded", "failed"})
    assert run["status"] == "succeeded"
    assert run["nodes"]["triage"] == "success"
    assert run["nodes"]["core_review"] == "success"
    assert run["nodes"]["security"] == "success"
    assert run["nodes"]["summarizer"] == "success"
    assert run["summary"]
    assert run["hitl_pending"] == 0

    severities = {finding["severity"] for finding in run["findings"]}
    assert "critical" in severities
    assert any(finding["requires_hitl"] for finding in run["findings"])


def test_hitl_reject_drops_finding(client: TestClient) -> None:
    run_id = post_event(client, diff=diff_with_security())

    run = wait_for(client, run_id, {"waiting_hitl"})
    for approval in run["approvals"]:
        response = client.post(
            f"/api/v1/hitl/{approval['id']}/decision",
            json={"decision": "reject", "by": "lead"},
        )
        assert response.status_code == 200, response.text

    run = wait_for(client, run_id, {"succeeded", "failed"})
    assert run["status"] == "succeeded"
    # The rejected critical finding must not appear in the final result.
    assert not any(finding["requires_hitl"] for finding in run["findings"])


def test_clean_diff_completes_without_hitl(client: TestClient) -> None:
    run_id = post_event(client, diff=diff_clean())
    run = wait_for(client, run_id, {"succeeded", "failed"})
    assert run["status"] == "succeeded"
    assert run["hitl_pending"] == 0
    assert run["findings"] == []


def test_ingest_is_idempotent_by_commit(client: TestClient) -> None:
    event = push_event(diff=diff_clean())
    first = client.post(
        "/api/v1/ingest/git",
        json=event,
        headers={"X-Ingest-Secret": "dev-secret"},
    )
    assert first.status_code == 202
    second = client.post(
        "/api/v1/ingest/git",
        json=event,
        headers={"X-Ingest-Secret": "dev-secret"},
    )
    assert second.status_code == 202
    assert second.json()["duplicate"] is True
    assert second.json()["run_id"] == first.json()["run_id"]


def test_run_fails_when_gateway_errors() -> None:
    repo = InMemoryRunRepository()
    bus = EventBus()
    run = _make_run()
    repo.create_run(run)

    orchestrator = ReviewOrchestrator(
        repo=repo, bus=bus, gateway=FailingGateway(), settings=get_settings()
    )
    asyncio.run(orchestrator.run_review(run.id))

    persisted = repo.get_run(run.id)
    assert persisted is not None
    assert persisted.status == RunStatus.failed
    assert persisted.error is not None
    assert "gateway down" in persisted.error


def test_run_fails_on_malformed_gateway_json() -> None:
    """Gateway response validation: invalid JSON fails the run, not the server."""
    repo = InMemoryRunRepository()
    bus = EventBus()
    run = _make_run()
    repo.create_run(run)

    orchestrator = ReviewOrchestrator(
        repo=repo, bus=bus, gateway=MalformedGateway(), settings=get_settings()
    )
    asyncio.run(orchestrator.run_review(run.id))

    persisted = repo.get_run(run.id)
    assert persisted is not None
    assert persisted.status == RunStatus.failed
    assert persisted.error is not None and persisted.error.strip() != ""


def test_dry_run_publisher_records_comments() -> None:
    from app.domain.models import AgentKind, Finding, Severity

    publisher = DryRunPublisher(target="dry-run://demo-repo")
    run = _make_run()
    run.findings = [
        Finding(
            id="f1",
            agent=AgentKind.security,
            severity=Severity.critical,
            category="injection",
            file_path="app.py",
            line_start=3,
            message="eval on untrusted input",
            suggestion="remove eval",
        )
    ]
    metadata = publisher.publish(run)

    assert metadata == {
        "provider": "dry_run",
        "target": "dry-run://demo-repo",
        "status": "published",
        "posted": 1,
    }
    assert publisher.comments[0]["file_path"] == "app.py"
    assert publisher.comments[0]["severity"] == "critical"


def test_completed_run_records_dry_run_publication() -> None:
    class EmptyGateway:
        async def chat(
            self,
            model: str,
            messages: list[dict[str, str]],
            *,
            temperature: float = 0.2,
        ) -> LLMResponse:
            if "triage" in model:
                content = '{"core": ["app.py"], "security": ["app.py"]}'
            elif "gemini" in model:
                content = '{"summary": "ok"}'
            else:
                content = '{"findings": []}'
            return LLMResponse(content=content, model=model, latency_ms=1)

    repo = InMemoryRunRepository()
    bus = EventBus()
    run = _make_run()
    repo.create_run(run)

    orchestrator = ReviewOrchestrator(
        repo=repo,
        bus=bus,
        gateway=EmptyGateway(),
        settings=get_settings(),
        publisher=DryRunPublisher(),
    )
    asyncio.run(orchestrator.run_review(run.id))

    persisted = repo.get_run(run.id)
    assert persisted is not None
    assert persisted.status == RunStatus.succeeded
    assert persisted.publication is not None
    assert persisted.publication["status"] == "published"
    assert persisted.publication["posted"] == 0
