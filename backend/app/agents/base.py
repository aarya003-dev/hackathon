"""Agent interfaces and shared context."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..config import Settings
from ..domain.models import AgentKind, ReviewRun, Severity

# LLMs frequently return descriptive strings for numeric fields like
# confidence.  Map common natural-language descriptors to floats so the
# pipeline doesn't crash on ``float("high")``.
_CONFIDENCE_MAP: dict[str, float] = {
    "very high": 0.95,
    "high": 0.9,
    "medium": 0.7,
    "low": 0.5,
    "very low": 0.3,
    "none": 0.0,
}

_SEVERITY_MAP: dict[str, Severity] = {
    "info": Severity.info,
    "low": Severity.info,
    "warning": Severity.warning,
    "medium": Severity.warning,
    "error": Severity.error,
    "high": Severity.error,
    "critical": Severity.critical,
    "very high": Severity.critical,
}


def coerce_confidence(raw: object, default: float = 1.0) -> float:
    """Safely convert a confidence value to a float between 0 and 1.

    Handles numeric floats/ints, numeric strings (``"0.8"``), and common
    descriptive strings (``"high"``, ``"low"``).  Unknown values fall back to
    *default*.
    """
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip().lower()
    if text in _CONFIDENCE_MAP:
        return _CONFIDENCE_MAP[text]
    # Try plain numeric conversion ("0.75", "1").
    text = re.sub(r"[^0-9.]", "", text)
    if text:
        try:
            value = float(text)
            return max(0.0, min(value, 1.0))
        except (ValueError, OverflowError):
            pass
    return default


def coerce_severity(raw: object, default: Severity = Severity.warning) -> Severity:
    """Safely convert raw severity values (e.g. 'high', 'medium', 'error') to a Severity enum."""
    text = str(raw).strip().lower()
    if text in _SEVERITY_MAP:
        return _SEVERITY_MAP[text]
    try:
        return Severity(text)
    except ValueError:
        return default


@dataclass
class AgentContext:
    gateway: LLMGateway
    settings: Settings
    run: ReviewRun


class BaseAgent:
    kind: AgentKind

    async def run(self, ctx: AgentContext, files: list[str] | None = None):
        raise NotImplementedError
