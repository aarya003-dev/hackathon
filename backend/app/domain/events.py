"""Normalized ingestion events.

Git providers and the local-git adapter all produce these domain events so the
orchestration pipeline is provider-neutral. Provider-specific payloads are
converted at integration boundaries.
"""

from pydantic import BaseModel


class RepositoryInfo(BaseModel):
    name: str
    owner: str | None = None
    path: str
    clone_url: str | None = None


class CommitRef(BaseModel):
    sha: str
    base_sha: str
    message: str = ""
    author: str | None = None
    files: list[str] = []
    diff: str = ""


class IngestEvent(BaseModel):
    event: str  # "push" | "pull_request.opened" | ...
    provider: str
    repository: RepositoryInfo
    commit: CommitRef
