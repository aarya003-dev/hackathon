"""Security agent: vulnerability findings and HITL triggers.

A finding requests HITL when it is critical, or when a high-severity finding
is delivered with low confidence (uncertain high risk).
"""

from __future__ import annotations

from uuid import uuid4

from ..domain.models import AgentKind, Finding, Severity
from ..orchestration.prompts import build_security_messages
from .base import AgentContext, BaseAgent, coerce_confidence

_HITL_CONFIDENCE = 0.8


class SecurityAgent(BaseAgent):
    kind = AgentKind.security

    async def run(
        self,
        ctx: AgentContext,
        files: list[str] | None = None,
        rag_context: str = "",
    ) -> list[Finding]:
        response = await ctx.gateway.chat(
            ctx.settings.model_security,
            build_security_messages(ctx.run, files, rag_context),
        )
        data = response.parsed()
        findings: list[Finding] = []
        for raw in data.get("findings", []):
            severity = Severity(raw.get("severity", "warning"))
            confidence = coerce_confidence(raw.get("confidence", 1.0))
            requires_hitl = severity == Severity.critical or (
                severity in (Severity.error, Severity.critical)
                and confidence < _HITL_CONFIDENCE
            )
            findings.append(
                Finding(
                    id=uuid4().hex,
                    agent=AgentKind.security,
                    severity=severity,
                    category=raw.get("category", "security"),
                    file_path=raw.get("file_path", ""),
                    line_start=raw.get("line_start"),
                    line_end=raw.get("line_end"),
                    message=raw.get("message", ""),
                    suggestion=raw.get("suggestion", ""),
                    confidence=confidence,
                    requires_hitl=requires_hitl,
                )
            )
        return findings
