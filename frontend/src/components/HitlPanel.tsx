import { useState } from 'react'
import { Check, Loader2, ShieldAlert, X } from 'lucide-react'
import type { Approval, Finding } from '../types'
import { api } from '../api/client'
import { SEVERITY_STYLE, formatTime } from '../lib/status'

/** Paused-run HITL gate: evidence + explicit approve/reject. */
export default function HitlPanel({
  approvals,
  findings,
  reviewer,
  onReviewerChange,
  onDecision,
}: {
  approvals: Approval[]
  findings: Finding[]
  reviewer: string
  onReviewerChange: (name: string) => void
  onDecision: () => void
}) {
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const pending = approvals.filter((approval) => approval.status === 'pending')
  if (pending.length === 0) return null

  const findingById = new Map(findings.map((finding) => [finding.id, finding]))

  const decide = async (approval: Approval, decision: 'approve' | 'reject') => {
    setBusy(approval.id)
    setError(null)
    try {
      await api.decide(approval.id, { decision, by: reviewer || 'operator' })
      onDecision()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Decision failed')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4">
      <div className="flex items-center gap-2 text-amber-200">
        <ShieldAlert size={18} />
        <h3 className="text-sm font-semibold">Human review required</h3>
        <span className="ml-auto text-xs text-amber-300">{pending.length} pending</span>
      </div>
      <p className="mt-1 text-xs text-amber-300/80">
        The security agent paused this review. Review the evidence below and decide
        explicitly; the run resumes automatically.
      </p>

      <div className="mt-3 space-y-3">
        {pending.map((approval) => {
          const finding = findingById.get(approval.finding_id)
          if (!finding) return null
          return (
            <div key={approval.id} className="rounded-lg border border-edge bg-panel p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${SEVERITY_STYLE[finding.severity]}`}
                >
                  {finding.severity}
                </span>
                <span className="font-mono text-[11px] text-slate-400">
                  {finding.file_path}
                  {finding.line_start != null ? `:${finding.line_start}` : ''}
                </span>
                <span className="ml-auto text-[11px] text-slate-500">
                  requested {formatTime(approval.requested_at)}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-200">{finding.message}</p>
              {finding.suggestion && (
                <pre className="mt-2 overflow-x-auto rounded-lg bg-[#0b0d12] px-3 py-2 text-xs text-emerald-300">
                  {finding.suggestion}
                </pre>
              )}
              <div className="mt-3 flex items-center gap-2">
                <button
                  type="button"
                  disabled={busy === approval.id}
                  onClick={() => decide(approval, 'approve')}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-50"
                >
                  {busy === approval.id ? (
                    <Loader2 size={13} className="animate-spin" />
                  ) : (
                    <Check size={13} />
                  )}
                  Override &amp; Approve
                </button>
                <button
                  type="button"
                  disabled={busy === approval.id}
                  onClick={() => decide(approval, 'reject')}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-rose-500/90 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-500 disabled:opacity-50"
                >
                  <X size={13} />
                  Reject Fix
                </button>
              </div>
            </div>
          )
        })}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
        <label htmlFor="reviewer" className="font-medium text-slate-300">
          Reviewer
        </label>
        <input
          id="reviewer"
          type="text"
          value={reviewer}
          onChange={(event) => onReviewerChange(event.target.value)}
          placeholder="your name"
          className="rounded-md border border-edge bg-panel px-2 py-1 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-accent/60"
        />
        {error && <span className="text-rose-400">{error}</span>}
      </div>
    </div>
  )
}
