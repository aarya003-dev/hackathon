"""Unit tests for the Gemini gateway.

The SDK client is stubbed (``aio.models.generate_content`` is replaced with a
fake) so no network or real API key is required.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from google.genai import types

from app.services.gemini_gateway import GeminiGateway


class _FakeUsage:
    prompt_token_count = 11
    candidates_token_count = 7


def _make_gateway() -> GeminiGateway:
    """Gateway whose lazily-built SDK client is pre-built so it can be stubbed."""
    gateway = GeminiGateway(api_key="test-key", model="gemini-3.6-flash")
    gateway._get_client()  # pre-builds the real (offline) client
    return gateway


def test_chat_returns_json_and_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = _make_gateway()
    captured: dict[str, object] = {}

    async def fake_generate_content(
        model: str, contents: types.Content, config: types.GenerateContentConfig
    ) -> object:
        captured["model"] = model
        captured["system_instruction"] = config.system_instruction
        captured["temperature"] = config.temperature
        return SimpleNamespace(text='{"summary": "ok"}', usage_metadata=_FakeUsage())

    monkeypatch.setattr(
        gateway._get_client().aio.models,
        "generate_content",
        fake_generate_content,
    )

    response = asyncio.run(
        gateway.chat(
            "azure/genailab-maas-gpt-4o-mini",  # per-agent name ignored by Gemini
            [
                {"role": "system", "content": "You are a code reviewer."},
                {"role": "user", "content": "Review this diff."},
            ],
        )
    )

    assert captured["model"] == "gemini-3.6-flash"
    assert captured["system_instruction"] == "You are a code reviewer."
    assert captured["temperature"] == 0.2
    assert response.parsed() == {"summary": "ok"}
    assert response.tokens_in == 11
    assert response.tokens_out == 7


def test_chat_strips_json_fences(monkeypatch: pytest.MonkeyPatch) -> None:
    gateway = _make_gateway()

    async def fake_generate_content(
        model: str, contents: types.Content, config: types.GenerateContentConfig
    ) -> object:
        return SimpleNamespace(
            text='```json\n{"summary": "ok"}\n```',
            usage_metadata=None,
        )

    monkeypatch.setattr(
        gateway._get_client().aio.models,
        "generate_content",
        fake_generate_content,
    )

    response = asyncio.run(
        gateway.chat("gemini-3.6-flash", [{"role": "user", "content": "hi"}])
    )
    assert response.parsed() == {"summary": "ok"}


def test_empty_api_key_raises_at_call_time() -> None:
    gateway = GeminiGateway(api_key="", model="gemini-3.6-flash")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        asyncio.run(
            gateway.chat("gemini-3.6-flash", [{"role": "user", "content": "hi"}])
        )
