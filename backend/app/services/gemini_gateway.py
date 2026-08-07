"""Gemini backend for the review pipeline.

Adds a second *live* gateway alongside the GenAI Lab HTTP gateway
(:class:`app.services.llm_gateway.HttpLLMGateway`) — both are selectable via
``LLM_BACKEND`` and neither is removed. ``GeminiGateway`` speaks the same
:class:`app.services.llm_gateway.LLMGateway` protocol, so agents and the
orchestrator are unchanged.

Implemented with the official ``google-genai`` SDK:

- the leading ``system`` message is mapped to ``GenerateContentConfig.system_instruction``
- user/tool turns become ``Content`` parts
- responses are requested as JSON (``response_mime_type``) and any markdown
  code fences are stripped before they reach ``LLMResponse.parsed``
"""

from __future__ import annotations

import asyncio
import time

from google import genai
from google.genai import types

from .llm_gateway import LLMResponse, _strip_json_fences


class GeminiGateway:
    """Calls Google Gemini through ``google.genai`` (native async client).

    Uses its own configured model (``MODEL_GEMINI``); the per-agent genailab
    model names passed to :meth:`chat` are intentionally ignored so model
    selection stays centralized in the settings.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout: float = 60.0,
    ) -> None:
        # The SDK client rejects an empty key at construction, so it is built
        # lazily on first use; that lets the app boot (and tests stay
        # deterministic) before the developer pastes the key into .env.
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> LLMResponse:
        if not self._api_key:
            raise ValueError(
                "GEMINI_API_KEY is required when LLM_BACKEND=gemini; set it in .env"
            )
        client = self._get_client()

        # The orchestrator passes a leading "system" message; Gemini wants it
        # as config.system_instruction and only non-system turns as content.
        system_parts: list[str] = []
        user_parts: list[str] = []
        for message in messages:
            if message.get("role") == "system":
                system_parts.append(message.get("content", ""))
            else:
                user_parts.append(message.get("content", ""))

        config = types.GenerateContentConfig(
            system_instruction="\n".join(system_parts).strip() or None,
            temperature=temperature,
            response_mime_type="application/json",
        )
        content = types.Content(
            role="user",
            parts=[types.Part(text="\n\n".join(user_parts))],
        )

        start = time.monotonic()
        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=self._model, contents=content, config=config
                ),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError as exc:
            raise RuntimeError(
                f"gemini request timed out after {self._timeout:.0f}s"
            ) from exc

        latency_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage_metadata
        return LLMResponse(
            content=_strip_json_fences(response.text or ""),
            model=self._model,
            latency_ms=latency_ms,
            tokens_in=int(getattr(usage, "prompt_token_count", 0) or 0),
            tokens_out=int(getattr(usage, "candidates_token_count", 0) or 0),
        )

    async def aclose(self) -> None:
        if self._client is None:
            return
        close = getattr(self._client.aio, "close", None)
        if close is not None:
            result = close()
            if asyncio.iscoroutine(result):
                await result
