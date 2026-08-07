"""Triage agent: classifies changed files and routes work to specialized agents."""

from __future__ import annotations

from ..domain.models import AgentKind
from ..orchestration.prompts import build_triage_messages
from .base import AgentContext, BaseAgent


class TriageAgent(BaseAgent):
    kind = AgentKind.triage

    async def run(self, ctx: AgentContext, files: list[str] | None = None) -> dict:
        response = await ctx.gateway.chat(
            ctx.settings.model_triage,
            build_triage_messages(ctx.run),
        )
        data = response.parsed()
        return {
            "core": data.get("core") or ctx.run.commit.files,
            "security": data.get("security") or ctx.run.commit.files,
        }
