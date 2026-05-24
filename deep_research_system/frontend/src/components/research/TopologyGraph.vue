<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'
import AgentNode from './AgentNode.vue'

const props = defineProps<{
  topology: string
  nodeStates: Record<string, string>
  agentDetails?: Record<string, { model?: string; message?: string; output?: any }>
  debateBranches?: string[]
  hasSupplementarySearch?: boolean
}>()

const emit = defineEmits<{ 'select-agent': [agent: string] }>()

const { fitView, onNodeDragStop } = useVueFlow()

function onNodeClick({ node }: { node: any }) {
  emit('select-agent', node.id)
}

// --- Layout builders ---

function buildHierarchicalLayout(hasSupplementary: boolean) {
  const base = [
    { id: 'planner', type: 'agent' as const, position: { x: 0, y: 200 }, data: { label: 'PLANNER', agent: 'planner', status: 'idle' } },
    { id: 'searcher', type: 'agent' as const, position: { x: 220, y: 80 }, data: { label: 'SEARCHER', agent: 'searcher', status: 'idle' } },
    { id: 'reader', type: 'agent' as const, position: { x: 220, y: 320 }, data: { label: 'READER', agent: 'reader', status: 'idle' } },
    { id: 'analyzer', type: 'agent' as const, position: { x: 440, y: 200 }, data: { label: 'ANALYZER', agent: 'analyzer', status: 'idle' } },
    { id: 'critic', type: 'agent' as const, position: { x: 660, y: 200 }, data: { label: 'CRITIC', agent: 'critic', status: 'idle' } },
    { id: 'supplementary_search', type: 'agent' as const, position: { x: 660, y: 80 }, data: { label: 'SUPPLEMENT', agent: 'supplementary_search', status: 'idle' } },
    { id: 'writer', type: 'agent' as const, position: { x: 880, y: 120 }, data: { label: 'WRITER', agent: 'writer', status: 'idle' } },
    { id: 'validator', type: 'agent' as const, position: { x: 880, y: 320 }, data: { label: 'VALIDATOR', agent: 'validator', status: 'idle' } },
  ]
  return base
}

function buildHierarchicalEdges(hasSupplementary: boolean) {
  const base: any[] = [
    { id: 'e1', source: 'planner', target: 'searcher', animated: true, type: 'smoothstep' },
    { id: 'e2', source: 'planner', target: 'reader', animated: true, type: 'smoothstep' },
    { id: 'e3', source: 'searcher', target: 'analyzer', animated: true, type: 'smoothstep' },
    { id: 'e4', source: 'reader', target: 'analyzer', animated: true, type: 'smoothstep' },
    { id: 'e5', source: 'analyzer', target: 'critic', animated: true, type: 'smoothstep' },
    { id: 'e-loop1', source: 'critic', target: 'supplementary_search', animated: true, type: 'smoothstep' },
    { id: 'e-loop2', source: 'supplementary_search', target: 'analyzer', animated: true, type: 'smoothstep' },
    { id: 'e6', source: 'critic', target: 'writer', animated: true, type: 'smoothstep' },
    { id: 'e7', source: 'critic', target: 'validator', animated: true, type: 'smoothstep' },
  ]
  return base
}

function buildDebateLayout(branches: string[]) {
  const ids = branches.length ? branches : ['pro', 'con', 'neutral']
  const spacing = 400 / Math.max(ids.length - 1, 1)
  const startY = 350 - (ids.length - 1) * spacing / 2
  const nodes: any[] = [
    { id: 'planner', type: 'agent', position: { x: 0, y: 200 }, data: { label: 'PLANNER', agent: 'planner', status: 'idle' } },
  ]
  ids.forEach((bid, i) => {
    nodes.push({ id: bid, type: 'agent', position: { x: 250, y: startY + i * spacing }, data: { label: bid.toUpperCase(), agent: bid, status: 'idle' } })
  })
  nodes.push(
    { id: 'critic', type: 'agent', position: { x: 500, y: 200 }, data: { label: 'CRITIC', agent: 'critic', status: 'idle' } },
    { id: 'synthesizer', type: 'agent', position: { x: 720, y: 200 }, data: { label: 'SYNTHESIZER', agent: 'synthesizer', status: 'idle' } },
    { id: 'writer', type: 'agent', position: { x: 940, y: 200 }, data: { label: 'WRITER', agent: 'writer', status: 'idle' } },
  )
  return nodes
}

function buildDebateEdges(branches: string[]) {
  const ids = branches.length ? branches : ['pro', 'con', 'neutral']
  const edges: any[] = []
  ids.forEach((bid, i) => {
    edges.push({ id: `e${i}`, source: 'planner', target: bid, animated: true, type: 'smoothstep' })
    edges.push({ id: `e${i + ids.length}`, source: bid, target: 'critic', animated: true, type: 'smoothstep' })
  })
  const offset = ids.length * 2
  edges.push(
    { id: `e${offset}`, source: 'critic', target: 'synthesizer', animated: true, type: 'smoothstep' },
    { id: `e${offset + 1}`, source: 'synthesizer', target: 'writer', animated: true, type: 'smoothstep' },
  )
  return edges
}

// --- Subtask node helpers ---

const SUBTASK_AGENTS = new Set(['searcher', 'reader', 'analyzer', 'critic', 'writer'])

function getSubtaskParent(agentName: string): string | null {
  // searcher_sq_1 -> searcher, reader_sq_2 -> reader
  const sqMatch = agentName.match(/^(\w+)_sq_\d+$/)
  if (sqMatch && SUBTASK_AGENTS.has(sqMatch[1])) return sqMatch[1]
  // repair_writer_1 -> validator, repair_writer_2 -> validator
  const repairMatch = agentName.match(/^repair_writer_\d+$/)
  if (repairMatch) return 'validator'
  return null
}

function getSubtaskLabel(agentName: string): string {
  const sqMatch = agentName.match(/^(\w+)_sq_(\d+)$/)
  if (sqMatch) return `${sqMatch[1].toUpperCase()} #${sqMatch[2]}`
  const repairMatch = agentName.match(/^repair_writer_(\d+)$/)
  if (repairMatch) return `REPAIR #${repairMatch[1]}`
  return agentName.toUpperCase()
}

const NODE_W = 180
const NODE_H = 70
const NODE_PAD = 12

function overlaps(x: number, y: number, existingNodes: any[]): boolean {
  for (const n of existingNodes) {
    const nx = n.position?.x ?? 0
    const ny = n.position?.y ?? 0
    if (Math.abs(x - nx) < NODE_W + NODE_PAD && Math.abs(y - ny) < NODE_H + NODE_PAD) {
      return true
    }
  }
  return false
}

function computeSubtaskPosition(parentAgent: string, index: number, existingNodes: any[]): { x: number; y: number } {
  const parent = existingNodes.find((n: any) => n.data.agent === parentAgent)
  const parentPos = parent?.position || { x: 220, y: 200 }
  const baseX = parentPos.x + 200
  let y = parentPos.y - 40 + index * 75
  // Walk downward until we find a free spot
  let attempts = 0
  while (overlaps(baseX, y, existingNodes) && attempts < 30) {
    y += NODE_H + NODE_PAD
    attempts++
  }
  return { x: baseX, y }
}

// --- Reactive state ---

const flowNodes = ref<any[]>([])
const flowEdges = ref<any[]>([])

// Track last topology key to detect structural changes
let lastTopologyKey = ''

function topologyKey(): string {
  const t = props.topology
  if (t === 'debate') return `debate:${(props.debateBranches || []).join(',')}`
  return `hierarchical:${props.hasSupplementarySearch ? '1' : '0'}`
}

// Rebuild nodes/edges from scratch (resets positions)
function rebuildLayout() {
  const isDebate = props.topology === 'debate'
  const rawNodes = isDebate
    ? buildDebateLayout(props.debateBranches || [])
    : buildHierarchicalLayout(props.hasSupplementarySearch || false)
  const rawEdges = isDebate
    ? buildDebateEdges(props.debateBranches || [])
    : buildHierarchicalEdges(props.hasSupplementarySearch || false)

  // Apply visibility + enrich data
  const activeAgents = Object.keys(props.nodeStates)
  const visibleNodes = rawNodes.filter((n, i) => {
    if (i === 0) return true
    if (activeAgents.includes(n.data.agent)) return true
    const incoming = rawEdges.filter((e: any) => e.target === n.id)
    return incoming.some((e: any) => activeAgents.includes(e.source))
  })

  flowNodes.value = visibleNodes.map(n => {
    const detail = props.agentDetails?.[n.data.agent]
    return {
      ...n,
      data: {
        ...n.data,
        status: props.nodeStates[n.data.agent] || 'idle',
        model: detail?.model,
        activity: detail?.message,
      },
    }
  })

  // Inject dynamic subtask nodes
  injectSubtaskNodes(activeAgents)

  const visibleIds = new Set(flowNodes.value.map((n: any) => n.id))
  flowEdges.value = rawEdges.filter((e: any) => visibleIds.has(e.source) && visibleIds.has(e.target))

  // Add edges for subtask nodes
  injectSubtaskEdges()

  lastTopologyKey = topologyKey()
}

function injectSubtaskNodes(activeAgents: string[]) {
  const existingIds = new Set(flowNodes.value.map((n: any) => n.id))
  // Group subtasks by parent for positioning
  const subtasksByParent: Record<string, string[]> = {}

  for (const agent of activeAgents) {
    if (existingIds.has(agent)) continue
    const parent = getSubtaskParent(agent)
    if (!parent) continue
    if (!subtasksByParent[parent]) subtasksByParent[parent] = []
    subtasksByParent[parent].push(agent)
  }

  for (const [parent, subtasks] of Object.entries(subtasksByParent)) {
    subtasks.sort() // sq_1, sq_2, ...
    subtasks.forEach((agent, index) => {
      if (existingIds.has(agent)) return
      const pos = computeSubtaskPosition(parent, index, flowNodes.value)
      const detail = props.agentDetails?.[agent]
      flowNodes.value.push({
        id: agent,
        type: 'agent',
        position: pos,
        data: {
          label: getSubtaskLabel(agent),
          agent,
          status: props.nodeStates[agent] || 'idle',
          model: detail?.model,
          activity: detail?.message,
        },
      })
    })
  }
}

function injectSubtaskEdges() {
  const existingEdgeIds = new Set(flowEdges.value.map((e: any) => e.id))
  const existingNodeIds = new Set(flowNodes.value.map((n: any) => n.id))

  for (const node of flowNodes.value) {
    const parent = getSubtaskParent(node.data.agent)
    if (!parent) continue
    const edgeId = `e-subtask-${node.data.agent}`
    if (existingEdgeIds.has(edgeId)) continue
    if (!existingNodeIds.has(parent)) continue
    flowEdges.value.push({
      id: edgeId,
      source: parent,
      target: node.data.agent,
      animated: true,
      type: 'smoothstep',
    })
    // Repair nodes need a return edge back to validator
    if (node.data.agent.startsWith('repair_writer_')) {
      const returnEdgeId = `e-subtask-return-${node.data.agent}`
      if (!existingEdgeIds.has(returnEdgeId)) {
        flowEdges.value.push({
          id: returnEdgeId,
          source: node.data.agent,
          target: parent,
          animated: true,
          type: 'smoothstep',
        })
      }
    }
  }
}

// Update data/status only, preserve positions
function updateDataOnly() {
  const activeAgents = Object.keys(props.nodeStates)
  const isDebate = props.topology === 'debate'
  const rawEdges = isDebate
    ? buildDebateEdges(props.debateBranches || [])
    : buildHierarchicalEdges(props.hasSupplementarySearch || false)

  // Get the full layout to check which nodes should be visible
  const rawNodes = isDebate
    ? buildDebateLayout(props.debateBranches || [])
    : buildHierarchicalLayout(props.hasSupplementarySearch || false)

  const visibleNodeIds = new Set<string>()
  rawNodes.forEach((n, i) => {
    if (i === 0) { visibleNodeIds.add(n.id); return }
    if (activeAgents.includes(n.data.agent)) { visibleNodeIds.add(n.id); return }
    const incoming = rawEdges.filter((e: any) => e.target === n.id)
    if (incoming.some((e: any) => activeAgents.includes(e.source))) visibleNodeIds.add(n.id)
  })

  // Add newly visible predefined nodes (with default positions)
  const existingIds = new Set(flowNodes.value.map((n: any) => n.id))
  for (const raw of rawNodes) {
    if (visibleNodeIds.has(raw.id) && !existingIds.has(raw.id)) {
      const detail = props.agentDetails?.[raw.data.agent]
      flowNodes.value.push({
        ...raw,
        data: {
          ...raw.data,
          status: props.nodeStates[raw.data.agent] || 'idle',
          model: detail?.model,
          activity: detail?.message,
        },
      })
    }
  }

  // Inject dynamic subtask nodes
  injectSubtaskNodes(activeAgents)

  // Update data/status on existing nodes (do NOT touch position)
  for (let i = 0; i < flowNodes.value.length; i++) {
    const node = flowNodes.value[i]
    const detail = props.agentDetails?.[node.data.agent]
    const newActivity = detail?.message
    const newStatus = props.nodeStates[node.data.agent] || 'idle'
    // Only replace if data actually changed to avoid unnecessary VueFlow re-renders
    if (node.data.status !== newStatus || node.data.activity !== newActivity || node.data.model !== detail?.model) {
      flowNodes.value[i] = {
        ...node,
        data: {
          ...node.data,
          status: newStatus,
          model: detail?.model,
          activity: newActivity,
        },
      }
    }
  }

  // Update edges
  const currentIds = new Set(flowNodes.value.map((n: any) => n.id))
  flowEdges.value = rawEdges.filter((e: any) => currentIds.has(e.source) && currentIds.has(e.target))

  // Add edges for subtask nodes
  injectSubtaskEdges()
}

// --- Watchers ---

// Topology structural change -> full rebuild
watch(() => [props.topology, props.debateBranches, props.hasSupplementarySearch], () => {
  rebuildLayout()
  setTimeout(() => fitView({ padding: 0.2 }), 100)
}, { deep: true })

// Node states / details change -> data-only update
watch(() => [props.nodeStates, props.agentDetails], () => {
  const key = topologyKey()
  if (key !== lastTopologyKey) {
    rebuildLayout()
    setTimeout(() => fitView({ padding: 0.2 }), 100)
  } else {
    updateDataOnly()
  }
}, { deep: true })

// Persist user-dragged positions
onNodeDragStop(({ nodes: draggedNodes }: any) => {
  for (const dn of draggedNodes) {
    const target = flowNodes.value.find((n: any) => n.id === dn.id)
    if (target) {
      target.position = { x: dn.position.x, y: dn.position.y }
    }
  }
})

// Initial build
onMounted(() => {
  rebuildLayout()
})
</script>

<template>
  <div class="h-[420px] rounded-xl border border-cyber-border overflow-hidden">
    <VueFlow
      v-model:nodes="flowNodes"
      v-model:edges="flowEdges"
      :default-viewport="{ zoom: 0.75, x: 20, y: 30 }"
      :min-zoom="0.3"
      :max-zoom="2"
      :snap-to-grid="false"
      :nodes-draggable="true"
      :nodes-connectable="false"
      :pan-on-drag="true"
      :zoom-on-scroll="true"
      :zoom-on-pinch="true"
      fit-view-on-init
      @node-click="onNodeClick"
    >
      <template #node-agent="nodeProps">
        <AgentNode v-bind="nodeProps" />
      </template>
      <Background :gap="24" :size="1" pattern-color="#1a2a4a" />
      <Controls class="!bg-cyber-card !border-cyber-border !text-gray-400" />
      <MiniMap class="!bg-cyber-card !border-cyber-border" />
    </VueFlow>
  </div>
</template>
