"""Unified gateway to the GenAI Lab model endpoint (https://genailab.tcs.in).

Owns authentication, timeouts, retries, structured-response validation, and
token/latency telemetry. Agents never talk to a model provider directly; they
call ``LLMGateway.chat`` and parse the returned JSON.

The ``DemoGateway`` in :mod:`app.services.demo_gateway` is the deterministic
offline stand-in used for tests and local demos.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Protocol

import httpx
from pydantic import BaseModel

from ..config import Settings


import re

def _strip_json_fences(text: str) -> str:
    """Remove reasoning tags (<think>...</think>) and code fences around JSON payloads."""
    stripped = text.strip()
    # Remove <think>...</think> tags if present (e.g. DeepSeek-R1)
    stripped = re.sub(r"<think>.*?</think>", "", stripped, flags=re.DOTALL).strip()
    # Extract ```json ... ``` content if present
    match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", stripped, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback to finding JSON object or array
    match = re.search(r"(\{.*\}|\[.*\])", stripped, re.DOTALL)
    if match:
        return match.group(1).strip()
    return stripped


class LLMResponse(BaseModel):
    content: str
    model: str
    latency_ms: int
    tokens_in: int = 0
    tokens_out: int = 0

    def parsed(self) -> dict[str, Any]:
        return json.loads(_strip_json_fences(self.content))


class LLMGateway(Protocol):
    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> LLMResponse: ...


class HttpLLMGateway:
    """HTTPX client for an OpenAI-compatible chat-completions endpoint."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=timeout, verify=False)
        self._max_retries = max_retries

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> LLMResponse:
        url = f"{self._base_url}/v1/chat/completions"
        payload = {"model": model, "messages": messages}
        if "gpt-5" not in model:
            payload["temperature"] = temperature
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            start = time.monotonic()
            try:
                response = await self._client.post(url, json=payload, headers=headers)
                if (
                    response.status_code in (429, 500, 502, 503, 504)
                    and attempt < self._max_retries
                ):
                    await asyncio.sleep(2**attempt)
                    continue
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return LLMResponse(
                    content=content,
                    model=model,
                    latency_ms=int((time.monotonic() - start) * 1000),
                    tokens_in=int(usage.get("prompt_tokens", 0)),
                    tokens_out=int(usage.get("completion_tokens", 0)),
                )
            except httpx.HTTPStatusError as exc:
                last_error = RuntimeError(f"HTTP {exc.response.status_code}: {exc.response.text}")
                if attempt < self._max_retries:
                    await asyncio.sleep(2**attempt)
                    continue
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(2**attempt)
                    continue
        raise RuntimeError(
            f"gateway request failed after {self._max_retries + 1} attempts: {last_error}"
        )

    async def aclose(self) -> None:
        await self._client.aclose()


def create_gateway(settings: Settings) -> LLMGateway:
    """Build the active gateway: GenAI Lab HTTP, Gemini, or the demo gateway."""
    if settings.llm_backend == "http":
        return HttpLLMGateway(
            settings.genai_gateway_url,
            settings.genai_api_key,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    if settings.llm_backend == "gemini":
        from .gemini_gateway import GeminiGateway

        return GeminiGateway(
            api_key=settings.gemini_api_key,
            model=settings.model_gemini,
            timeout=settings.llm_timeout_seconds,
        )
    from .demo_gateway import DemoGateway

    return DemoGateway()
