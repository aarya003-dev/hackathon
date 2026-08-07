"""Tests for run list/detail endpoints and the SSE event stream."""

from __future__ import annotations

from fastapi.testclient import TestClient

from .helpers import diff_clean, diff_with_security, post_event, wait_for


def test_list_and_detail(client: TestClient) -> None:
    run_id = post_event(client, diff=diff_clean())
    wait_for(client, run_id, {"succeeded"})

    listing = client.get("/api/v1/runs").json()
    assert any(
        item["id"] == run_id and item["status"] == "succeeded" for item in listing
    )

    detail = client.get(f"/api/v1/runs/{run_id}").json()
    assert detail["id"] == run_id
    assert detail["status"] == "succeeded"
    assert detail["summary"]
    assert set(detail["nodes"].keys()) == {
        "triage",
        "core_review",
        "security",
        "summarizer",
    }

    missing = client.get("/api/v1/runs/does-not-exist")
    assert missing.status_code == 404


def test_sse_stream_replays_completed_run(client: TestClient) -> None:
    run_id = post_event(client, diff=diff_clean())
    wait_for(client, run_id, {"succeeded"})

    with client.stream("GET", f"/api/v1/runs/{run_id}/events") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = "".join(response.iter_text())

    assert "event: run.queued" in body
    assert "event: run.started" in body
    assert "event: review.completed" in body
    assert body.count("event: agent.started") == 4


def test_hitl_decision_validation(client: TestClient) -> None:
    run_id = post_event(client, diff=diff_with_security())
    run = wait_for(client, run_id, {"waiting_hitl"})
    approval = run["approvals"][0]

    # Unknown approval id -> 404
    assert (
        client.post(
            "/api/v1/hitl/does-not-exist/decision",
            json={"decision": "approve", "by": "lead"},
        ).status_code
        == 404
    )

    # Invalid decision value -> 422
    assert (
        client.post(
            f"/api/v1/hitl/{approval['id']}/decision",
            json={"decision": "maybe", "by": "lead"},
        ).status_code
        == 422
    )

    # Happy path still works
    response = client.post(
        f"/api/v1/hitl/{approval['id']}/decision",
        json={"decision": "approve", "by": "lead"},
    )
    assert response.status_code == 200
    wait_for(client, run_id, {"succeeded"})
