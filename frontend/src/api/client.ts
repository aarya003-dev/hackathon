import type { DecisionResult, RunDetail, RunSummary } from '../types'

/**
 * Typed REST client for the backend. In dev, Vite proxies `/api` to the
 * FastAPI server (see vite.config.ts); in production the dashboard and API
 * are expected to share an origin or be CORS-configured.
 */
const BASE = '/api/v1'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init)
  if (!response.ok) {
    const detail = await response.text()
    throw new ApiError(response.status, detail || `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const api = {
  listRuns: () => request<RunSummary[]>('/runs'),
  getRun: (runId: string) => request<RunDetail>(`/runs/${runId}`),
  decide: (approvalId: string, body: { decision: 'approve' | 'reject'; by: string }) =>
    request<DecisionResult>(`/hitl/${approvalId}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  /** SSE stream URL for a run (consumed via EventSource). */
  eventsUrl: (runId: string) => `${BASE}/runs/${runId}/events`,
}
