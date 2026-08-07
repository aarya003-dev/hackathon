"""Ingestion endpoints.

``POST /api/v1/ingest/git`` accepts the payload produced by the local-git
adapter (bare-repo ``post-receive`` hook or polling watcher) and enqueues a
review run, feeding the same pipeline a GitHub webhook would. The endpoint is
idempotent by commit SHA.

``POST /api/v1/ingest/analyze`` is an on-demand variant: it builds a push event
for the latest commit of a known repository (an explicit ``?repo=`` override,
the most recently ingested repository, or the configured ``GIT_REPO_PATH``) and
enqueues it, so the dashboard's "New Analysis" action works without a watcher.
"""

import hmac
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query

from ...config import Settings
from ...domain.events import IngestEvent
from ...domain.models import ReviewRun, RunEvent
from ...integrations.local_git import GitCommandError, build_push_event, rev_parse
from ..deps import BusDep, OrchestratorDep, RepoDep, SettingsDep

# Empty tree SHA: base for analyzing the very first commit (no HEAD~1 parent).
_EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


def _verify_secret(secret: str | None, settings: Settings) -> bool:
    expected = settings.ingest_secret.encode()
    provided = (secret or "").encode()
    return hmac.compare_digest(expected, provided)


def _enqueue(
    event: IngestEvent, repo: RepoDep, bus: BusDep, orchestrator: OrchestratorDep
) -> dict:
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
        "duplicate": False,
        "run_id": run.id,
        "provider": event.provider,
        "event": event.event,
        "commit": event.commit.sha,
        "base_sha": event.commit.base_sha,
        "files": len(event.commit.files),
        "diff_bytes": len(event.commit.diff),
    }


@router.post("/git", status_code=202)
async def ingest_git(
    event: IngestEvent,
    repo: RepoDep,
    bus: BusDep,
    orchestrator: OrchestratorDep,
    settings: SettingsDep,
    x_ingest_secret: Annotated[str | None, Header()] = None,
) -> dict:
    if not _verify_secret(x_ingest_secret, settings):
        raise HTTPException(status_code=401, detail="invalid ingest secret")
    return _enqueue(event, repo, bus, orchestrator)


@router.post("/analyze", status_code=202)
async def analyze_latest(
    repo: RepoDep,
    bus: BusDep,
    orchestrator: OrchestratorDep,
    settings: SettingsDep,
    repo_path: Annotated[str | None, Query(alias="repo")] = None,
    x_ingest_secret: Annotated[str | None, Header()] = None,
) -> dict:
    if not _verify_secret(x_ingest_secret, settings):
        raise HTTPException(status_code=401, detail="invalid ingest secret")

    runs = repo.list_runs()
    path = repo_path
    if not path:
        last = max(runs, key=lambda run: run.updated_at, default=None)
        path = (last.repository.path if last else None) or settings.git_repo_path
    if not path:
        raise HTTPException(
            status_code=400,
            detail="no repository configured: set GIT_REPO_PATH or ingest at least one commit",
        )

    repo_dir = Path(path).resolve()
    # Base = the most recent commit already reviewed for this repo, else the
    # parent of HEAD (or the empty tree for an initial commit).
    prior = max(
        (run for run in runs if run.repository.name == repo_dir.name),
        key=lambda run: run.updated_at,
        default=None,
    )
    try:
        head = rev_parse(repo_dir, "HEAD")
        base_sha = prior.commit.sha if prior else _resolve_base(repo_dir)
        event = build_push_event(repo_dir, base_sha, head)
    except GitCommandError as exc:
        raise HTTPException(
            status_code=502, detail=f"cannot read repository: {exc}"
        ) from exc

    return _enqueue(event, repo, bus, orchestrator)


def _resolve_base(repo_dir: Path) -> str:
    try:
        return rev_parse(repo_dir, "HEAD~1")
    except GitCommandError:
        return _EMPTY_TREE
