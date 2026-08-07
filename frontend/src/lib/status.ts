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
  queued: 'border-slate-600/60 bg-slate-800/60 text-slate-300',
  running: 'border-cyan-500/50 bg-cyan-500/10 text-cyan-300',
  waiting_hitl: 'border-amber-500/50 bg-amber-500/10 text-amber-300',
  succeeded: 'border-emerald-500/50 bg-emerald-500/10 text-emerald-300',
  failed: 'border-rose-500/50 bg-rose-500/10 text-rose-300',
}

/** Visual mapping for DAG agent nodes. */
export interface NodeStyle {
  border: string
  background: string
  dot: string
  pulse?: boolean
}

export const NODE_STATUS_STYLE: Record<NodeStatus, NodeStyle> = {
  idle: { border: '#2c3345', background: '#14171f', dot: '#4b5563' },
  running: {
    border: '#22d3ee',
    background: 'rgba(34, 211, 238, 0.12)',
    dot: '#22d3ee',
    pulse: true,
  },
  success: {
    border: '#10b981',
    background: 'rgba(16, 185, 129, 0.12)',
    dot: '#10b981',
  },
  failed: {
    border: '#f43f5e',
    background: 'rgba(244, 63, 94, 0.12)',
    dot: '#f43f5e',
  },
  paused: {
    border: '#f59e0b',
    background: 'rgba(245, 158, 11, 0.12)',
    dot: '#f59e0b',
  },
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
  critical: 'bg-rose-500/15 text-rose-300',
  error: 'bg-orange-500/15 text-orange-300',
  warning: 'bg-amber-500/15 text-amber-300',
  info: 'bg-slate-600/50 text-slate-300',
}

/** Colored dot for run-status badges on dark surfaces. */
export const STATUS_DOT: Record<RunStatus, string> = {
  queued: 'bg-slate-400',
  running: 'bg-cyan-400',
  waiting_hitl: 'bg-amber-400',
  succeeded: 'bg-emerald-400',
  failed: 'bg-rose-400',
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
