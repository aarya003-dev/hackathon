"""PR summarizer: aggregates findings into a structured review summary."""

from __future__ import annotations

from ..domain.models import AgentKind
from ..orchestration.prompts import build_summarizer_messages
from .base import AgentContext, BaseAgent


def _as_string_list(raw: object) -> list[str]:
    """Coerce the model's bullet fields (list or newline text) to clean lists."""
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str) and raw.strip():
        return [line.strip() for line in raw.splitlines() if line.strip()]
    return []


class SummarizerAgent(BaseAgent):
    kind = AgentKind.summarizer

    async def run(self, ctx: AgentContext, files: list[str] | None = None) -> dict:
        response = await ctx.gateway.chat(
            ctx.settings.model_summarizer,
            build_summarizer_messages(ctx.run),
        )
        data = response.parsed()
        if not isinstance(data, dict):
            data = {}
        # ``summary`` is the plain-text narrative; the bullet fields power the
        # structured summary page. Missing keys (older models / test stubs)
        # degrade to empty lists instead of crashing.
        return {
            "summary": str(data.get("summary", "")),
            "changes": _as_string_list(data.get("changes")),
            "impact": _as_string_list(data.get("impact")),
            "recommendations": _as_string_list(data.get("recommendations")),
        }
