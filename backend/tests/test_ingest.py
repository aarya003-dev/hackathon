"""Tests for the ingestion endpoints."""

import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def _sample_event() -> dict:
    return {
        "event": "push",
        "provider": "local_git",
        "repository": {
            "name": "sample-repo",
            "owner": None,
            "path": "/tmp/sample-repo",
            "clone_url": "file:///tmp/sample-repo",
        },
        "commit": {
            "sha": "b" * 40,
            "base_sha": "a" * 40,
            "message": "fix bug",
            "author": "Test User",
            "files": ["app.py"],
            "diff": "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-return 'x'\n+return 'y'\n",
        },
    }


def test_health() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ingest_accepts_valid_event() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/ingest/git",
        json=_sample_event(),
        headers={"X-Ingest-Secret": "dev-secret"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["commit"] == "b" * 40
    assert body["files"] == 1


def test_ingest_rejects_wrong_secret() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/ingest/git",
        json=_sample_event(),
        headers={"X-Ingest-Secret": "wrong"},
    )
    assert response.status_code == 401


def test_ingest_rejects_missing_secret() -> None:
    client = TestClient(create_app())
    response = client.post("/api/v1/ingest/git", json=_sample_event())
    assert response.status_code == 401


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "-C", str(path), "init", "-q", "-b", "main"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test User"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "--allow-empty", "-m", "init"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "--allow-empty", "-m", "second"],
        check=True,
    )


def test_analyze_requires_a_repository() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/ingest/analyze", headers={"X-Ingest-Secret": "dev-secret"}
    )
    assert response.status_code == 400


def test_analyze_reviews_latest_commit(tmp_path: Path) -> None:
    repo_dir = tmp_path / "watched-repo"
    repo_dir.mkdir()
    _init_git_repo(repo_dir)

    client = TestClient(create_app())
    response = client.post(
        "/api/v1/ingest/analyze",
        params={"repo": str(repo_dir)},
        headers={"X-Ingest-Secret": "dev-secret"},
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["duplicate"] is False
    assert payload["event"] == "push"
    assert len(payload["commit"]) == 40
    assert payload["base_sha"] != payload["commit"]

    # Idempotent: analyzing the same HEAD returns the same run.
    repeat = client.post(
        "/api/v1/ingest/analyze",
        params={"repo": str(repo_dir)},
        headers={"X-Ingest-Secret": "dev-secret"},
    )
    assert repeat.status_code == 202
    assert repeat.json()["duplicate"] is True
    assert repeat.json()["run_id"] == payload["run_id"]


def test_analyze_rejects_wrong_secret(tmp_path: Path) -> None:
    repo_dir = tmp_path / "watched-repo"
    repo_dir.mkdir()
    _init_git_repo(repo_dir)

    client = TestClient(create_app())
    response = client.post(
        "/api/v1/ingest/analyze",
        params={"repo": str(repo_dir)},
        headers={"X-Ingest-Secret": "wrong"},
    )
    assert response.status_code == 401
