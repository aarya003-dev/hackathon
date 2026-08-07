import { useCallback, useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Activity,
  Bot,
  CheckCircle2,
  FileDiff,
  Gauge,
  GitPullRequest,
  Info,
  Loader2,
  ScrollText,
  Zap,
  type LucideIcon,
} from 'lucide-react'
import { api } from '../api/client'
import type { AnalyzeResult, RunSummary } from '../types'

interface NavItem {
  id: string
  label: string
  icon: LucideIcon
  to: string
  active: boolean
  subtitle?: string
  disabled?: boolean
}

export default function Sidebar() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [analyzing, setAnalyzing] = useState(false)
  const [toast, setToast] = useState<{ kind: 'ok' | 'info' | 'error'; text: string } | null>(
    null,
  )
  const location = useLocation()
  const navigate = useNavigate()

  const refresh = useCallback(() => {
    api
      .listRuns()
      .then(setRuns)
      .catch(() => {
        /* sidebar stays usable offline; pages surface the error */
      })
  }, [])

  useEffect(() => {
    refresh()
    const timer = window.setInterval(refresh, 15000)
    return () => window.clearInterval(timer)
  }, [refresh])

  const latestRun = [...runs].sort((a, b) => b.updated_at - a.updated_at)[0]
  const live = runs.some((run) =>
    ['queued', 'running', 'waiting_hitl'].includes(run.status),
  )
  const onRunView = location.pathname.startsWith('/runs/')
  const onRunSummary = onRunView && location.pathname.endsWith('/summary')

  const nav: NavItem[] = [
    {
      id: 'metrics',
      label: 'Metrics',
      icon: Gauge,
      to: '/metrics',
      active: location.pathname === '/metrics',
    },
    {
      id: 'pipeline',
      label: 'Pipeline',
      icon: GitPullRequest,
      to: '/',
      active: location.pathname === '/',
    },
    {
      id: 'pr-view',
      label: 'PR View',
      icon: FileDiff,
      to: latestRun ? `/runs/${latestRun.id}` : '/',
      active: onRunView && !onRunSummary,
      subtitle: latestRun ? `latest · ${latestRun.commit}` : undefined,
      disabled: !latestRun,
    },
    {
      id: 'summary',
      label: 'Summary',
      icon: ScrollText,
      to: latestRun ? `/runs/${latestRun.id}/summary` : '/',
      active: onRunSummary,
      subtitle: latestRun ? 'AI review summary' : undefined,
      disabled: !latestRun,
    },
    {
      id: 'agents',
      label: 'Agents',
      icon: Bot,
      to: '/agents',
      active: location.pathname === '/agents',
    },
  ]

  const showToast = (
    kind: 'ok' | 'info' | 'error',
    text: string,
    timeout = 6000,
  ) => {
    setToast({ kind, text })
    window.setTimeout(() => setToast(null), timeout)
  }

  const runAnalyze = async () => {
    if (analyzing) return
    setAnalyzing(true)
    try {
      const result: AnalyzeResult = await api.analyze()
      if (result.duplicate) {
        showToast('info', 'Latest commit already analyzed — no new review needed.')
      } else {
        showToast('ok', `Analysis started for ${result.commit?.slice(0, 8) ?? 'HEAD'}.`)
        navigate(`/runs/${result.run_id}`)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'request failed'
      showToast(
        'error',
        message.includes('no repository')
          ? 'No repository configured — set GIT_REPO_PATH or ingest a commit first.'
          : `New analysis failed: ${message}`,
      )
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-edge bg-panel">
        {/* Brand */}
        <div className="flex items-center gap-3 px-4 py-5">
          <div className="glow-accent flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <Activity size={20} />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold leading-tight text-slate-100">
              Solar Flare
            </div>
            <div className="truncate text-[10px] uppercase tracking-wider text-slate-500">
              AI Review Control Center
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="mt-2 flex-1 space-y-1 px-3">
          {nav.map((item) => (
            <button
              key={item.id}
              type="button"
              disabled={item.disabled}
              onClick={() => navigate(item.to)}
              className={`group flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left text-sm transition-colors ${
                item.active
                  ? 'glow-accent border-accent/40 bg-accent-soft text-accent'
                  : item.disabled
                    ? 'cursor-not-allowed border-transparent text-slate-600'
                    : 'border-transparent text-slate-400 hover:bg-panel-2 hover:text-slate-200'
              }`}
            >
              <item.icon
                size={17}
                className={item.active ? 'text-accent' : 'text-slate-500'}
              />
              <span className="min-w-0 flex-1">
                <span className="block">{item.label}</span>
                {item.subtitle && (
                  <span className="block truncate font-mono text-[10px] text-slate-600">
                    {item.subtitle}
                  </span>
                )}
              </span>
              {item.active && <span className="h-1.5 w-1.5 rounded-full bg-accent" />}
            </button>
          ))}
        </nav>

        {/* System status */}
        <div className="px-4 pb-3">
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-slate-600">
            <span
              className={`h-1.5 w-1.5 rounded-full ${live ? 'animate-pulse bg-cyan-400' : 'bg-emerald-400'}`}
            />
            {live ? 'Pipeline live' : 'System online'}
          </div>
        </div>

        {/* New Analysis */}
        <div className="border-t border-edge p-3">
          <button
            type="button"
            onClick={runAnalyze}
            disabled={analyzing}
            className="glow-accent flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-3 py-2.5 text-sm font-semibold text-slate-950 transition-colors hover:bg-cyan-300 disabled:opacity-60"
          >
            {analyzing ? (
              <Loader2 size={15} className="animate-spin" />
            ) : (
              <Zap size={15} />
            )}
            New Analysis
          </button>
          <p className="mt-2 text-center text-[10px] text-slate-600">
            Reviews the latest commit in the watched repo
          </p>
        </div>
      </aside>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 flex max-w-sm items-start gap-2.5 rounded-lg border border-edge bg-panel-2 px-4 py-3 text-sm text-slate-200 shadow-2xl">
          {toast.kind === 'ok' && (
            <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-emerald-400" />
          )}
          {toast.kind === 'info' && (
            <Info size={16} className="mt-0.5 shrink-0 text-cyan-400" />
          )}
          {toast.kind === 'error' && (
            <Zap size={16} className="mt-0.5 shrink-0 text-rose-400" />
          )}
          <span>{toast.text}</span>
        </div>
      )}
    </>
  )
}
