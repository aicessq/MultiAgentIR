<script setup lang="ts">
defineProps<{
  progress: number
  stage: string
}>()

const stageLabels: Record<string, string> = {
  init: '初始化',
  planner: '规划中',
  searcher: '搜索中',
  reader: '阅读中',
  analyzer: '分析中',
  critic: '审稿中',
  synthesizer: '综合中',
  writer: '写作中',
  validator: '校验中',
  completed: '已完成',
}
</script>

<template>
  <div class="px-6 py-3">
    <div class="flex justify-between items-center mb-2">
      <span class="text-xs font-mono text-cyber-cyan">{{ stageLabels[stage] || stage }}</span>
      <span class="text-xs font-mono text-gray-500">{{ progress }}%</span>
    </div>
    <el-progress
      :percentage="progress"
      :stroke-width="6"
      :show-text="false"
      color="#00f0ff"
      class="sci-fi-progress"
    />
  </div>
</template>
