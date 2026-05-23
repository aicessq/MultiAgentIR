<script setup lang="ts">
import { ref } from 'vue'
import { Search } from '@element-plus/icons-vue'

const emit = defineEmits<{
  submit: [query: string, taskType: string, depth: string]
}>()

const query = ref('')
const taskType = ref('industry_report')
const depth = ref('standard')

const taskTypes = [
  { value: 'industry_report', label: '行业报告' },
  { value: 'company_analysis', label: '公司分析' },
  { value: 'technical_research', label: '技术调研' },
  { value: 'open_question', label: '开放性问题' },
  { value: 'strategy_decision', label: '策略建议' },
  { value: 'general', label: '通用' },
]

const depths = [
  { value: 'quick', label: '快速' },
  { value: 'standard', label: '标准' },
  { value: 'deep', label: '深度' },
]

function handleSubmit() {
  if (!query.value.trim()) return
  emit('submit', query.value, taskType.value, depth.value)
}
</script>

<template>
  <div class="p-6">
    <h1 class="font-display text-2xl text-cyber-cyan mb-6 tracking-wider">DEEP RESEARCH</h1>
    <div class="flex gap-3 items-end">
      <div class="flex-1">
        <el-input
          v-model="query"
          size="large"
          placeholder="输入研究主题..."
          @keyup.enter="handleSubmit"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
      <el-select v-model="taskType" size="large" class="w-36">
        <el-option v-for="t in taskTypes" :key="t.value" :label="t.label" :value="t.value" />
      </el-select>
      <el-select v-model="depth" size="large" class="w-24">
        <el-option v-for="d in depths" :key="d.value" :label="d.label" :value="d.value" />
      </el-select>
      <el-button type="primary" size="large" @click="handleSubmit" :loading="false">
        开始研究
      </el-button>
    </div>
  </div>
</template>
