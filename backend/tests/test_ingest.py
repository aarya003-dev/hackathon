"""Tests for the ingestion endpoints."""

from app.main import create_app
from fastapi.testclient import TestClient


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
