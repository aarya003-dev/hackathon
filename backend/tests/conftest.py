"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app import config as app_config
from app.main import create_app


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """TestClient kept open for the whole test so all requests share one
    event loop. This mirrors uvicorn (single loop) and lets in-process
    background review tasks run and resume across requests.

    Settings are loaded without the developer's ``.env`` so the suite is
    deterministic (the default ``demo`` gateway) no matter what backend is
    configured locally.
    """
    test_settings = app_config.Settings(_env_file=None)
    monkeypatch.setattr("app.main.get_settings", lambda: test_settings)
    with TestClient(create_app()) as test_client:
        yield test_client
