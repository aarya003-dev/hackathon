"""Seed the demo dashboard with a few review runs.

Requires the backend to be running on localhost:8000 (LLM_BACKEND=demo is the
default, so no credentials are needed):

    uvicorn backend.app.main:app --reload     # terminal 1
    python backend/scripts/seed_demo.py       # terminal 2

The script ingests three synthetic pushes (clean, style issues, security issue)
and auto-approves any HITL checkpoint so every run reaches a terminal state.
"""

from __future__ import annotations

import time
import uuid

import httpx

BASE_URL = "http://localhost:8000"
INGEST_SECRET = "dev-secret"

CLEAN_DIFF = (
    "diff --git a/app.py b/app.py\n"
    "index 111..222 100644\n"
    "--- a/app.py\n+++ b/app.py\n"
    "@@ -1,3 +1,3 @@\n"
    " def f():\n"
    '-    return "old"\n'
    '+    return "new"\n'
)

STYLE_DIFF = (
    "diff --git a/utils.py b/utils.py\n"
    "index 333..444 100644\n"
    "--- a/utils.py\n+++ b/utils.py\n"
    "@@ -1,6 +1,8 @@\n"
    " def run():\n"
    '-    return "ok"\n'
    "+    try:\n"
    '+        return "ok"\n'
    "+    except:\n"
    '+        print("debug")\n'
    "+        pass\n"
)

SECURITY_DIFF = (
    "diff --git a/app.py b/app.py\n"
    "index 555..666 100644\n"
    "--- a/app.py\n+++ b/app.py\n"
    "@@ -1,5 +1,5 @@\n"
    " def handle():\n"
    '-    return run("clean")\n'
    "+    eval(input())\n"
    '+    print("debug")\n'
)

FIXTURES = [
    ("clean", ("app.py",), CLEAN_DIFF, "refactor: extract helper"),
    ("style", ("utils.py",), STYLE_DIFF, "feat: add logging to worker"),
    ("security", ("app.py",), SECURITY_DIFF, "fix: wire user input"),
]


def ingest(
    client: httpx.Client, diff: str, files: tuple[str, ...], message: str
) -> str:
    event = {
        "event": "push",
        "provider": "local_git",
        "repository": {
            "name": "demo-repo",
            "path": "/tmp/demo-repo",
            "clone_url": None,
        },
        "commit": {
            "sha": uuid.uuid4().hex,
            "base_sha": uuid.uuid4().hex,
            "message": message,
            "files": list(files),
            "diff": diff,
        },
    }
    response = client.post(
        "/api/v1/ingest/git", json=event, headers={"X-Ingest-Secret": INGEST_SECRET}
    )
    response.raise_for_status()
    return response.json()["run_id"]


def approve_hitl(client: httpx.Client, run_id: str) -> None:
    """Poll until the run is paused or terminal; approve any pending decision."""
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        run = client.get(f"/api/v1/runs/{run_id}").json()
        if run["status"] == "waiting_hitl":
            for approval in run["approvals"]:
                if approval["status"] == "pending":
                    decision = client.post(
                        f"/api/v1/hitl/{approval['id']}/decision",
                        json={"decision": "approve", "by": "seed"},
                    )
                    decision.raise_for_status()
            return
        if run["status"] in ("succeeded", "failed"):
            return
        time.sleep(0.2)
    raise RuntimeError(f"run {run_id} did not reach a terminal state in time")


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        health = client.get("/health")
        if health.status_code != 200:
            raise SystemExit("Backend is not running on " + BASE_URL)

        for label, files, diff, message in FIXTURES:
            run_id = ingest(client, diff, files, message)
            approve_hitl(client, run_id)
            run = client.get(f"/api/v1/runs/{run_id}").json()
            print(
                f"[{label:8}] {run_id[:12]}  status={run['status']}  "
                f"findings={len(run['findings'])}"
            )

        print("Done. Open http://localhost:5173 to view the dashboard.")


if __name__ == "__main__":
    main()
