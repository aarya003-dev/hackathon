"""Tests for the agents status endpoint."""

from __future__ import annotations

from . import helpers

AGENT_IDS = {"triage", "core_review", "security", "summarizer"}


def test_agents_empty(client) -> None:
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    body = response.json()
    agents = {item["id"]: item for item in body["agents"]}
    assert set(agents) == AGENT_IDS
    for agent in agents.values():
        assert agent["runs"] == 0
        assert agent["success_rate"] == 0.0
        assert agent["latest_status"] == "idle"
        assert agent["findings"] == 0
        assert agent["model"]
    assert body["config"]["llm_backend"] == "demo"
    assert body["config"]["ingestion_source"] == "local_git"
    assert body["config"]["models"]["gemini"]


def test_agents_reflect_runs_and_hitl(client) -> None:
    run_id = helpers.post_event(client, diff=helpers.diff_with_security())
    run = helpers.wait_for(client, run_id, {"waiting_hitl"})

    body = client.get("/api/v1/agents").json()
    agents = {item["id"]: item for item in body["agents"]}
    assert agents["triage"]["runs"] == 1
    assert agents["core_review"]["latest_status"] == "success"
    # The critical eval() finding paused the security agent at the HITL gate.
    assert agents["security"]["latest_status"] == "paused"
    assert agents["security"]["findings"] == 1
    assert agents["security"]["hitl"] == 1

    # Approve the pause; the run resumes and security ends successful.
    approval_id = run["approvals"][0]["id"]
    decision = client.post(
        f"/api/v1/hitl/{approval_id}/decision",
        json={"decision": "approve", "by": "tester"},
    )
    assert decision.status_code == 200
    helpers.wait_for(client, run_id, {"succeeded"})

    body = client.get("/api/v1/agents").json()
    agents = {item["id"]: item for item in body["agents"]}
    assert agents["security"]["latest_status"] == "success"
    assert agents["security"]["success_rate"] == 1.0
    assert agents["security"]["findings"] == 1
    assert agents["summarizer"]["latest_status"] == "success"
