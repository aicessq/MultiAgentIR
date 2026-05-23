<script setup lang="ts">
defineProps<{
  trail: Array<{
    agent: string
    model: string
    prompt_version: string
    token_in: number
    token_out: number
    cost: number
    latency_ms: number
  }>
}>()
</script>

<template>
  <div class="px-6 py-4">
    <h3 class="font-display text-xs text-cyber-purple mb-3 tracking-wider">AUDIT TRAIL</h3>
    <el-table :data="trail" size="small" class="sci-fi-table">
      <el-table-column prop="agent" label="Agent" width="100" />
      <el-table-column prop="model" label="Model" width="140" />
      <el-table-column label="Tokens" width="120">
        <template #default="{ row }">
          <span class="font-mono text-xs">{{ row.token_in }}→{{ row.token_out }}</span>
        </template>
      </el-table-column>
      <el-table-column label="Cost" width="100">
        <template #default="{ row }">
          <span class="font-mono text-xs text-cyber-green">${{ row.cost.toFixed(4) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="Latency" width="100">
        <template #default="{ row }">
          <span class="font-mono text-xs">{{ row.latency_ms.toFixed(0) }}ms</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
