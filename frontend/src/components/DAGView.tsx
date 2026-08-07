import { useMemo } from 'react'
import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react'
import { Code2, GitBranch, ShieldAlert, Sparkles, type LucideIcon } from 'lucide-react'
import '@xyflow/react/dist/style.css'
import type { AgentId, NodeStatus } from '../types'
import { NODE_STATUS_STYLE } from '../lib/status'

const AGENT_LABEL: Record<AgentId, string> = {
  triage: 'Triage',
  core_review: 'Core review',
  security: 'Security',
  summarizer: 'Summarizer',
}

const AGENT_ICON: Record<AgentId, LucideIcon> = {
  triage: GitBranch,
  core_review: Code2,
  security: ShieldAlert,
  summarizer: Sparkles,
}

const AGENT_ORDER: AgentId[] = ['triage', 'core_review', 'security', 'summarizer']

const POSITIONS: Record<AgentId, { x: number; y: number }> = {
  triage: { x: 0, y: 130 },
  core_review: { x: 300, y: 0 },
  security: { x: 300, y: 260 },
  summarizer: { x: 600, y: 130 },
}

const EDGES: Edge[] = [
  { id: 'e-triage-core', source: 'triage', target: 'core_review' },
  { id: 'e-triage-security', source: 'triage', target: 'security' },
  { id: 'e-core-summary', source: 'core_review', target: 'summarizer' },
  { id: 'e-security-summary', source: 'security', target: 'summarizer' },
]

export interface AgentNodeData extends Record<string, unknown> {
  agent: AgentId
  status: NodeStatus
}

export type AgentFlowNode = Node<AgentNodeData, 'agent'>

function AgentNode({ data }: NodeProps<AgentFlowNode>) {
  const style = NODE_STATUS_STYLE[data.status]
  const Icon = AGENT_ICON[data.agent]
  return (
    <div className="flex flex-col items-center gap-2">
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !border-0 !bg-slate-600" />
      <div
        className="flex h-16 w-16 items-center justify-center rounded-full border-2 transition-shadow"
        style={{
          borderColor: style.border,
          background: style.background,
          boxShadow: style.pulse ? `0 0 22px ${style.border}66` : undefined,
        }}
      >
        <Icon size={26} style={{ color: style.dot }} className={style.pulse ? 'animate-pulse' : ''} />
      </div>
      <div className="text-center">
        <div className="text-sm font-medium text-slate-100">{AGENT_LABEL[data.agent]}</div>
        <div className="text-[10px] uppercase tracking-wider text-slate-500">{data.status}</div>
      </div>
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !border-0 !bg-slate-600" />
    </div>
  )
}

const nodeTypes = { agent: AgentNode }

/** Live agent DAG: maps backend NodeStatus -> visual state. */
export default function DAGView({ nodes }: { nodes: Record<AgentId, NodeStatus> }) {
  const flowNodes: AgentFlowNode[] = useMemo(
    () =>
      AGENT_ORDER.map((agent) => ({
        id: agent,
        type: 'agent' as const,
        position: POSITIONS[agent],
        data: { agent, status: nodes[agent] ?? 'idle' } satisfies AgentNodeData,
      })),
    [nodes],
  )

  return (
    <div className="h-[380px] w-full overflow-hidden rounded-xl border border-edge bg-panel">
      <ReactFlow
        nodes={flowNodes}
        edges={EDGES}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.35 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={26} color="#1f2430" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  )
}
