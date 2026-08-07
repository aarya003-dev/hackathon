import { Eye, Loader2 } from 'lucide-react'
import type { RunStatus } from '../types'
import { RUN_STATUS_LABEL, RUN_STATUS_STYLE } from '../lib/status'

export default function StatusBadge({ status }: { status: RunStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${RUN_STATUS_STYLE[status]}`}
    >
      {status === 'running' && <Loader2 size={12} className="animate-spin" />}
      {status === 'waiting_hitl' && <Eye size={12} />}
      {RUN_STATUS_LABEL[status]}
    </span>
  )
}
