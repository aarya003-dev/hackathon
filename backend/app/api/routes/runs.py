"""Review run endpoints: list, detail, and the SSE event stream."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import computed_field

from ...domain.models import ReviewRun
from ..deps import BusDep, RepoDep

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


class RunDetail(ReviewRun):
    @computed_field  # type: ignore[prop-decorator]
    @property
    def hitl_pending(self) -> int:
        return sum(1 for approval in self.approvals if approval.status == "pending")


def _summary(run: ReviewRun) -> dict:
    return {
        "id": run.id,
        "status": run.status.value,
        "repository": run.repository.name,
        "commit": run.commit.sha[:12],
        "base_sha": run.commit.base_sha[:12],
        "findings": len(run.findings),
        "hitl_pending": sum(
            1 for approval in run.approvals if approval.status == "pending"
        ),
        "summary": run.summary,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
    }


@router.get("")
def list_runs(repo: RepoDep) -> list[dict]:
    return [_summary(run) for run in repo.list_runs()]


@router.get("/{run_id}")
def get_run(run_id: str, repo: RepoDep) -> RunDetail:
    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return RunDetail.model_validate_json(run.model_dump_json())


@router.get("/{run_id}/events")
async def run_events(
    run_id: str,
    request: Request,
    repo: RepoDep,
    bus: BusDep,
):
    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    async def stream():
        async for event in bus.stream(run_id):
            if await request.is_disconnected():
                break
            yield f"event: {event.event_type}\ndata: {event.model_dump_json()}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
