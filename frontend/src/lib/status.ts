import type { NodeStatus, RunStatus, Severity } from '../types'

/** Display labels for run states. */
export const RUN_STATUS_LABEL: Record<RunStatus, string> = {
  queued: 'Queued',
  running: 'Running',
  waiting_hitl: 'Awaiting human review',
  succeeded: 'Succeeded',
  failed: 'Failed',
}

/** Tailwind classes for run status badges. */
export const RUN_STATUS_STYLE: Record<RunStatus, string> = {
  queued: 'border-slate-300 bg-slate-100 text-slate-700',
  running: 'border-blue-300 bg-blue-100 text-blue-800',
  waiting_hitl: 'border-amber-300 bg-amber-100 text-amber-800',
  succeeded: 'border-emerald-300 bg-emerald-100 text-emerald-800',
  failed: 'border-rose-300 bg-rose-100 text-rose-800',
}

/** Visual mapping for DAG agent nodes. */
export interface NodeStyle {
  border: string
  background: string
  dot: string
  pulse?: boolean
}

export const NODE_STATUS_STYLE: Record<NodeStatus, NodeStyle> = {
  idle: { border: '#cbd5e1', background: '#f8fafc', dot: '#94a3b8' },
  running: { border: '#3b82f6', background: '#eff6ff', dot: '#3b82f6', pulse: true },
  success: { border: '#22c55e', background: '#f0fdf4', dot: '#22c55e' },
  failed: { border: '#ef4444', background: '#fef2f2', dot: '#ef4444' },
  paused: { border: '#f59e0b', background: '#fffbeb', dot: '#f59e0b' },
}

/** Severity -> sort rank (lower = more severe). */
export const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 0,
  error: 1,
  warning: 2,
  info: 3,
}

/** Tailwind classes for severity badges. */
export const SEVERITY_STYLE: Record<Severity, string> = {
  critical: 'bg-rose-100 text-rose-800',
  error: 'bg-orange-100 text-orange-800',
  warning: 'bg-amber-100 text-amber-800',
  info: 'bg-slate-100 text-slate-700',
}

/** Solid dot colors for inline markers (diff lines). */
export const SEVERITY_DOT: Record<Severity, string> = {
  critical: 'bg-rose-500',
  error: 'bg-orange-500',
  warning: 'bg-amber-400',
  info: 'bg-slate-400',
}

export function formatTime(epochSeconds: number): string {
  return new Date(epochSeconds * 1000).toLocaleString()
}

export function formatRelative(epochSeconds: number): string {
  const seconds = Math.max(0, Math.floor(Date.now() / 1000 - epochSeconds))
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}
