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
  supplementary_search: '补充搜索中',
  synthesizer: '综合中',
  writer: '写作中',
  validator: '校验中',
  completed: '已完成',
}

function getStageLabel(stage: string): string {
  if (stageLabels[stage]) return stageLabels[stage]
  // Dynamic h_* debate branches
  if (stage.startsWith('h_')) return `辩论-${stage.slice(2)}`
  // Subtask agents: searcher_sq_1, reader_sq_2, etc.
  const sqMatch = stage.match(/^(\w+)_sq_(\d+)$/)
  if (sqMatch) {
    const parentLabel = stageLabels[sqMatch[1]] || sqMatch[1]
    return `${parentLabel} #${sqMatch[2]}`
  }
  // Repair writer: repair_writer, repair_writer_1, repair_writer_2
  if (stage === 'repair_writer' || stage.startsWith('repair_writer_')) {
    const num = stage.match(/\d+$/)
    return num ? `修复写作中 #${num[0]}` : '修复写作中'
  }
  return stage
}
</script>

<template>
  <div class="px-6 py-3">
    <div class="flex justify-between items-center mb-2">
      <span class="text-xs font-mono text-cyber-cyan">{{ getStageLabel(stage) }}</span>
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
