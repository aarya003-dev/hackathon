import { useEffect, useRef } from 'react'
import { api } from '../api/client'
import type { RunEvent } from '../types'

const EVENT_TYPES = [
  'run.queued',
  'run.started',
  'agent.started',
  'agent.completed',
  'agent.failed',
  'hitl.required',
  'hitl.resolved',
  'review.completed',
  'run.failed',
]

/**
 * Subscribe to the run's SSE stream. EventSource auto-reconnects on dropped
 * connections; the backend also replays recent events on (re)connect, so a
 * late-joining page still sees the run's progress.
 *
 * When the run reaches a terminal state the stream closes; disable via
 * `enabled` to stop the reconnect churn.
 */
export function useRunEvents(
  runId: string | null | undefined,
  onEvent: (event: RunEvent) => void,
  enabled: boolean,
): void {
  const handlerRef = useRef(onEvent)
  handlerRef.current = onEvent

  useEffect(() => {
    if (!runId || !enabled) return

    const source = new EventSource(api.eventsUrl(runId))
    const handlers = new Map<string, (event: MessageEvent<string>) => void>()

    const register = (type: string): void => {
      const listener = (message: MessageEvent<string>) => {
        try {
          handlerRef.current({ ...(JSON.parse(message.data) as RunEvent), event_type: type })
        } catch {
          // Ignore malformed frames; the poll fallback keeps the page correct.
        }
      }
      handlers.set(type, listener)
      source.addEventListener(type, listener)
    }

    EVENT_TYPES.forEach(register)

    return () => {
      handlers.forEach((listener, type) => source.removeEventListener(type, listener))
      source.close()
    }
  }, [runId, enabled])
}
