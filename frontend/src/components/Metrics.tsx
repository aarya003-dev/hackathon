import type { Finding, RunSummary } from '../types'
import { SEVERITY_ORDER, SEVERITY_STYLE } from '../lib/status'

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
    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className={`text-2xl font-semibold ${accent}`}>{value}</div>
      <div className="mt-0.5 text-xs text-slate-500">{label}</div>
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
      <StatTile label="Total reviews" value={runs.length} accent="text-slate-900" />
      <StatTile label="Succeeded" value={succeeded} accent="text-emerald-600" />
      <StatTile label="Failed" value={failed} accent="text-rose-600" />
      <StatTile label="Awaiting human" value={awaiting + hitlPending} accent="text-amber-600" />
      <StatTile label="Findings" value={findings} accent="text-indigo-600" />
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
    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        Findings by severity
      </h3>
      {total === 0 && runStatus === 'failed' ? (
        <p className="mt-2 text-sm text-rose-500">Review failed</p>
      ) : total === 0 ? (
        <p className="mt-2 text-sm text-slate-400">No findings.</p>
      ) : (
        <div className="mt-2 space-y-2">
          {counts.map(({ severity, count }) => (
            <div key={severity} className="flex items-center gap-2 text-xs">
              <span
                className={`w-16 rounded px-1.5 py-0.5 text-center font-medium uppercase ${SEVERITY_STYLE[severity]}`}
              >
                {severity}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-slate-700"
                  style={{ width: `${total ? (count / total) * 100 : 0}%` }}
                />
              </div>
              <span className="w-6 text-right font-mono text-slate-600">{count}</span>
            </div>
          ))}
          <div className="flex items-center justify-between pt-1 text-xs text-slate-500">
            <span>
              {total} finding{total === 1 ? '' : 's'}
            </span>
            {hitl > 0 && (
              <span className="text-amber-700">{hitl} required human review</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

/** Export for tests. */
export const SEVERITY_RANK = SEVERITY_ORDER
