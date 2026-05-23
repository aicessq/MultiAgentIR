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
}>()

const emit = defineEmits<{ 'select-agent': [agent: string] }>()

const { fitView } = useVueFlow()

function onNodeClick({ node }: { node: any }) {
  emit('select-agent', node.id)
}

// Horizontal layout: left to right
const hierarchicalNodes = [
  { id: 'planner', type: 'agent', position: { x: 0, y: 200 }, data: { label: 'PLANNER', agent: 'planner', status: 'idle' } },
  { id: 'searcher', type: 'agent', position: { x: 220, y: 80 }, data: { label: 'SEARCHER', agent: 'searcher', status: 'idle' } },
  { id: 'reader', type: 'agent', position: { x: 220, y: 320 }, data: { label: 'READER', agent: 'reader', status: 'idle' } },
  { id: 'analyzer', type: 'agent', position: { x: 440, y: 200 }, data: { label: 'ANALYZER', agent: 'analyzer', status: 'idle' } },
  { id: 'critic', type: 'agent', position: { x: 660, y: 200 }, data: { label: 'CRITIC', agent: 'critic', status: 'idle' } },
  { id: 'writer', type: 'agent', position: { x: 880, y: 120 }, data: { label: 'WRITER', agent: 'writer', status: 'idle' } },
  { id: 'validator', type: 'agent', position: { x: 880, y: 320 }, data: { label: 'VALIDATOR', agent: 'validator', status: 'idle' } },
]

const hierarchicalEdges = [
  { id: 'e1', source: 'planner', target: 'searcher', animated: true, type: 'smoothstep' },
  { id: 'e2', source: 'planner', target: 'reader', animated: true, type: 'smoothstep' },
  { id: 'e3', source: 'searcher', target: 'analyzer', animated: true, type: 'smoothstep' },
  { id: 'e4', source: 'reader', target: 'analyzer', animated: true, type: 'smoothstep' },
  { id: 'e5', source: 'analyzer', target: 'critic', animated: true, type: 'smoothstep' },
  { id: 'e6', source: 'critic', target: 'writer', animated: true, type: 'smoothstep' },
  { id: 'e7', source: 'critic', target: 'validator', animated: true, type: 'smoothstep' },
]

const debateNodes = [
  { id: 'planner', type: 'agent', position: { x: 0, y: 200 }, data: { label: 'PLANNER', agent: 'planner', status: 'idle' } },
  { id: 'pro', type: 'agent', position: { x: 250, y: 50 }, data: { label: 'PRO', agent: 'pro', status: 'idle' } },
  { id: 'con', type: 'agent', position: { x: 250, y: 200 }, data: { label: 'CON', agent: 'con', status: 'idle' } },
  { id: 'neutral', type: 'agent', position: { x: 250, y: 350 }, data: { label: 'NEUTRAL', agent: 'neutral', status: 'idle' } },
  { id: 'critic', type: 'agent', position: { x: 500, y: 200 }, data: { label: 'CRITIC', agent: 'critic', status: 'idle' } },
  { id: 'synthesizer', type: 'agent', position: { x: 720, y: 200 }, data: { label: 'SYNTHESIZER', agent: 'synthesizer', status: 'idle' } },
  { id: 'writer', type: 'agent', position: { x: 940, y: 200 }, data: { label: 'WRITER', agent: 'writer', status: 'idle' } },
]

const debateEdges = [
  { id: 'e1', source: 'planner', target: 'pro', animated: true, type: 'smoothstep' },
  { id: 'e2', source: 'planner', target: 'con', animated: true, type: 'smoothstep' },
  { id: 'e3', source: 'planner', target: 'neutral', animated: true, type: 'smoothstep' },
  { id: 'e4', source: 'pro', target: 'critic', animated: true, type: 'smoothstep' },
  { id: 'e5', source: 'con', target: 'critic', animated: true, type: 'smoothstep' },
  { id: 'e6', source: 'neutral', target: 'critic', animated: true, type: 'smoothstep' },
  { id: 'e7', source: 'critic', target: 'synthesizer', animated: true, type: 'smoothstep' },
  { id: 'e8', source: 'synthesizer', target: 'writer', animated: true, type: 'smoothstep' },
]

const nodes = computed(() => {
  const base = props.topology === 'debate' ? debateNodes : hierarchicalNodes
  // Progressive rendering: only show nodes that have been activated or are completed
  const activeAgents = Object.keys(props.nodeStates)
  const visibleNodes = base.filter((n, i) => {
    if (i === 0) return true // Always show planner
    if (activeAgents.includes(n.data.agent)) return true
    // Show nodes whose predecessors are completed
    const edges = props.topology === 'debate' ? debateEdges : hierarchicalEdges
    const incomingEdges = edges.filter(e => e.target === n.id)
    return incomingEdges.some(e => activeAgents.includes(e.source))
  })
  return visibleNodes.map(n => {
    const detail = props.agentDetails?.[n.data.agent]
    return {
      ...n,
      data: {
        ...n.data,
        status: props.nodeStates[n.data.agent] || 'idle',
        model: detail?.model || n.data.model,
        activity: detail?.message,
      },
    }
  })
})

const edges = computed(() => {
  const allEdges = props.topology === 'debate' ? debateEdges : hierarchicalEdges
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
      <MiniMap :pannable :zoomable class="!bg-cyber-card !border-cyber-border" />
    </VueFlow>
  </div>
</template>
