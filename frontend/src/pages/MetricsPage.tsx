import { useCallback, useEffect, useState } from 'react'
import { Activity, AlertCircle, RefreshCw } from 'lucide-react'
import { api } from '../api/client'
import type { RunSummary } from '../types'
import { DashboardMetrics, RunFeed } from '../components/Metrics'

export default function MetricsPage() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(() => {
    api
      .listRuns()
      .then(setRuns)
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load metrics'),
      )
  }, [])

  useEffect(() => {
    refresh()
    const timer = window.setInterval(refresh, 4000)
    return () => window.clearInterval(timer)
  }, [refresh])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="glow-accent flex h-9 w-9 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <Activity size={18} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Global metrics</h2>
            <p className="text-sm text-slate-500">
              Throughput and health across every review run.
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

      {runs === null && !error ? (
        <div className="flex items-center justify-center rounded-xl border border-edge bg-panel py-20 text-sm text-slate-500">
          Loading metrics…
        </div>
      ) : null}

      {runs !== null && (
        <div className="space-y-6">
          <DashboardMetrics runs={runs} />
          <section>
            <div className="mb-3 flex items-center gap-2">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
                Live run feed
              </h3>
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />
            </div>
            {runs.length === 0 ? (
              <div className="rounded-xl border border-edge bg-panel px-6 py-12 text-center text-sm text-slate-500">
                No runs yet — ingest a push or click New Analysis.
              </div>
            ) : (
              <RunFeed runs={runs} />
            )}
          </section>
        </div>
      )}
    </div>
  )
}
