"""Domain models for review runs, findings, HITL approvals, and events."""

from __future__ import annotations

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .events import CommitRef, RepositoryInfo


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    waiting_hitl = "waiting_hitl"
    succeeded = "succeeded"
    failed = "failed"


class AgentKind(str, Enum):
    triage = "triage"
    core = "core_review"
    security = "security"
    summarizer = "summarizer"


class NodeStatus(str, Enum):
    idle = "idle"
    running = "running"
    success = "success"
    failed = "failed"
    paused = "paused"


class Severity(str, Enum):
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class Finding(BaseModel):
    id: str
    agent: AgentKind
    severity: Severity
    category: str
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    message: str
    suggestion: str = ""
    confidence: float = 1.0
    requires_hitl: bool = False


class HitlApproval(BaseModel):
    id: str
    run_id: str
    finding_id: str
    status: str = "pending"  # pending | approved | rejected
    requested_at: float = Field(default_factory=time.time)
    decided_at: float | None = None
    decided_by: str | None = None


class ReviewRun(BaseModel):
    id: str
    provider: str
    repository: RepositoryInfo
    commit: CommitRef
    status: RunStatus = RunStatus.queued
    nodes: dict[AgentKind, NodeStatus] = Field(
        default_factory=lambda: {kind: NodeStatus.idle for kind in AgentKind}
    )
    findings: list[Finding] = []
    approvals: list[HitlApproval] = []
    summary: str = ""
    publication: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class RunEvent(BaseModel):
    run_id: str
    event_type: str
    agent: AgentKind | None = None
    payload: dict[str, Any] = {}
    at: float = Field(default_factory=time.time)
