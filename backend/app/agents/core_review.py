"""Core code-review agent: style, syntax, and functional findings."""

from __future__ import annotations

from uuid import uuid4

from ..domain.models import AgentKind, Finding, Severity
from ..orchestration.prompts import build_core_messages
from .base import AgentContext, BaseAgent


class CoreReviewAgent(BaseAgent):
    kind = AgentKind.core

    async def run(
        self,
        ctx: AgentContext,
        files: list[str] | None = None,
        rag_context: str = "",
    ) -> list[Finding]:
        response = await ctx.gateway.chat(
            ctx.settings.model_core_review,
            build_core_messages(ctx.run, files, rag_context),
        )
        data = response.parsed()
        findings: list[Finding] = []
        for raw in data.get("findings", []):
            findings.append(
                Finding(
                    id=uuid4().hex,
                    agent=AgentKind.core,
                    severity=Severity(raw.get("severity", "warning")),
                    category=raw.get("category", "style"),
                    file_path=raw.get("file_path", ""),
                    line_start=raw.get("line_start"),
                    line_end=raw.get("line_end"),
                    message=raw.get("message", ""),
                    suggestion=raw.get("suggestion", ""),
                    confidence=float(raw.get("confidence", 1.0)),
                )
            )
        return findings
