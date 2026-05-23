<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useConfigStore } from '../stores/config'
import { ElMessage } from 'element-plus'
import { Connection, Refresh } from '@element-plus/icons-vue'

const store = useConfigStore()
const testingSlot = ref('')

const slotLabels: Record<string, string> = {
  search: '搜索/阅读',
  analysis: '分析',
  reasoning: '规划/审稿',
  writing: '写作',
}

onMounted(() => store.loadConfig())

async function handleSave() {
  await store.saveConfig()
  ElMessage.success('配置已保存')
}

async function handleTest(slot: any) {
  testingSlot.value = slot.slot
  try {
    const result = await store.testConnection(slot.model_name, slot.api_key, slot.api_base)
    if (result.connected) {
      ElMessage.success(`${slot.slot}: ${result.message}`)
    } else {
      ElMessage.warning(`${slot.slot}: ${result.message}`)
    }
  } catch {
    ElMessage.error('测试失败')
  } finally {
    testingSlot.value = ''
  }
}

async function handleReset() {
  await store.resetConfig()
  ElMessage.info('配置已重置')
}
</script>

<template>
  <div class="h-full overflow-auto p-6">
    <div class="flex items-center justify-between mb-6">
      <h1 class="font-display text-xl text-cyber-cyan tracking-wider">MODEL CONFIG</h1>
      <div class="flex gap-2">
        <el-button @click="handleReset" :icon="Refresh" size="small">重置</el-button>
        <el-button type="primary" @click="handleSave" size="small">保存配置</el-button>
      </div>
    </div>

    <div class="grid gap-4 max-w-2xl">
      <div
        v-for="slot in store.slots"
        :key="slot.slot"
        class="bg-cyber-card rounded-xl border border-cyber-border p-5"
      >
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2">
            <span class="font-display text-sm text-cyber-cyan tracking-wider">
              {{ slotLabels[slot.slot] || slot.slot }}
            </span>
            <span class="text-[10px] font-mono text-gray-600 bg-cyber-bg px-2 py-0.5 rounded">
              {{ slot.slot }}
            </span>
          </div>
          <div class="flex items-center gap-2">
            <span v-if="slot.has_key" class="w-2 h-2 rounded-full bg-cyber-green" />
            <span v-else class="w-2 h-2 rounded-full bg-gray-600" />
          </div>
        </div>

        <div class="space-y-3">
          <div>
            <label class="text-[10px] text-gray-500 font-mono block mb-1">MODEL NAME</label>
            <el-input v-model="slot.model_name" placeholder="e.g. gpt-4o, deepseek-chat" size="small" />
          </div>
          <div>
            <label class="text-[10px] text-gray-500 font-mono block mb-1">API BASE</label>
            <el-input v-model="slot.api_base" placeholder="https://api.openai.com/v1" size="small" />
          </div>
          <div>
            <label class="text-[10px] text-gray-500 font-mono block mb-1">API KEY</label>
            <el-input v-model="slot.api_key" type="password" show-password placeholder="sk-..." size="small" />
          </div>
          <el-button
            size="small"
            :loading="testingSlot === slot.slot"
            @click="handleTest(slot)"
            :icon="Connection"
            class="!mt-2"
          >
            测试连接
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>
