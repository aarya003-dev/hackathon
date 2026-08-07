"""Phase 6 settings validation and output-adapter tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.integrations.publisher import DryRunPublisher, create_publisher


def test_settings_defaults_load() -> None:
    # _env_file=None keeps the test independent of the developer's .env.
    settings = Settings(_env_file=None)
    assert settings.llm_backend == "demo"
    assert settings.embedding_dim == 256
    assert settings.publish_mode == "dry_run"
    assert settings.model_gemini == "gemini-3.6-flash"


def test_invalid_llm_backend_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_backend="bogus")


def test_gemini_backend_is_accepted() -> None:
    settings = Settings(_env_file=None, llm_backend="gemini")
    assert settings.llm_backend == "gemini"
    assert settings.gemini_api_key == ""


def test_invalid_embedding_dim_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, embedding_dim=4)


def test_publish_mode_none_disables_publisher() -> None:
    assert create_publisher(Settings(_env_file=None, publish_mode="none")) is None
    assert isinstance(create_publisher(Settings(_env_file=None)), DryRunPublisher)
