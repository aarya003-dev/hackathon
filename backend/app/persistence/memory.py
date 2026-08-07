"""In-memory implementation of the run repository (single process)."""

from __future__ import annotations

import threading

from ..domain.models import ReviewRun


class InMemoryRunRepository:
    def __init__(self) -> None:
        self._runs: dict[str, ReviewRun] = {}
        self._lock = threading.Lock()

    def create_run(self, run: ReviewRun) -> ReviewRun:
        with self._lock:
            self._runs[run.id] = run
        return run

    def get_run(self, run_id: str) -> ReviewRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def update_run(self, run: ReviewRun) -> ReviewRun:
        with self._lock:
            self._runs[run.id] = run
        return run

    def list_runs(self) -> list[ReviewRun]:
        with self._lock:
            return list(self._runs.values())

    def find_by_commit(self, repo_name: str, sha: str) -> ReviewRun | None:
        with self._lock:
            for run in self._runs.values():
                if run.repository.name == repo_name and run.commit.sha == sha:
                    return run
        return None
