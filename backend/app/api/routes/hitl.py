"""HITL checkpoint decisions.

A run paused at ``waiting_hitl`` resumes only when every pending approval has
been approved or rejected by an authorized reviewer.
"""

from __future__ import annotations

import time
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...domain.models import AgentKind, RunEvent, RunStatus
from ..deps import BusDep, RepoDep

router = APIRouter(prefix="/api/v1/hitl", tags=["hitl"])


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject"]
    by: str
    note: str = ""


@router.post("/{approval_id}/decision")
async def decide(
    approval_id: str,
    body: DecisionIn,
    repo: RepoDep,
    bus: BusDep,
) -> dict:
    run = _find_run_with_approval(repo, approval_id)
    if run is None:
        raise HTTPException(status_code=404, detail="approval not found")
    if run.status != RunStatus.waiting_hitl:
        raise HTTPException(
            status_code=409, detail="run is not waiting for a human decision"
        )

    approval = next(item for item in run.approvals if item.id == approval_id)
    if approval.status != "pending":
        raise HTTPException(status_code=409, detail="approval already decided")

    approval.status = "approved" if body.decision == "approve" else "rejected"
    approval.decided_by = body.by
    approval.decided_at = time.time()
    run.updated_at = time.time()
    repo.update_run(run)

    bus.publish(
        RunEvent(
            run_id=run.id,
            event_type="hitl.resolved",
            agent=AgentKind.security,
            payload={
                "approval_id": approval_id,
                "decision": body.decision,
                "by": body.by,
            },
        )
    )

    # The paused run's orchestrator task polls the repository for decided
    # approvals and resumes on its own.
    return {"status": approval.status, "run_id": run.id}


def _find_run_with_approval(repo, approval_id: str):
    for run in repo.list_runs():
        if any(item.id == approval_id for item in run.approvals):
            return run
    return None
