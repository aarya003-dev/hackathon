"""PR summarizer: aggregates findings into a review summary / changelog."""

from __future__ import annotations

from ..domain.models import AgentKind
from ..orchestration.prompts import build_summarizer_messages
from .base import AgentContext, BaseAgent


class SummarizerAgent(BaseAgent):
    kind = AgentKind.summarizer

    async def run(self, ctx: AgentContext, files: list[str] | None = None) -> str:
        response = await ctx.gateway.chat(
            ctx.settings.model_summarizer,
            build_summarizer_messages(ctx.run),
        )
        return response.parsed().get("summary", "")
