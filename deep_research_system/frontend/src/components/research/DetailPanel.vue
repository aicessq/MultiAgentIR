<script setup lang="ts">
import { ref, computed } from 'vue'
import { Close } from '@element-plus/icons-vue'

const props = defineProps<{
  agent: string
  detail?: {
    model?: string
    message?: string
    output?: any
    streamContent?: string
    latencyMs?: number
    tokens?: number
    activityLog?: string[]
  }
}>()

const emit = defineEmits<{ close: [] }>()

const tab = ref<'output' | 'log'>('output')

const agentLabels: Record<string, string> = {
  planner: 'PLANNER',
  searcher: 'SEARCHER',
  reader: 'READER',
  analyzer: 'ANALYZER',
  critic: 'CRITIC',
  writer: 'WRITER',
  validator: 'VALIDATOR',
  pro: 'PRO',
  con: 'CON',
  neutral: 'NEUTRAL',
  synthesizer: 'SYNTHESIZER',
}

const formattedOutput = computed(() => {
  if (!props.detail?.output) return ''
  try {
    return JSON.stringify(props.detail.output, null, 2)
  } catch {
    return String(props.detail.output)
  }
})
</script>

<template>
  <div class="bg-cyber-card rounded-xl border border-cyber-border p-4">
    <!-- Header -->
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2">
        <span class="font-display text-sm text-cyber-cyan tracking-wider">
          {{ agentLabels[agent] || agent.toUpperCase() }}
        </span>
        <span v-if="detail?.model" class="text-[10px] font-mono text-gray-500 bg-cyber-bg px-2 py-0.5 rounded">
          {{ detail.model }}
        </span>
      </div>
      <div class="flex items-center gap-3">
        <span v-if="detail?.latencyMs" class="text-[10px] font-mono text-gray-600">
          {{ detail.latencyMs.toFixed(0) }}ms
        </span>
        <span v-if="detail?.tokens" class="text-[10px] font-mono text-gray-600">
          {{ detail.tokens }} tokens
        </span>
        <button class="text-gray-500 hover:text-gray-300 transition-colors" @click="emit('close')">
          <el-icon :size="14"><Close /></el-icon>
        </button>
      </div>
    </div>

    <!-- Status message -->
    <div v-if="detail?.message" class="text-xs text-gray-400 font-mono mb-3 bg-cyber-bg rounded-lg px-3 py-2">
      {{ detail.message }}
    </div>

    <!-- Tabs -->
    <div class="flex gap-4 mb-3 border-b border-cyber-border pb-2">
      <button
        v-for="t in ['output', 'log'] as const"
        :key="t"
        class="text-xs font-display tracking-wider pb-1 transition-colors"
        :class="tab === t ? 'text-cyber-cyan border-b border-cyber-cyan' : 'text-gray-500 hover:text-gray-300'"
        @click="tab = t"
      >
        {{ t === 'output' ? 'OUTPUT' : 'ACTIVITY LOG' }}
      </button>
    </div>

    <!-- Output tab -->
    <div v-if="tab === 'output'" class="text-xs font-mono text-gray-400 bg-cyber-bg rounded-lg p-3 max-h-64 overflow-auto whitespace-pre-wrap break-all">
      <!-- Streaming in progress -->
      <div v-if="detail?.streamContent && !detail?.output" class="text-gray-300">
        {{ detail.streamContent }}<span class="animate-pulse text-cyber-cyan">|</span>
      </div>
      <!-- Completed output -->
      <pre v-else-if="formattedOutput" class="m-0">{{ formattedOutput }}</pre>
      <!-- Waiting -->
      <div v-else class="text-gray-600 italic">等待输出...</div>
    </div>

    <!-- Activity log tab -->
    <div v-if="tab === 'log'" class="max-h-64 overflow-auto space-y-1">
      <div v-if="detail?.activityLog?.length">
        <div
          v-for="(msg, i) in detail.activityLog"
          :key="i"
          class="text-xs font-mono text-gray-400 py-0.5 border-b border-cyber-border/30 last:border-0"
        >
          {{ msg }}
        </div>
      </div>
      <div v-else class="text-xs text-gray-600 italic">暂无活动记录</div>
    </div>
  </div>
</template>
