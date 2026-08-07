import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  AlertCircle,
  ArrowLeft,
  Clock,
  GitCommitHorizontal,
  GitFork,
  Loader2,
  Sparkles,
  User,
} from 'lucide-react'
import { api } from '../api/client'
import type { RunDetail } from '../types'
import { formatRelative, formatTime } from '../lib/status'
import { useRunEvents } from '../hooks/useRunEvents'
import StatusBadge from '../components/StatusBadge'
import DAGView from '../components/DAGView'
import { FindingMetrics } from '../components/Metrics'
import FindingList from '../components/FindingList'
import HitlPanel from '../components/HitlPanel'
import DiffViewer from '../components/DiffViewer'

export default function ReviewDetail() {
  const { runId } = useParams<{ runId: string }>()
  const [run, setRun] = useState<RunDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [revision, setRevision] = useState(0)
  const [reviewer, setReviewer] = useState('operator')

  const refresh = useCallback(() => {
    if (!runId) return
    let cancelled = false
    api
      .getRun(runId)
      .then((data) => {
        if (!cancelled) {
          setRun(data)
          setError(null)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load run')
      })
    return () => {
      cancelled = true
    }
  }, [runId])

  useEffect(() => {
    const cancel = refresh()
    return cancel
  }, [refresh, revision])

  const nonTerminal =
    run !== null &&
    (run.status === 'queued' || run.status === 'running' || run.status === 'waiting_hitl')

  // Live updates: SSE events + a 2s fallback poll while the run is active.
  useRunEvents(runId, () => setRevision((value) => value + 1), nonTerminal)

  useEffect(() => {
    if (!nonTerminal) return
    const timer = window.setInterval(() => setRevision((value) => value + 1), 2000)
    return () => window.clearInterval(timer)
  }, [nonTerminal])

  if (error && run === null) {
    return (
      <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-10 text-center text-sm text-rose-300">
        <AlertCircle size={20} className="mx-auto mb-2" />
        {error}
      </div>
    )
  }

  if (run === null) {
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-sm text-slate-400">
        <Loader2 size={16} className="animate-spin" />
        Loading run…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Link
        to="/"
        className="inline-flex items-center gap-1 text-sm font-medium text-slate-400 hover:text-slate-200"
      >
        <ArrowLeft size={15} /> All reviews
      </Link>

      {/* Header */}
      <div className="rounded-xl border border-edge bg-panel p-4">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="font-mono text-lg font-semibold text-slate-100">
            {run.id.slice(0, 12)}
          </h2>
          <StatusBadge status={run.status} />
          {nonTerminal && (
            <span className="inline-flex items-center gap-1 text-xs text-cyan-300">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-400" />
              live
            </span>
          )}
          {run.error && (
            <span className="inline-flex items-center gap-1 text-xs text-rose-400">
              <AlertCircle size={12} /> {run.error}
            </span>
          )}
        </div>

        <div className="mt-3 grid gap-2 text-sm text-slate-400 sm:grid-cols-2">
          <span className="flex items-center gap-1.5">
            <GitFork size={14} className="text-slate-500" />
            {run.repository.name}
            <span className="text-slate-600">/</span>
            <span className="font-mono text-xs text-slate-500">{run.provider}</span>
          </span>
          <span className="flex items-center gap-1.5">
            <GitCommitHorizontal size={14} className="text-slate-500" />
            <span className="font-mono text-xs text-accent">
              {run.commit.base_sha.slice(0, 8)}…{run.commit.sha.slice(0, 8)}
            </span>
          </span>
          <span className="flex items-center gap-1.5">
            <User size={14} className="text-slate-500" />
            {run.commit.author ?? 'unknown author'}
          </span>
          <span className="flex items-center gap-1.5">
            <Clock size={14} className="text-slate-500" />
            {formatTime(run.created_at)} · updated {formatRelative(run.updated_at)}
          </span>
        </div>

        {run.commit.message && (
          <p className="mt-2 rounded-lg bg-[#0b0d12] px-3 py-2 font-mono text-xs text-slate-300">
            {run.commit.message}
          </p>
        )}
      </div>

      {/* Summary */}
      <div className="rounded-xl border border-edge bg-panel p-4">
        <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
          <Sparkles size={13} /> Summary
        </h3>
        {run.summary ? (
          <p className="mt-2 whitespace-pre-wrap text-sm text-slate-200">{run.summary}</p>
        ) : run.status === 'succeeded' ? (
          <p className="mt-2 text-sm text-slate-500">No summary generated.</p>
        ) : (
          <p className="mt-2 text-sm text-slate-500">
            Summary will be generated after the review completes.
          </p>
        )}
        {run.publication && run.publication.status === 'published' && (
          <p className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-2 py-1 text-xs text-emerald-300">
            <GitCommitHorizontal size={12} />
            Dry-run published {String(run.publication.posted ?? 0)} comment
            {run.publication.posted === 1 ? '' : 's'} to{' '}
            <span className="font-mono">{String(run.publication.target ?? '')}</span>
          </p>
        )}
      </div>

      {/* DAG */}
      <section>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Agent pipeline
        </h3>
        <DAGView nodes={run.nodes} />
      </section>

      {/* HITL */}
      {run.status === 'waiting_hitl' && (
        <HitlPanel
          approvals={run.approvals}
          findings={run.findings}
          reviewer={reviewer}
          onReviewerChange={setReviewer}
          onDecision={() => setRevision((value) => value + 1)}
        />
      )}

      {/* Findings + metrics */}
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <FindingMetrics findings={run.findings} runStatus={run.status} />
        <FindingList findings={run.findings} runStatus={run.status} />
      </div>

      {/* Diff */}
      <section>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Changed files
        </h3>
        <DiffViewer diff={run.commit.diff} findings={run.findings} />
      </section>
    </div>
  )
}
