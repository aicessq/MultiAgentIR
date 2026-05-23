<script setup lang="ts">
defineProps<{
  metrics: {
    cost_so_far: number
    latency_ms: number
    model_usage: Record<string, number>
    token_usage: { prompt_tokens: number; completion_tokens: number }
    total_audit_entries: number
  }
}>()

function formatCost(v: number) { return `$${v.toFixed(4)}` }
function formatMs(v: number) { return v > 1000 ? `${(v / 1000).toFixed(1)}s` : `${v.toFixed(0)}ms` }
</script>

<template>
  <div class="grid grid-cols-4 gap-3 px-6">
    <div class="bg-cyber-card rounded-lg p-3 border border-cyber-border">
      <div class="text-[10px] text-gray-500 font-mono uppercase">Cost</div>
      <div class="text-lg font-mono text-cyber-green">{{ formatCost(metrics.cost_so_far) }}</div>
    </div>
    <div class="bg-cyber-card rounded-lg p-3 border border-cyber-border">
      <div class="text-[10px] text-gray-500 font-mono uppercase">Latency</div>
      <div class="text-lg font-mono text-cyber-cyan">{{ formatMs(metrics.latency_ms) }}</div>
    </div>
    <div class="bg-cyber-card rounded-lg p-3 border border-cyber-border">
      <div class="text-[10px] text-gray-500 font-mono uppercase">Tokens</div>
      <div class="text-lg font-mono text-cyber-purple">{{ (metrics.token_usage.prompt_tokens + metrics.token_usage.completion_tokens).toLocaleString() }}</div>
    </div>
    <div class="bg-cyber-card rounded-lg p-3 border border-cyber-border">
      <div class="text-[10px] text-gray-500 font-mono uppercase">LLM Calls</div>
      <div class="text-lg font-mono text-cyber-orange">{{ metrics.total_audit_entries }}</div>
    </div>
  </div>
</template>
