"""Suggestion agent: maintainability, scalability, and software engineering best practices."""

from __future__ import annotations

from uuid import uuid4

from ..domain.models import AgentKind, Finding
from ..orchestration.prompts import build_suggestion_messages
from .base import AgentContext, BaseAgent, coerce_confidence, coerce_severity


class SuggestionAgent(BaseAgent):
    kind = AgentKind.suggestion

    async def run(
        self,
        ctx: AgentContext,
        files: list[str] | None = None,
        rag_context: str = "",
    ) -> list[Finding]:
        response = await ctx.gateway.chat(
            ctx.settings.model_suggestion,
            build_suggestion_messages(ctx.run, files, rag_context),
        )
        data = response.parsed()
        findings: list[Finding] = []
        for raw in data.get("findings", []):
            findings.append(
                Finding(
                    id=uuid4().hex,
                    agent=AgentKind.suggestion,
                    severity=coerce_severity(raw.get("severity", "info")),
                    category=raw.get("category", "best_practices"),
                    file_path=raw.get("file_path") or raw.get("file") or raw.get("path") or "",
                    line_start=raw.get("line_start"),
                    line_end=raw.get("line_end"),
                    message=raw.get("message", ""),
                    suggestion=raw.get("suggestion", ""),
                    confidence=coerce_confidence(raw.get("confidence", 0.9)),
                )
            )
        return findings
