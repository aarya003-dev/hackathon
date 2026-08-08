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
import '@xyflow/react/dist/style.css'
import type { AgentId, NodeStatus } from '../types'
import { NODE_STATUS_STYLE } from '../lib/status'

const AGENT_LABEL: Record<AgentId, string> = {
  triage: 'Triage',
  core_review: 'Core review',
  security: 'Security',
  suggestion: 'Suggestion',
  summarizer: 'Summarizer',
}

const AGENT_ORDER: AgentId[] = ['triage', 'core_review', 'security', 'suggestion', 'summarizer']

const POSITIONS: Record<AgentId, { x: number; y: number }> = {
  triage: { x: 0, y: 130 },
  core_review: { x: 280, y: 0 },
  security: { x: 280, y: 130 },
  suggestion: { x: 280, y: 260 },
  summarizer: { x: 560, y: 130 },
}

const EDGES: Edge[] = [
  { id: 'e-triage-core', source: 'triage', target: 'core_review' },
  { id: 'e-triage-security', source: 'triage', target: 'security' },
  { id: 'e-triage-suggestion', source: 'triage', target: 'suggestion' },
  { id: 'e-core-summary', source: 'core_review', target: 'summarizer' },
  { id: 'e-security-summary', source: 'security', target: 'summarizer' },
  { id: 'e-suggestion-summary', source: 'suggestion', target: 'summarizer' },
]

export interface AgentNodeData extends Record<string, unknown> {
  agent: AgentId
  status: NodeStatus
}

export type AgentFlowNode = Node<AgentNodeData, 'agent'>

function AgentNode({ data }: NodeProps<AgentFlowNode>) {
  const style = NODE_STATUS_STYLE[data.status]
  return (
    <div
      className="flex items-center gap-2 rounded-xl border-2 px-3 py-2 text-sm font-medium text-slate-700 shadow-sm"
      style={{ borderColor: style.border, background: style.background }}
    >
      <Handle type="target" position={Position.Left} className="!bg-slate-400" />
      <span
        className={`h-2 w-2 shrink-0 rounded-full ${style.pulse ? 'animate-pulse' : ''}`}
        style={{ background: style.dot }}
      />
      <span>{AGENT_LABEL[data.agent]}</span>
      <span className="ml-2 text-[10px] uppercase tracking-wide text-slate-400">{data.status}</span>
      <Handle type="source" position={Position.Right} className="!bg-slate-400" />
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
    <div className="h-[360px] w-full overflow-hidden rounded-xl border border-slate-200 bg-white">
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
        <Background gap={22} color="#e2e8f0" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  )
}
