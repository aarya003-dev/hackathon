"""Review run orchestrator: the DAG state machine.

    queued → running → triage → (core ∥ security) → HITL gate if needed
                        → summarizer → succeeded | failed

Persists every transition, publishes events to the SSE bus, and pauses at
``waiting_hitl`` until an authorized approval/rejection decision resumes it.
"""

from __future__ import annotations

import asyncio
import time
from uuid import uuid4

from ..agents.base import AgentContext
from ..agents.core_review import CoreReviewAgent
from ..agents.security import SecurityAgent
from ..agents.suggestion import SuggestionAgent
from ..agents.summarizer import SummarizerAgent
from ..agents.triage import TriageAgent
from ..config import Settings
from ..domain.models import (
    AgentKind,
    Finding,
    HitlApproval,
    NodeStatus,
    ReviewRun,
    RunEvent,
    RunStatus,
)
from ..integrations.publisher import GitPublisher
from ..persistence.base import RunRepository
from ..rag.service import RagService
from ..services.event_bus import EventBus
from ..services.llm_gateway import LLMGateway

_TERMINAL_EVENTS = ("review.completed", "run.failed")
_RAG_TOP_K = 3


def _format_rag_hits(hits: list) -> str:
    return "\n".join(
        f"- [{hit.metadata.get('source_type', 'guideline')}] "
        f"{hit.metadata.get('path', '')}: {hit.metadata.get('content', '').strip()}"
        for hit in hits
    )


class ReviewOrchestrator:
    def __init__(
        self,
        repo: RunRepository,
        bus: EventBus,
        gateway: LLMGateway,
        settings: Settings,
        rag: RagService | None = None,
        publisher: GitPublisher | None = None,
    ) -> None:
        self.repo = repo
        self.bus = bus
        self.settings = settings
        self.gateway = gateway
        self.rag = rag
        self.publisher = publisher
        self.triage = TriageAgent()
        self.core = CoreReviewAgent()
        self.security = SecurityAgent()
        self.suggestion = SuggestionAgent()
        self.summarizer = SummarizerAgent()
        self._tasks: set[asyncio.Task] = set()

    def enqueue(self, run_id: str) -> None:
        """Start the review in the background without blocking the request."""
        task = asyncio.create_task(self.run_review(run_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def run_review(self, run_id: str) -> None:
        run = self.repo.get_run(run_id)
        if run is None:
            return
        run.status = RunStatus.running
        self._persist(run, "run.started")

        try:
            # 1. Triage routes files to the specialized agents.
            self._node(run, AgentKind.triage, NodeStatus.running)
            routing = await self.triage.run(self._ctx(run))
            self._node(run, AgentKind.triage, NodeStatus.success)

            core_files = routing.get("core") or run.commit.files
            security_files = routing.get("security") or run.commit.files
            suggestion_files = routing.get("suggestion") or run.commit.files

            # 1b. Retrieve relevant guidance for the specialized agents.
            rag_context = self._retrieve_rag_context(run)

            # 2. Core review, security, and suggestion agents run in parallel.
            #    return_exceptions=True so a failure in one agent does not
            #    cancel the other — partial results are still useful.
            self._node(run, AgentKind.core, NodeStatus.running)
            self._node(run, AgentKind.security, NodeStatus.running)
            self._node(run, AgentKind.suggestion, NodeStatus.running)
            core_result, security_result, suggestion_result = await asyncio.gather(
                self.core.run(self._ctx(run), core_files, rag_context),
                self.security.run(self._ctx(run), security_files, rag_context),
                self.suggestion.run(self._ctx(run), suggestion_files, rag_context),
                return_exceptions=True,
            )
            core_findings = core_result if isinstance(core_result, list) else []
            security_findings = (
                security_result if isinstance(security_result, list) else []
            )
            suggestion_findings = (
                suggestion_result if isinstance(suggestion_result, list) else []
            )
            errors: list[str] = []
            if isinstance(core_result, BaseException):
                errors.append(f"core review: {core_result}")
                self._node(run, AgentKind.core, NodeStatus.failed)
            else:
                self._node(run, AgentKind.core, NodeStatus.success)
            if isinstance(security_result, BaseException):
                errors.append(f"security: {security_result}")
                self._node(run, AgentKind.security, NodeStatus.failed)
            else:
                self._node(run, AgentKind.security, NodeStatus.success)
            if isinstance(suggestion_result, BaseException):
                errors.append(f"suggestion: {suggestion_result}")
                self._node(run, AgentKind.suggestion, NodeStatus.failed)
            else:
                self._node(run, AgentKind.suggestion, NodeStatus.success)
            if errors:
                run.error = "; ".join(errors)
            run.findings = core_findings + security_findings + suggestion_findings

            # 3. HITL gate: pause if any finding needs a human decision.
            pending = [finding for finding in run.findings if finding.requires_hitl]
            if pending:
                self._node(run, AgentKind.security, NodeStatus.paused)
                run = await self._request_hitl(run, pending)
                self._apply_hitl_decisions(run)
                self._node(run, AgentKind.security, NodeStatus.success)

            # 4. Synthesize the summary.
            self._node(run, AgentKind.summarizer, NodeStatus.running)
            run.summary = await self.summarizer.run(self._ctx(run))
            self._node(run, AgentKind.summarizer, NodeStatus.success)

            # 5. Route findings to the repository (dry-run in the demo).
            if self.publisher is not None:
                run.publication = self.publisher.publish(run)

            run.status = RunStatus.succeeded
            self._persist(run, "review.completed")
        except Exception as exc:  # noqa: BLE001 - terminal failure state
            run.status = RunStatus.failed
            run.error = str(exc)
            for agent, node in run.nodes.items():
                if node == NodeStatus.running:
                    run.nodes[agent] = NodeStatus.failed
            self._persist(run, "run.failed")

    # -- internals ---------------------------------------------------------

    def _ctx(self, run: ReviewRun) -> AgentContext:
        return AgentContext(gateway=self.gateway, settings=self.settings, run=run)

    def _retrieve_rag_context(self, run: ReviewRun) -> str:
        """Query guidelines/history for this change; empty when RAG is off."""
        if self.rag is None:
            return ""
        query = f"{run.commit.message} {' '.join(run.commit.files)}"
        hits = self.rag.search(query, k=_RAG_TOP_K)
        return _format_rag_hits(hits)

    def _node(self, run: ReviewRun, agent: AgentKind, status: NodeStatus) -> None:
        run.nodes[agent] = status
        event_type = (
            "agent.started"
            if status == NodeStatus.running
            else "agent.failed"
            if status == NodeStatus.failed
            else "agent.completed"
        )
        self._persist(run, event_type, agent, {"status": status.value})

    async def _request_hitl(self, run: ReviewRun, findings: list[Finding]) -> ReviewRun:
        """Pause at ``waiting_hitl`` until every approval is decided.

        Polls the repository rather than relying on an in-loop notification,
        so a decision arriving from a different event-loop/thread still
        resumes the run.
        """
        run.status = RunStatus.waiting_hitl
        for finding in findings:
            run.approvals.append(
                HitlApproval(id=uuid4().hex, run_id=run.id, finding_id=finding.id)
            )
        self._persist(
            run, "hitl.required", AgentKind.security, {"findings": len(findings)}
        )

        while True:
            latest = self.repo.get_run(run.id)
            if latest is None:
                return run
            pending = [
                approval
                for approval in latest.approvals
                if approval.status == "pending"
            ]
            if not pending:
                return latest
            await asyncio.sleep(0.1)

    def _apply_hitl_decisions(self, run: ReviewRun) -> None:
        rejected = {
            approval.finding_id
            for approval in run.approvals
            if approval.status == "rejected"
        }
        run.findings = [
            finding for finding in run.findings if finding.id not in rejected
        ]

    def _persist(
        self,
        run: ReviewRun,
        event_type: str,
        agent: AgentKind | None = None,
        payload: dict | None = None,
    ) -> None:
        run.updated_at = time.time()
        self.repo.update_run(run)
        self.bus.publish(
            RunEvent(
                run_id=run.id, event_type=event_type, agent=agent, payload=payload or {}
            )
        )
