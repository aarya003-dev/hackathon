"""Shared helpers for Phase 3 orchestration tests."""

from __future__ import annotations

import time
import uuid

from fastapi.testclient import TestClient

INGEST_SECRET = "dev-secret"


def push_event(
    files: tuple[str, ...] = ("app.py",), diff: str = "", message: str = "demo change"
) -> dict:
    return {
        "event": "push",
        "provider": "local_git",
        "repository": {
            "name": "demo-repo",
            "path": "/tmp/demo-repo",
            "clone_url": "file:///tmp/demo-repo",
        },
        "commit": {
            "sha": uuid.uuid4().hex,
            "base_sha": uuid.uuid4().hex,
            "message": message,
            "files": list(files),
            "diff": diff,
        },
    }


def post_event(
    client: TestClient, diff: str = "", files: tuple[str, ...] = ("app.py",)
) -> str:
    response = client.post(
        "/api/v1/ingest/git",
        json=push_event(files=files, diff=diff),
        headers={"X-Ingest-Secret": INGEST_SECRET},
    )
    assert response.status_code == 202, response.text
    return response.json()["run_id"]


def wait_for(
    client: TestClient, run_id: str, targets: set[str], timeout: float = 5.0
) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run = client.get(f"/api/v1/runs/{run_id}").json()
        if run["status"] in targets:
            return run
        time.sleep(0.02)
    raise AssertionError(
        f"run {run_id} did not reach {targets}; last status: {run['status']}"
    )


def diff_with_security() -> str:
    return (
        "diff --git a/app.py b/app.py\n"
        "index 111..222 100644\n"
        "--- a/app.py\n+++ b/app.py\n"
        "@@ -1,5 +1,5 @@\n"
        " def handle():\n"
        '-    return run("clean")\n'
        "+    eval(input())\n"
        '+    print("debug")\n'
    )


def diff_clean() -> str:
    return (
        "diff --git a/app.py b/app.py\n"
        "index 111..222 100644\n"
        "--- a/app.py\n+++ b/app.py\n"
        "@@ -1,3 +1,3 @@\n"
        " def f():\n"
        '-    return "old"\n'
        '+    return "new"\n'
    )
