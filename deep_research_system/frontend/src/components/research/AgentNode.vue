<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps<{
  data: {
    label: string
    agent: string
    model?: string
    activity?: string
    status: 'idle' | 'running' | 'completed' | 'error'
    icon?: string
  }
}>()

const statusColor = computed(() => {
  switch (props.data.status) {
    case 'running': return 'border-cyber-cyan shadow-glow animate-pulse-glow'
    case 'completed': return 'border-cyber-green shadow-[0_0_15px_rgba(0,255,136,0.3)]'
    case 'error': return 'border-cyber-pink shadow-[0_0_15px_rgba(255,51,102,0.3)]'
    default: return 'border-cyber-border'
  }
})

const statusIcon = computed(() => {
  switch (props.data.status) {
    case 'running': return '⟳'
    case 'completed': return '✓'
    case 'error': return '✕'
    default: return '○'
  }
})
</script>

<template>
  <div
    class="px-4 py-3 rounded-xl bg-cyber-card/90 backdrop-blur border-2 min-w-[160px] max-w-[200px] transition-all duration-300"
    :class="statusColor"
  >
    <Handle type="target" :position="Position.Left" class="!bg-cyber-cyan !w-2 !h-2" />
    <div class="flex items-center gap-2 mb-1">
      <span class="text-sm" :class="data.status === 'running' ? 'animate-spin' : ''">{{ statusIcon }}</span>
      <span class="font-display text-xs tracking-wider text-cyber-cyan">{{ data.label }}</span>
    </div>
    <div v-if="data.model" class="text-[10px] text-gray-500 font-mono truncate mb-0.5">{{ data.model }}</div>
    <div v-if="data.status === 'running' && data.activity"
         class="text-[9px] text-gray-400 font-mono truncate leading-tight"
         :title="data.activity">
      {{ data.activity }}
    </div>
    <div v-else-if="data.status === 'completed' && data.activity"
         class="text-[9px] text-gray-500 font-mono truncate leading-tight">
      {{ data.activity }}
    </div>
    <Handle type="source" :position="Position.Right" class="!bg-cyber-cyan !w-2 !h-2" />
  </div>
</template>
