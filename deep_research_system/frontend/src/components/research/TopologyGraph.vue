<script setup lang="ts">
import { computed, watch } from 'vue'
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

const { fitView } = useVueFlow()

function onNodeClick({ node }: { node: any }) {
  emit('select-agent', node.id)
}

// Horizontal layout: left to right
const hierarchicalNodes = computed(() => {
  const base = [
    { id: 'planner', type: 'agent', position: { x: 0, y: 200 }, data: { label: 'PLANNER', agent: 'planner', status: 'idle' } },
    { id: 'searcher', type: 'agent', position: { x: 220, y: 80 }, data: { label: 'SEARCHER', agent: 'searcher', status: 'idle' } },
    { id: 'reader', type: 'agent', position: { x: 220, y: 320 }, data: { label: 'READER', agent: 'reader', status: 'idle' } },
    { id: 'analyzer', type: 'agent', position: { x: 440, y: 200 }, data: { label: 'ANALYZER', agent: 'analyzer', status: 'idle' } },
    { id: 'critic', type: 'agent', position: { x: 660, y: 200 }, data: { label: 'CRITIC', agent: 'critic', status: 'idle' } },
  ]
  if (props.hasSupplementarySearch) {
    base.push({ id: 'supplementary_search', type: 'agent', position: { x: 660, y: 80 }, data: { label: 'SUPPLEMENT', agent: 'supplementary_search', status: 'idle' } })
  }
  base.push(
    { id: 'writer', type: 'agent', position: { x: 880, y: 120 }, data: { label: 'WRITER', agent: 'writer', status: 'idle' } },
    { id: 'validator', type: 'agent', position: { x: 880, y: 320 }, data: { label: 'VALIDATOR', agent: 'validator', status: 'idle' } },
  )
  return base
})

const hierarchicalEdges = computed(() => {
  const base = [
    { id: 'e1', source: 'planner', target: 'searcher', animated: true, type: 'smoothstep' },
    { id: 'e2', source: 'planner', target: 'reader', animated: true, type: 'smoothstep' },
    { id: 'e3', source: 'searcher', target: 'analyzer', animated: true, type: 'smoothstep' },
    { id: 'e4', source: 'reader', target: 'analyzer', animated: true, type: 'smoothstep' },
    { id: 'e5', source: 'analyzer', target: 'critic', animated: true, type: 'smoothstep' },
  ]
  if (props.hasSupplementarySearch) {
    base.push(
      { id: 'e-loop1', source: 'critic', target: 'supplementary_search', animated: true, type: 'smoothstep' } as any,
      { id: 'e-loop2', source: 'supplementary_search', target: 'analyzer', animated: true, type: 'smoothstep' } as any,
    )
  }
  base.push(
    { id: 'e6', source: 'critic', target: 'writer', animated: true, type: 'smoothstep' },
    { id: 'e7', source: 'critic', target: 'validator', animated: true, type: 'smoothstep' },
  )
  return base
})

function buildDebateNodes(branches: string[]) {
  const ids = branches.length ? branches : ['pro', 'con', 'neutral']
  const spacing = 400 / Math.max(ids.length - 1, 1)
  const startY = 350 - (ids.length - 1) * spacing / 2
  const nodes = [
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

const debateNodes = computed(() => buildDebateNodes(props.debateBranches || []))
const debateEdges = computed(() => buildDebateEdges(props.debateBranches || []))

const nodes = computed(() => {
  const base = props.topology === 'debate' ? debateNodes.value : hierarchicalNodes.value
  // Progressive rendering: only show nodes that have been activated or are completed
  const activeAgents = Object.keys(props.nodeStates)
  const visibleNodes = base.filter((n, i) => {
    if (i === 0) return true // Always show planner
    if (activeAgents.includes(n.data.agent)) return true
    // Show nodes whose predecessors are completed
    const allBaseEdges = props.topology === 'debate' ? debateEdges.value : hierarchicalEdges.value
    const incomingEdges = allBaseEdges.filter(e => e.target === n.id)
    return incomingEdges.some(e => activeAgents.includes(e.source))
  })
  return visibleNodes.map(n => {
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
})

const edges = computed(() => {
  const allEdges = props.topology === 'debate' ? debateEdges.value : hierarchicalEdges.value
  const visibleNodeIds = new Set(nodes.value.map(n => n.id))
  return allEdges.filter(e => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target))
})

watch(() => props.topology, () => setTimeout(() => fitView({ padding: 0.2 }), 100))
// Auto-center when nodes appear or change
watch(() => Object.keys(props.nodeStates).length, () => {
  setTimeout(() => fitView({ padding: 0.2 }), 80)
})
</script>

<template>
  <div class="h-[420px] rounded-xl border border-cyber-border overflow-hidden">
    <VueFlow
      :nodes="nodes"
      :edges="edges"
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
