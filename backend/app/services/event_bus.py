"""In-process event bus backing the SSE endpoint.

Events are stored per run (replay for late subscribers) and pushed to live
subscriber queues. Suitable for the single-process Phase 3 slice; swap for a
distributed bus (Redis Streams, etc.) when scaling out.
"""

from __future__ import annotations

import asyncio

from ..domain.models import RunEvent


class EventBus:
    def __init__(self) -> None:
        self._history: dict[str, list[RunEvent]] = {}
        self._subscribers: dict[str, list[asyncio.Queue[RunEvent]]] = {}

    def publish(self, event: RunEvent) -> None:
        self._history.setdefault(event.run_id, []).append(event)
        for queue in self._subscribers.get(event.run_id, []):
            queue.put_nowait(event)

    def subscribe(self, run_id: str) -> asyncio.Queue[RunEvent]:
        queue: asyncio.Queue[RunEvent] = asyncio.Queue()
        for event in self._history.get(run_id, []):
            queue.put_nowait(event)
        self._subscribers.setdefault(run_id, []).append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue[RunEvent]) -> None:
        try:
            self._subscribers.get(run_id, []).remove(queue)
        except ValueError:
            pass

    async def stream(self, run_id: str):
        """Async iterator over an event stream (replay history, then live).

        Ends when the run reaches a terminal event. Emits a keepalive ``ping``
        if the stream would otherwise sit idle.
        """
        queue = self.subscribe(run_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield RunEvent(run_id=run_id, event_type="ping")
                    continue
                yield event
                if event.event_type in ("review.completed", "run.failed"):
                    break
        finally:
            self.unsubscribe(run_id, queue)
