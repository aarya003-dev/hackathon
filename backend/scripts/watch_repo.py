#!/usr/bin/env python3
"""Poll a local git repo and POST normalized review events to the backend.

This is the simplest "use git commits to track data on a local repo" path:
every time HEAD moves, the change ``<previous>..HEAD`` is sent as a review
event. No hooks, no deployment, no port forwarding.

Usage (from the repository root, with .venv active):

    python -m scripts.watch_repo --repo /path/to/your/repo

Optional flags: --url (default from INGEST_URL or the local backend),
--secret (default from INGEST_SECRET), --interval seconds, --state file.
"""

import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.integrations.local_git import GitCommandError, build_push_event


def _last_sha(state_file: Path) -> str | None:
    if state_file.exists():
        value = state_file.read_text().strip()
        return value or None
    return None


def _head_sha(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise GitCommandError(result.stderr.strip())
    return result.stdout.strip()


def _post(url: str, secret: str, body: bytes) -> None:
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("X-Ingest-Secret", secret)
    with urllib.request.urlopen(request) as resp:
        status = resp.status
    if status != 202:
        raise RuntimeError(f"backend returned HTTP {status}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", required=True, help="Path to the local git repo to watch"
    )
    parser.add_argument(
        "--url",
        default=os.getenv("INGEST_URL", "http://localhost:8000/api/v1/ingest/git"),
    )
    parser.add_argument("--secret", default=os.getenv("INGEST_SECRET", "dev-secret"))
    parser.add_argument(
        "--interval", type=int, default=int(os.getenv("GIT_POLL_SECONDS", "10"))
    )
    parser.add_argument("--state", default=".review-state")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    state_file = repo / args.state
    seen = _last_sha(state_file)

    while True:
        try:
            head = _head_sha(repo)
        except GitCommandError as exc:
            print(f"[watch] {exc}", file=sys.stderr)
            time.sleep(args.interval)
            continue

        if head and head != seen:
            base = seen or f"{head}~1"
            try:
                event = build_push_event(repo, base, head)
            except GitCommandError as exc:
                print(f"[watch] {exc}", file=sys.stderr)
                time.sleep(args.interval)
                continue

            try:
                _post(args.url, args.secret, event.model_dump_json().encode())
                state_file.write_text(head)
                seen = head
                print(f"[watch] ingested {head[:12]} ({len(event.commit.files)} files)")
            except Exception as exc:  # noqa: BLE001 - watcher keeps running
                print(f"[watch] ingest failed: {exc}", file=sys.stderr)

        time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
