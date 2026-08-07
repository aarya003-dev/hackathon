"""Review-output publication adapters.

The orchestrator synthesizes a summary and then routes findings through a Git
provider adapter. For local demos and tests the adapter is a dry run that only
records what would have been posted — no repository, network, or credentials
are involved. A real Git provider (e.g. GitHub review-comment API) replaces it
behind the same ``GitPublisher`` interface.
"""

from __future__ import annotations

from typing import Any, Protocol

from ..config import Settings
from ..domain.models import ReviewRun


class GitPublisher(Protocol):
    def publish(self, run: ReviewRun) -> dict[str, Any]:
        """Persist review output to a repository; returns publication metadata."""


class DryRunPublisher:
    """Records the comments that would be posted; never touches a repository."""

    def __init__(self, target: str | None = None) -> None:
        self.target = target
        self.comments: list[dict[str, Any]] = []

    def publish(self, run: ReviewRun) -> dict[str, Any]:
        # Default target reflects the reviewed repository, not a placeholder.
        target = self.target or f"dry-run://{run.repository.name}"
        comments = [
            {
                "file_path": finding.file_path,
                "line_start": finding.line_start,
                "severity": finding.severity.value,
                "message": finding.message,
                "suggestion": finding.suggestion,
            }
            for finding in run.findings
        ]
        self.comments.extend(comments)
        return {
            "provider": "dry_run",
            "target": target,
            "status": "published",
            "posted": len(comments),
        }


def create_publisher(settings: Settings) -> GitPublisher | None:
    """Build the active output adapter (``none`` disables publication)."""
    if settings.publish_mode == "none":
        return None
    return DryRunPublisher()
