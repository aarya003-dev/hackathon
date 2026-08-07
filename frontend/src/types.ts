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

export type AgentId = 'triage' | 'core_review' | 'security' | 'summarizer'

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
  /**
   * Structured AI summary from the summarizer agent. `summary` keeps the
   * plain-text narrative; this holds the bullet sections shown on the AI
   * Review Summary page. Absent for runs summarized before the field existed.
   */
  summary_detail: SummaryDetail | null
  publication: Record<string, unknown> | null
  error: string | null
  created_at: number
  updated_at: number
  hitl_pending: number
}

/** Structured output of the summarizer agent (POST-run synthesis). */
export interface SummaryDetail {
  summary: string
  changes: string[]
  impact: string[]
  recommendations: string[]
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

/** Per-agent health aggregate from GET /api/v1/agents. */
export interface AgentStats {
  id: AgentId
  name: string
  role: string
  backend: string
  model: string
  latest_status: NodeStatus
  runs: number
  success_rate: number
  successes: number
  failures: number
  findings: number
  hitl: number
}

/** Read-only gateway/config snapshot returned alongside agent stats. */
export interface SystemConfig {
  llm_backend: string
  ingestion_source: string
  publish_mode: string
  gateway_url: string
  models: Record<string, string>
}

export interface AgentsResponse {
  agents: AgentStats[]
  config: SystemConfig
}

/** Result of POST /api/v1/ingest/analyze (on-demand "New Analysis"). */
export interface AnalyzeResult {
  accepted: boolean
  duplicate: boolean
  run_id: string
  commit?: string
  event?: string
}
