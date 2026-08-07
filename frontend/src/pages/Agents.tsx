import { useCallback, useEffect, useState } from 'react'
import {
  AlertCircle,
  Bot,
  Code2,
  GitBranch,
  RefreshCw,
  Server,
  ShieldAlert,
  Sparkles,
  type LucideIcon,
} from 'lucide-react'
import { api } from '../api/client'
import type { AgentId, AgentStats, NodeStatus, SystemConfig } from '../types'

const AGENT_ICON: Record<AgentId, LucideIcon> = {
  triage: GitBranch,
  core_review: Code2,
  security: ShieldAlert,
  summarizer: Sparkles,
}

const NODE_META: Record<NodeStatus, { label: string; dot: string; text: string }> = {
  idle: { label: 'Idle', dot: 'bg-slate-500', text: 'text-slate-400' },
  running: { label: 'Running', dot: 'bg-cyan-400', text: 'text-cyan-300' },
  success: { label: 'Active', dot: 'bg-emerald-400', text: 'text-emerald-300' },
  failed: { label: 'Failing', dot: 'bg-rose-400', text: 'text-rose-300' },
  paused: { label: 'Paused · HITL', dot: 'bg-amber-400', text: 'text-amber-300' },
}

function AgentCard({ agent }: { agent: AgentStats }) {
  const Icon = AGENT_ICON[agent.id]
  const meta = NODE_META[agent.latest_status]
  return (
    <div className="rounded-xl border border-edge bg-panel p-4">
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
          <Icon size={22} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-100">{agent.name}</h3>
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                agent.latest_status === 'success' ||
                agent.latest_status === 'running'
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                  : agent.latest_status === 'failed'
                    ? 'border-rose-500/40 bg-rose-500/10 text-rose-300'
                    : agent.latest_status === 'paused'
                      ? 'border-amber-500/40 bg-amber-500/10 text-amber-300'
                      : 'border-slate-600/50 bg-slate-800/50 text-slate-300'
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
              {meta.label}
            </span>
          </div>
          <p className="mt-0.5 text-xs text-slate-500">{agent.role}</p>
        </div>
      </div>

      <div className="mt-3 space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <span className="text-slate-500">Model</span>
          <span className="max-w-[60%] truncate font-mono text-slate-300">{agent.model}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-500">Backend</span>
          <span className="font-mono text-accent">{agent.backend}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-500">Success rate</span>
          <span className="font-mono text-slate-300">
            {agent.runs === 0 ? '—' : `${Math.round(agent.success_rate * 100)}%`}
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-slate-700/50">
          <div
            className="h-full rounded-full bg-emerald-400"
            style={{ width: `${Math.round(agent.success_rate * 100)}%` }}
          />
        </div>
      </div>

      <div className="mt-3 grid grid-cols-4 gap-2 border-t border-edge pt-3 text-center">
        <div>
          <div className="font-mono text-base font-semibold text-slate-100">{agent.runs}</div>
          <div className="text-[10px] uppercase tracking-wider text-slate-600">Runs</div>
        </div>
        <div>
          <div className="font-mono text-base font-semibold text-emerald-400">
            {agent.successes}
          </div>
          <div className="text-[10px] uppercase tracking-wider text-slate-600">Passed</div>
        </div>
        <div>
          <div className="font-mono text-base font-semibold text-amber-300">{agent.findings}</div>
          <div className="text-[10px] uppercase tracking-wider text-slate-600">Findings</div>
        </div>
        <div>
          <div className="font-mono text-base font-semibold text-rose-400">{agent.hitl}</div>
          <div className="text-[10px] uppercase tracking-wider text-slate-600">HITL</div>
        </div>
      </div>
    </div>
  )
}

function ConfigPanel({ config }: { config: SystemConfig }) {
  const rows: [string, string][] = [
    ['LLM backend', config.llm_backend],
    ['Ingestion source', config.ingestion_source],
    ['Publish mode', config.publish_mode],
    ['Gateway', config.gateway_url],
    ...Object.entries(config.models).map(
      ([key, value]) => [`Model · ${key}`, value] as [string, string],
    ),
  ]
  return (
    <div className="rounded-xl border border-edge bg-panel p-4">
      <div className="flex items-center gap-2">
        <Server size={16} className="text-slate-500" />
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
          Runtime configuration
        </h3>
      </div>
      <div className="mt-3 divide-y divide-edge/60">
        {rows.map(([label, value]) => (
          <div key={label} className="flex items-center justify-between gap-4 py-2 text-xs">
            <span className="text-slate-500">{label}</span>
            <span className="max-w-[70%] truncate text-right font-mono text-slate-300">
              {value || '—'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Agents() {
  const [data, setData] = useState<{ agents: AgentStats[]; config: SystemConfig } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(() => {
    api
      .getAgents()
      .then(setData)
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load agents'),
      )
  }, [])

  useEffect(() => {
    refresh()
    const timer = window.setInterval(refresh, 8000)
    return () => window.clearInterval(timer)
  }, [refresh])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="glow-accent flex h-9 w-9 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <Bot size={18} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Agents</h2>
            <p className="text-sm text-slate-500">
              Health of the review agents across all runs.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={refresh}
          className="inline-flex items-center gap-1.5 rounded-lg border border-edge bg-panel px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-accent/40 hover:text-accent"
        >
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
          <AlertCircle size={16} />
          <span>Cannot reach the backend: {error}</span>
        </div>
      )}

      {data === null && !error ? (
        <div className="flex items-center justify-center rounded-xl border border-edge bg-panel py-20 text-sm text-slate-500">
          Loading agents…
        </div>
      ) : null}

      {data !== null && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2">
            {data.agents.map((agent) => (
              <AgentCard key={agent.id} agent={agent} />
            ))}
          </div>
          <ConfigPanel config={data.config} />
        </div>
      )}
    </div>
  )
}
