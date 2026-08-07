import { ChevronRight, GitBranch } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Finding, RunSummary } from '../types'
import { SEVERITY_ORDER, SEVERITY_STYLE } from '../lib/status'
import { formatRelative } from '../lib/status'
import StatusBadge from './StatusBadge'

const SEVERITIES = ['critical', 'error', 'warning', 'info'] as const

function StatTile({
  label,
  value,
  accent,
}: {
  label: string
  value: number | string
  accent: string
}) {
  return (
    <div className="rounded-xl border border-edge bg-panel p-4">
      <div className={`text-2xl font-semibold tabular-nums ${accent}`}>{value}</div>
      <div className="mt-1 text-xs text-slate-400">{label}</div>
    </div>
  )
}

/** Dashboard-level metrics derived from the run list. */
export function DashboardMetrics({ runs }: { runs: RunSummary[] }) {
  const succeeded = runs.filter((run) => run.status === 'succeeded').length
  const failed = runs.filter((run) => run.status === 'failed').length
  const awaiting = runs.filter((run) => run.status === 'waiting_hitl').length
  const findings = runs.reduce((sum, run) => sum + run.findings, 0)
  const hitlPending = runs.reduce((sum, run) => sum + run.hitl_pending, 0)

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      <StatTile label="Total reviews" value={runs.length} accent="text-slate-100" />
      <StatTile label="Succeeded" value={succeeded} accent="text-emerald-400" />
      <StatTile label="Failed" value={failed} accent="text-rose-400" />
      <StatTile label="Awaiting human" value={awaiting + hitlPending} accent="text-amber-400" />
      <StatTile label="Findings" value={findings} accent="text-accent" />
    </div>
  )
}

/** Live run feed table (Metrics page). */
export function RunFeed({ runs }: { runs: RunSummary[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-edge bg-panel">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-edge bg-panel-2 text-xs uppercase tracking-wider text-slate-500">
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
              className="border-b border-edge/60 last:border-0 hover:bg-panel-2/60"
            >
              <td className="px-4 py-3">
                <StatusBadge status={run.status} />
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-1.5 font-medium text-slate-200">
                  <GitBranch size={14} className="text-slate-500" />
                  {run.repository}
                </div>
              </td>
              <td className="px-4 py-3">
                <span className="font-mono text-xs text-accent">{run.commit}</span>
                {run.hitl_pending > 0 && (
                  <span className="ml-2 text-xs text-amber-300">• paused</span>
                )}
              </td>
              <td className="px-4 py-3 text-right font-mono text-xs text-slate-300">
                {run.findings}
              </td>
              <td className="px-4 py-3 text-right font-mono text-xs text-amber-300">
                {run.hitl_pending > 0 ? run.hitl_pending : '—'}
              </td>
              <td className="px-4 py-3 text-xs text-slate-500">
                {formatRelative(run.updated_at)}
              </td>
              <td className="px-4 py-3 text-right">
                <Link
                  to={`/runs/${run.id}`}
                  className="inline-flex items-center gap-1 rounded-lg border border-edge bg-panel-2 px-2.5 py-1 text-xs font-medium text-slate-300 hover:border-accent/50 hover:text-accent"
                >
                  View <ChevronRight size={13} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Severity distribution for a single run. */
export function FindingMetrics({
  findings,
  runStatus,
}: {
  findings: Finding[]
  runStatus?: string
}) {
  const counts = SEVERITIES.map((severity) => ({
    severity,
    count: findings.filter((finding) => finding.severity === severity).length,
  }))
  const total = findings.length
  const hitl = findings.filter((finding) => finding.requires_hitl).length

  return (
    <div className="rounded-xl border border-edge bg-panel p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Findings by severity
      </h3>
      {total === 0 && runStatus === 'failed' ? (
        <p className="mt-2 text-sm text-rose-400">Review failed</p>
      ) : total === 0 ? (
        <p className="mt-2 text-sm text-slate-500">No findings.</p>
      ) : (
        <div className="mt-3 space-y-2">
          {counts.map(({ severity, count }) => (
            <div key={severity} className="flex items-center gap-2 text-xs">
              <span
                className={`w-16 rounded px-1.5 py-0.5 text-center font-medium uppercase ${SEVERITY_STYLE[severity]}`}
              >
                {severity}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-700/50">
                <div
                  className="h-full rounded-full bg-accent"
                  style={{ width: `${total ? (count / total) * 100 : 0}%` }}
                />
              </div>
              <span className="w-6 text-right font-mono text-slate-300">{count}</span>
            </div>
          ))}
          <div className="flex items-center justify-between pt-1 text-xs text-slate-500">
            <span>
              {total} finding{total === 1 ? '' : 's'}
            </span>
            {hitl > 0 && (
              <span className="text-amber-300">{hitl} required human review</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

/** Export for tests. */
export const SEVERITY_RANK = SEVERITY_ORDER
