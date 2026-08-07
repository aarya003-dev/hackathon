import { CheckCircle2, ShieldAlert, TriangleAlert } from 'lucide-react'
import type { Finding, Severity } from '../types'
import { SEVERITY_ORDER, SEVERITY_STYLE } from '../lib/status'

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: 'Critical',
  error: 'Error',
  warning: 'Warning',
  info: 'Info',
}

const AGENT_LABEL: Record<Finding['agent'], string> = {
  triage: 'Triage',
  core_review: 'Core review',
  security: 'Security',
  summarizer: 'Summarizer',
}

export default function FindingList({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-6 text-center text-sm text-emerald-800">
        <CheckCircle2 size={20} className="mx-auto mb-2" />
        No issues found in this change.
      </div>
    )
  }

  const sorted = [...findings].sort(
    (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity],
  )

  return (
    <ul className="space-y-3">
      {sorted.map((finding) => (
        <li
          key={finding.id}
          className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
        >
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${SEVERITY_STYLE[finding.severity]}`}
            >
              {finding.severity === 'critical' || finding.severity === 'error' ? (
                <ShieldAlert size={12} />
              ) : (
                <TriangleAlert size={12} />
              )}
              {SEVERITY_LABEL[finding.severity]}
            </span>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
              {finding.category}
            </span>
            <span className="text-[11px] text-slate-400">{AGENT_LABEL[finding.agent]}</span>
            <span className="ml-auto font-mono text-[11px] text-slate-500">
              {finding.file_path}
              {finding.line_start != null ? `:${finding.line_start}` : ''}
              {finding.requires_hitl && (
                <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 font-sans font-medium text-amber-800">
                  HITL
                </span>
              )}
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-800">{finding.message}</p>
          {finding.suggestion && (
            <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-900 px-3 py-2 text-xs text-emerald-300">
              {finding.suggestion}
            </pre>
          )}
          <div className="mt-2 flex items-center gap-2 text-[11px] text-slate-400">
            <span>Confidence</span>
            <div className="h-1.5 w-24 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-indigo-500"
                style={{ width: `${Math.round(finding.confidence * 100)}%` }}
              />
            </div>
            <span>{Math.round(finding.confidence * 100)}%</span>
          </div>
        </li>
      ))}
    </ul>
  )
}
