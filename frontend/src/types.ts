/**
 * Frontend mirror of the backend domain schemas (backend/app/domain/*).
 * Keep these in sync with the REST + SSE contracts; the dashboard treats the
 * backend as the system of record.
 */

export type RunStatus =
  | 'queued'
  | 'running'
  | 'waiting_hitl'
  | 'succeeded'
  | 'failed'

export type NodeStatus = 'idle' | 'running' | 'success' | 'failed' | 'paused'

export type Severity = 'info' | 'warning' | 'error' | 'critical'

export type ApprovalStatus = 'pending' | 'approved' | 'rejected'

export type AgentId = 'triage' | 'core_review' | 'security' | 'suggestion' | 'summarizer'

export interface RepositoryInfo {
  name: string
  owner: string | null
  path: string
  clone_url: string | null
}

export interface CommitRef {
  sha: string
  base_sha: string
  message: string
  author: string | null
  files: string[]
  diff: string
}

export interface Finding {
  id: string
  agent: AgentId
  severity: Severity
  category: string
  file_path: string
  line_start: number | null
  line_end: number | null
  message: string
  suggestion: string
  confidence: number
  requires_hitl: boolean
}

export interface Approval {
  id: string
  run_id: string
  finding_id: string
  status: ApprovalStatus
  requested_at: number
  decided_at: number | null
  decided_by: string | null
}

/** Shallow row used by GET /api/v1/runs (list). */
export interface RunSummary {
  id: string
  status: RunStatus
  repository: string
  commit: string
  base_sha: string
  findings: number
  hitl_pending: number
  summary: string
  created_at: number
  updated_at: number
}

/** Full run from GET /api/v1/runs/{id} (includes hitl_pending computed). */
export interface RunDetail {
  id: string
  provider: string
  repository: RepositoryInfo
  commit: CommitRef
  status: RunStatus
  nodes: Record<AgentId, NodeStatus>
  findings: Finding[]
  approvals: Approval[]
  summary: string
  publication: Record<string, unknown> | null
  error: string | null
  created_at: number
  updated_at: number
  hitl_pending: number
}

/** SSE event payload from GET /api/v1/runs/{id}/events. */
export interface RunEvent {
  run_id: string
  event_type: string
  agent: AgentId | null
  payload: Record<string, unknown>
  at: number
}

export interface DecisionResult {
  status: ApprovalStatus
  run_id: string
}
