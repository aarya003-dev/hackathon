import { Eye, Loader2 } from 'lucide-react'
import type { RunStatus } from '../types'
import { RUN_STATUS_LABEL, RUN_STATUS_STYLE, STATUS_DOT } from '../lib/status'

export default function StatusBadge({ status }: { status: RunStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${RUN_STATUS_STYLE[status]}`}
    >
      {status === 'running' ? (
        <Loader2 size={12} className="animate-spin" />
      ) : (
        <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[status]}`} />
      )}
      {status === 'waiting_hitl' && <Eye size={12} />}
      {RUN_STATUS_LABEL[status]}
    </span>
  )
}
