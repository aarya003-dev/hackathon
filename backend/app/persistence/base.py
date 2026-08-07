"""Repository interfaces.

The in-memory implementation is the default for local development and tests;
a SQL/PostgreSQL implementation can be dropped in behind the same interface
(Phase 1 leftover — no Docker/Postgres required for the Phase 3 slice).
"""

from __future__ import annotations

from typing import Protocol

from ..domain.models import ReviewRun


class RunRepository(Protocol):
    def create_run(self, run: ReviewRun) -> ReviewRun: ...

    def get_run(self, run_id: str) -> ReviewRun | None: ...

    def update_run(self, run: ReviewRun) -> ReviewRun: ...

    def list_runs(self) -> list[ReviewRun]: ...

    def find_by_commit(self, repo_name: str, sha: str) -> ReviewRun | None: ...
