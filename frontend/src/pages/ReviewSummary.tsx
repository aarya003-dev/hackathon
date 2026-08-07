import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  AlertCircle,
  ArrowLeft,
  Clock,
  Code2,
  Files,
  GitBranch,
  GitCommitHorizontal,
  GitFork,
  ListChecks,
  Loader2,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  User,
} from 'lucide-react'
import { api } from '../api/client'
import type { AgentId, RunDetail } from '../types'
import { formatRelative, formatTime, NODE_STATUS_STYLE } from '../lib/status'
import { useRunEvents } from '../hooks/useRunEvents'
import StatusBadge from '../components/StatusBadge'
import { FindingMetrics } from '../components/Metrics'

const PIPELINE: { id: AgentId; label: string; Icon: typeof GitBranch }[] = [
  { id: 'triage', label: 'Triage', Icon: GitBranch },
  { id: 'core_review', label: 'Core review', Icon: Code2 },
  { id: 'security', label: 'Security', Icon: ShieldAlert },
  { id: 'summarizer', label: 'Summarizer', Icon: Sparkles },
]

function BulletList({ items, empty }: { items: string[]; empty: string }) {
  if (!items.length) {
    return <p className="text-sm text-slate-500">{empty}</p>
  }
  return (
    <ul className="space-y-2">
      {items.map((item, index) => (
        <li key={index} className="flex items-start gap-2 text-sm text-slate-200">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
          <span className="min-w-0 whitespace-pre-wrap">{item}</span>
        </li>
      ))}
    </ul>
  )
}

function SectionCard({
  icon,
  title,
  children,
}: {
  icon: ReactNode
  title: string
  children: ReactNode
}) {
  return (
    <div className="rounded-xl border border-edge bg-panel p-4">
      <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
        {icon} {title}
      </h3>
      <div className="mt-3">{children}</div>
    </div>
  )
}

export default function ReviewSummary() {
  const { runId } = useParams<{ runId: string }>()
  const [run, setRun] = useState<RunDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [revision, setRevision] = useState(0)

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

  useRunEvents(runId, () => setRevision((value) => value + 1), nonTerminal)

  useEffect(() => {
    if (!nonTerminal) return
    const timer = window.setInterval(() => setRevision((value) => value + 1), 2000)
    return () => window.clearInterval(timer)
  }, [nonTerminal])

  const detail = run?.summary_detail
  const narrative = detail?.summary?.trim() || run?.summary?.trim() || ''
  const files = run?.commit.files ?? []

  const diffStats = useMemo(() => {
    const diff = run?.commit.diff ?? ''
    let added = 0
    let removed = 0
    for (const line of diff.split('\n')) {
      if (line.startsWith('+') && !line.startsWith('+++')) added += 1
      else if (line.startsWith('-') && !line.startsWith('---')) removed += 1
    }
    return { added, removed }
  }, [run?.commit.diff])

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
        Loading summary…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Link
        to={`/runs/${run.id}`}
        className="inline-flex items-center gap-1 text-sm font-medium text-slate-400 hover:text-slate-200"
      >
        <ArrowLeft size={15} /> Back to review
      </Link>

      {/* Header */}
      <div className="rounded-xl border border-edge bg-panel p-4">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-lg font-semibold text-slate-100">AI Review Summary</h2>
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
          <p className="mt-3 rounded-lg bg-[#0b0d12] px-3 py-2 font-mono text-xs text-slate-300">
            {run.commit.message}
          </p>
        )}
      </div>

      {/* AI narrative hero */}
      <div className="glow-accent rounded-xl border border-accent/30 bg-panel p-5">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-accent" />
          <h3 className="text-xs font-semibold uppercase tracking-wide text-accent">
            AI Summary
          </h3>
        </div>
        {narrative ? (
          <p className="mt-3 whitespace-pre-wrap text-[15px] leading-relaxed text-slate-100">
            {narrative}
          </p>
        ) : run.status === 'succeeded' ? (
          <p className="mt-3 text-sm text-slate-500">No summary generated for this review.</p>
        ) : (
          <p className="mt-3 text-sm text-slate-500">
            The AI summary will be generated once the review completes…
          </p>
        )}
      </div>

      {/* What changed / Impact */}
      <div className="grid gap-6 lg:grid-cols-2">
        <SectionCard icon={<Files size={13} />} title="What changed">
          {detail ? (
            <BulletList items={detail.changes} empty="The summarizer did not list any changes." />
          ) : (
            <BulletList
              items={files}
              empty="No changed files recorded for this run."
            />
          )}
          <div className="mt-4 rounded-lg border border-edge bg-panel-2 px-3 py-2.5 text-xs text-slate-400">
            <div className="flex items-center justify-between">
              <span>
                {files.length} file{files.length === 1 ? '' : 's'} ·{' '}
                <span className="font-mono text-emerald-400">+{diffStats.added}</span>{' '}
                <span className="font-mono text-rose-400">-{diffStats.removed}</span>
              </span>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {files.map((file) => (
                <span
                  key={file}
                  className="rounded border border-edge bg-[#0b0d12] px-1.5 py-0.5 font-mono text-[11px] text-slate-300"
                >
                  {file}
                </span>
              ))}
            </div>
          </div>
        </SectionCard>

        <SectionCard icon={<TrendingUp size={13} />} title="Impact">
          {detail ? (
            <BulletList
              items={detail.impact}
              empty="The summarizer did not flag any impact."
            />
          ) : (
            <p className="text-sm text-slate-500">
              Impact notes will appear once the review has been summarized.
            </p>
          )}
          <div className="mt-4">
            <FindingMetrics findings={run.findings} runStatus={run.status} />
          </div>
        </SectionCard>
      </div>

      {/* What happened: agent pipeline */}
      <SectionCard icon={<GitBranch size={13} />} title="What happened">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {PIPELINE.map(({ id, label, Icon }) => {
            const status = run.nodes[id] ?? 'idle'
            const style = NODE_STATUS_STYLE[status]
            return (
              <div
                key={id}
                className="flex items-center gap-2.5 rounded-lg border border-edge bg-panel-2 px-3 py-2.5"
              >
                <Icon size={16} style={{ color: style.dot }} />
                <div className="min-w-0">
                  <div className="truncate text-xs font-medium text-slate-200">{label}</div>
                  <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-slate-500">
                    <span
                      className="h-1.5 w-1.5 rounded-full"
                      style={{ background: style.dot }}
                    />
                    {status}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </SectionCard>

      {/* Recommendations */}
      <SectionCard icon={<ListChecks size={13} />} title="Recommendations">
        {detail ? (
          <BulletList
            items={detail.recommendations}
            empty="The summarizer did not suggest follow-up actions."
          />
        ) : (
          <p className="text-sm text-slate-500">
            Recommendations will appear once the review has been summarized.
          </p>
        )}
      </SectionCard>
    </div>
  )
}
