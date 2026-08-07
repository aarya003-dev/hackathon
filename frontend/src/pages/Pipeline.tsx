import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, ChevronRight, Inbox, RefreshCw } from 'lucide-react'
import { api } from '../api/client'
import type { RunStatus, RunSummary } from '../types'
import { formatRelative } from '../lib/status'
import StatusBadge from '../components/StatusBadge'

type Filter = 'all' | 'active' | 'completed' | 'failed' | 'hitl'

const FILTERS: { id: Filter; label: string }[] = [
  { id: 'all', label: 'All Reviews' },
  { id: 'active', label: 'Active' },
  { id: 'completed', label: 'Completed' },
  { id: 'failed', label: 'Failed' },
  { id: 'hitl', label: 'HITL Required' },
]

const ACTIVE: RunStatus[] = ['queued', 'running', 'waiting_hitl']

function matches(run: RunSummary, filter: Filter): boolean {
  switch (filter) {
    case 'all':
      return true
    case 'active':
      return ACTIVE.includes(run.status)
    case 'completed':
      return run.status === 'succeeded'
    case 'failed':
      return run.status === 'failed'
    case 'hitl':
      return run.status === 'waiting_hitl' || run.hitl_pending > 0
  }
}

const GLYPH_COLORS = [
  'bg-cyan-500/15 text-cyan-300',
  'bg-violet-500/15 text-violet-300',
  'bg-emerald-500/15 text-emerald-300',
  'bg-amber-500/15 text-amber-300',
  'bg-rose-500/15 text-rose-300',
  'bg-sky-500/15 text-sky-300',
]

function RepoGlyph({ name }: { name: string }) {
  const index = [...name].reduce((sum, char) => sum + char.charCodeAt(0), 0) % GLYPH_COLORS.length
  return (
    <span
      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-sm font-semibold uppercase ${GLYPH_COLORS[index]}`}
    >
      {name.slice(0, 1)}
    </span>
  )
}

export default function Pipeline() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<Filter>('all')

  const refresh = useCallback(() => {
    api
      .listRuns()
      .then(setRuns)
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load reviews'),
      )
  }, [])

  useEffect(() => {
    refresh()
    const timer = window.setInterval(refresh, 4000)
    return () => window.clearInterval(timer)
  }, [refresh])

  const live = runs?.some((run) => ACTIVE.includes(run.status))
  const counts = (id: Filter) => (runs ? runs.filter((run) => matches(run, id)).length : 0)
  const visible = runs?.filter((run) => matches(run, filter)) ?? []

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Review pipeline</h2>
          <p className="text-sm text-slate-500">
            Multi-agent pull-request reviews ingested from the local Git adapter.
          </p>
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
          <span>Cannot reach the backend: {error}. Is the API running on port 8000?</span>
        </div>
      )}

      {runs !== null && runs.length > 0 && (
        <>
          {live && (
            <p className="flex items-center gap-1.5 text-xs text-cyan-300">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />
              Live — refreshing every 4s
            </p>
          )}
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                onClick={() => setFilter(id)}
                className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                  filter === id
                    ? 'glow-accent border-accent/50 bg-accent-soft text-accent'
                    : 'border-edge bg-panel text-slate-400 hover:text-slate-200'
                }`}
              >
                {label}
                <span
                  className={`rounded-full px-1.5 text-[10px] tabular-nums ${
                    filter === id ? 'bg-accent/20 text-accent' : 'bg-slate-700/50 text-slate-400'
                  }`}
                >
                  {counts(id)}
                </span>
              </button>
            ))}
          </div>
        </>
      )}

      {runs === null && !error ? (
        <div className="flex items-center justify-center rounded-xl border border-edge bg-panel py-20 text-sm text-slate-500">
          Loading reviews…
        </div>
      ) : null}

      {runs !== null && runs.length === 0 && (
        <div className="rounded-xl border border-edge bg-panel px-6 py-16 text-center">
          <Inbox size={32} className="mx-auto mb-3 text-slate-600" />
          <p className="text-sm font-medium text-slate-200">No reviews yet</p>
          <p className="mx-auto mt-1 max-w-md text-xs text-slate-500">
            Ingest a local Git push (via <code>scripts/watch_repo.py</code> or the
            bare-repo hook), click{' '}
            <span className="text-accent">New Analysis</span> in the sidebar, or run{' '}
            <code>python backend/scripts/seed_demo.py</code> to populate the pipeline.
          </p>
        </div>
      )}

      {runs !== null && runs.length > 0 && visible.length === 0 && (
        <div className="rounded-xl border border-edge bg-panel px-6 py-12 text-center text-sm text-slate-500">
          No reviews match this filter.
        </div>
      )}

      {visible.length > 0 && (
        <div className="space-y-3">
          {visible.map((run) => (
            <Link
              key={run.id}
              to={`/runs/${run.id}`}
              className="group flex items-start gap-4 rounded-xl border border-edge bg-panel p-4 transition-colors hover:border-accent/40 hover:bg-panel-2"
            >
              <RepoGlyph name={run.repository} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <StatusBadge status={run.status} />
                  <span className="text-sm font-medium text-slate-100">{run.repository}</span>
                  <span className="font-mono text-xs text-accent">{run.commit}</span>
                </div>
                {run.summary && (
                  <p className="mt-1 line-clamp-1 text-xs text-slate-400">{run.summary}</p>
                )}
                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-500">
                  <span>
                    {run.findings} finding{run.findings === 1 ? '' : 's'}
                  </span>
                  {run.hitl_pending > 0 && (
                    <span className="text-amber-300">
                      {run.hitl_pending} awaiting human review
                    </span>
                  )}
                  <span>{formatRelative(run.updated_at)}</span>
                </div>
              </div>
              <ChevronRight
                size={18}
                className="mt-2 shrink-0 text-slate-600 transition-colors group-hover:text-accent"
              />
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
