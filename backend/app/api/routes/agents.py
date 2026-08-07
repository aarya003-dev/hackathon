"""Agent status endpoint.

``GET /api/v1/agents`` aggregates the persisted runs into per-agent health
(turns entered, success rate, latest node status, findings produced) plus a
read-only snapshot of the gateway configuration. It powers the dashboard's
Agents page without exposing credentials or live model state.
"""

from __future__ import annotations

from fastapi import APIRouter

from ...config import Settings
from ...domain.models import AgentKind, NodeStatus
from ..deps import RepoDep, SettingsDep

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

AGENT_INFO: dict[AgentKind, tuple[str, str]] = {
    AgentKind.triage: ("Triage", "Routes changed files to the review agents."),
    AgentKind.core: ("Core review", "Analyzes code quality, correctness, and style."),
    AgentKind.security: ("Security", "Scans for vulnerabilities and sensitive data."),
    AgentKind.summarizer: ("Summarizer", "Synthesizes findings into a review summary."),
}

_MODEL_FOR_KIND: dict[AgentKind, str] = {
    AgentKind.triage: "model_triage",
    AgentKind.core: "model_core_review",
    AgentKind.security: "model_security",
    AgentKind.summarizer: "model_summarizer",
}


def _effective_model(kind: AgentKind, settings: Settings) -> str:
    # The Gemini backend routes every agent through the single Gemini model;
    # the per-kind GenAI Lab model names only apply to the http backend.
    if settings.llm_backend == "gemini":
        return settings.model_gemini
    return getattr(settings, _MODEL_FOR_KIND[kind])


def _agent_stats(kind: AgentKind, settings: Settings, runs) -> dict:
    name, role = AGENT_INFO[kind]
    entered = [
        run for run in runs if run.nodes.get(kind, NodeStatus.idle) != NodeStatus.idle
    ]
    successes = sum(1 for run in entered if run.nodes.get(kind) == NodeStatus.success)
    failures = sum(1 for run in entered if run.nodes.get(kind) == NodeStatus.failed)
    latest = max(entered, key=lambda run: run.updated_at, default=None)
    findings = sum(
        1 for run in runs for finding in run.findings if finding.agent == kind
    )
    hitl = sum(
        1
        for run in runs
        for finding in run.findings
        if finding.agent == kind and finding.requires_hitl
    )
    return {
        "id": kind.value,
        "name": name,
        "role": role,
        "backend": settings.llm_backend,
        "model": _effective_model(kind, settings),
        "latest_status": (
            latest.nodes.get(kind, NodeStatus.idle).value
            if latest
            else NodeStatus.idle.value
        ),
        "runs": len(entered),
        "success_rate": round(successes / len(entered), 3) if entered else 0.0,
        "successes": successes,
        "failures": failures,
        "findings": findings,
        "hitl": hitl,
    }


@router.get("")
def list_agents(repo: RepoDep, settings: SettingsDep) -> dict:
    runs = repo.list_runs()
    return {
        "agents": [_agent_stats(kind, settings, runs) for kind in AGENT_INFO],
        "config": {
            "llm_backend": settings.llm_backend,
            "ingestion_source": settings.ingestion_source,
            "publish_mode": settings.publish_mode,
            "gateway_url": settings.genai_gateway_url,
            "models": {
                "triage": settings.model_triage,
                "core_review": settings.model_core_review,
                "security": settings.model_security,
                "summarizer": settings.model_summarizer,
                "gemini": settings.model_gemini,
                "embeddings": settings.model_embeddings,
            },
        },
    }
