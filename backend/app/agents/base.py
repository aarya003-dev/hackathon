"""Agent interfaces and shared context."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
from ..domain.models import AgentKind, ReviewRun
from ..services.llm_gateway import LLMGateway


@dataclass
class AgentContext:
    gateway: LLMGateway
    settings: Settings
    run: ReviewRun


class BaseAgent:
    kind: AgentKind

    async def run(self, ctx: AgentContext, files: list[str] | None = None):
        raise NotImplementedError
