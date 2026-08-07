"""Ingestion endpoints.

``POST /api/v1/ingest/git`` accepts the payload produced by the local-git
adapter (bare-repo ``post-receive`` hook or polling watcher) and enqueues a
review run, feeding the same pipeline a GitHub webhook would. The endpoint is
idempotent by commit SHA.
"""

import hmac
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException

from ...config import get_settings
from ...domain.events import IngestEvent
from ...domain.models import ReviewRun, RunEvent
from ..deps import BusDep, OrchestratorDep, RepoDep

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


def _verify_secret(secret: str | None) -> bool:
    settings = get_settings()
    expected = settings.ingest_secret.encode()
    provided = (secret or "").encode()
    return hmac.compare_digest(expected, provided)


@router.post("/git", status_code=202)
async def ingest_git(
    event: IngestEvent,
    repo: RepoDep,
    bus: BusDep,
    orchestrator: OrchestratorDep,
    x_ingest_secret: Annotated[str | None, Header()] = None,
) -> dict:
    if not _verify_secret(x_ingest_secret):
        raise HTTPException(status_code=401, detail="invalid ingest secret")

    # Idempotency: one review per commit SHA per repository.
    existing = repo.find_by_commit(event.repository.name, event.commit.sha)
    if existing is not None:
        return {
            "accepted": True,
            "duplicate": True,
            "run_id": existing.id,
            "commit": event.commit.sha,
        }

    run = ReviewRun(
        id=uuid4().hex,
        provider=event.provider,
        repository=event.repository,
        commit=event.commit,
    )
    repo.create_run(run)
    bus.publish(RunEvent(run_id=run.id, event_type="run.queued"))
    orchestrator.enqueue(run.id)

    return {
        "accepted": True,
        "run_id": run.id,
        "provider": event.provider,
        "event": event.event,
        "commit": event.commit.sha,
        "base_sha": event.commit.base_sha,
        "files": len(event.commit.files),
        "diff_bytes": len(event.commit.diff),
    }
