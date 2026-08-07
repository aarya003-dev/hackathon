import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, ChevronRight, GitBranch, Inbox, RefreshCw } from 'lucide-react'
import { api } from '../api/client'
import type { RunSummary } from '../types'
import { formatRelative } from '../lib/status'
import StatusBadge from '../components/StatusBadge'
import { DashboardMetrics } from '../components/Metrics'

export default function Dashboard() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

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

  const live = runs?.some(
    (run) =>
      run.status === 'queued' || run.status === 'running' || run.status === 'waiting_hitl',
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Review runs</h2>
          <p className="text-sm text-slate-500">
            Multi-agent pull-request reviews ingested from the local Git adapter.
          </p>
        </div>
        <button
          type="button"
          onClick={refresh}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <AlertCircle size={16} />
          <span>
            Cannot reach the backend: {error}. Is the API running on port 8000?
          </span>
        </div>
      )}

      {runs !== null && runs.length > 0 && (
        <>
          {live && (
            <p className="text-xs text-blue-600">● Live — refreshing every 4s</p>
          )}
          <DashboardMetrics runs={runs} />
        </>
      )}

      {runs === null && !error ? (
        <div className="flex items-center justify-center rounded-xl border border-slate-200 bg-white py-20 text-sm text-slate-400">
          Loading reviews…
        </div>
      ) : null}

      {runs !== null && runs.length === 0 && (
        <div className="rounded-xl border border-slate-200 bg-white px-6 py-16 text-center">
          <Inbox size={32} className="mx-auto mb-3 text-slate-300" />
          <p className="text-sm font-medium text-slate-700">No reviews yet</p>
          <p className="mx-auto mt-1 max-w-md text-xs text-slate-500">
            Ingest a local Git push (via <code>scripts/watch_repo.py</code> or the
            bare-repo hook) or run <code>python backend/scripts/seed_demo.py</code>{' '}
            to populate the dashboard.
          </p>
        </div>
      )}

      {runs !== null && runs.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2.5">Status</th>
                <th className="px-4 py-2.5">Repository</th>
                <th className="px-4 py-2.5">Commit</th>
                <th className="px-4 py-2.5 text-right">Findings</th>
                <th className="px-4 py-2.5 text-right">HITL</th>
                <th className="px-4 py-2.5">Updated</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr
                  key={run.id}
                  className="border-b border-slate-100 last:border-0 hover:bg-slate-50"
                >
                  <td className="px-4 py-3">
                    <StatusBadge status={run.status} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5 font-medium text-slate-800">
                      <GitBranch size={14} className="text-slate-400" />
                      {run.repository}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs text-slate-600">{run.commit}</span>
                    {run.hitl_pending > 0 && (
                      <span className="ml-2 text-xs text-amber-700">• paused</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs text-slate-600">
                    {run.findings}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs text-amber-700">
                    {run.hitl_pending > 0 ? run.hitl_pending : '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {formatRelative(run.updated_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      to={`/runs/${run.id}`}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100"
                    >
                      View <ChevronRight size={13} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
