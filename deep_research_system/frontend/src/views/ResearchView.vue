<script setup lang="ts">
import { computed, ref } from 'vue'
import { useResearchStore } from '../stores/research'
import { ElMessage } from 'element-plus'
import { exportMarkdown, exportPdf, exportWord } from '../utils/export'
import ResearchForm from '../components/research/ResearchForm.vue'
import TopologyGraph from '../components/research/TopologyGraph.vue'
import ProgressBar from '../components/research/ProgressBar.vue'
import MetricsCard from '../components/research/MetricsCard.vue'
import ReportViewer from '../components/research/ReportViewer.vue'
import AuditTrail from '../components/research/AuditTrail.vue'
import DetailPanel from '../components/research/DetailPanel.vue'

const store = useResearchStore()
const selectedAgent = ref<string | null>(null)

const topology = computed(() => store.currentTask?.selected_topology || 'hierarchical')
const report = computed(() => store.currentTask?.result?.report)
const metrics = computed(() => store.currentTask?.result?.metrics)
const trail = computed(() => store.currentTask?.result?.audit_trail || [])

async function handleSubmit(query: string, taskType: string, depth: string) {
  selectedAgent.value = null
  store.reset()
  await store.submitResearch(query, taskType, depth)
}

function handleSelectAgent(agent: string) {
  selectedAgent.value = selectedAgent.value === agent ? null : agent
}

async function handleCancel() {
  if (!store.currentTask) return
  try {
    await store.cancelTask(store.currentTask.task_id)
    ElMessage.info('已发送终止请求')
  } catch {
    ElMessage.error('终止失败')
  }
}
</script>

<template>
  <div class="h-full overflow-auto">
    <ResearchForm @submit="handleSubmit" />

    <div v-if="store.currentTask" class="px-6 pb-4">
      <!-- Topology label -->
      <div class="flex items-center gap-2 mb-3">
        <span class="text-[10px] font-display tracking-widest text-gray-500">TOPOLOGY</span>
        <span class="text-xs font-mono px-2 py-0.5 rounded border"
          :class="topology === 'debate' ? 'text-cyber-purple border-cyber-purple/30 bg-cyber-purple/10' : 'text-cyber-cyan border-cyber-cyan/30 bg-cyber-cyan/10'">
          {{ topology.toUpperCase() }}
        </span>
        <span class="text-[10px] font-mono text-gray-600 ml-auto">{{ store.currentTask.task_id }}</span>
        <el-button
          v-if="store.currentTask.status === 'running'"
          type="danger"
          size="small"
          plain
          @click="handleCancel"
          class="!ml-2"
        >
          终止
        </el-button>
        <el-dropdown v-if="report" trigger="click" class="!ml-2">
          <el-button size="small" plain>
            下载报告
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="exportMarkdown(report)">导出 Markdown</el-dropdown-item>
              <el-dropdown-item @click="exportPdf(report)">导出 PDF</el-dropdown-item>
              <el-dropdown-item @click="exportWord(report)">导出 Word</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <!-- Progress -->
      <ProgressBar :progress="store.currentTask.progress" :stage="store.currentTask.current_stage" />

      <!-- Topology Graph -->
      <div class="mt-3">
        <TopologyGraph
          :topology="topology"
          :node-states="store.nodeStates"
          :agent-details="store.agentDetails"
          @select-agent="handleSelectAgent"
        />
      </div>

      <!-- Agent Detail Panel (on click) -->
      <div v-if="selectedAgent" class="mt-3">
        <DetailPanel
          :agent="selectedAgent"
          :detail="store.agentDetails[selectedAgent]"
          @close="selectedAgent = null"
        />
      </div>

      <!-- Activity Log -->
      <div v-if="store.events.length" class="mt-3 bg-cyber-card rounded-xl border border-cyber-border px-6 py-4">
        <h3 class="font-display text-xs text-cyber-cyan mb-3 tracking-wider">ACTIVITY LOG</h3>
        <div class="max-h-48 overflow-auto space-y-0.5">
          <div
            v-for="(event, i) in store.events"
            :key="i"
            class="text-xs font-mono text-gray-400 py-0.5 flex gap-2"
          >
            <span class="text-gray-600 shrink-0">{{ event._time }}</span>
            <span v-if="event.agent" class="text-cyber-cyan shrink-0">[{{ event.agent }}]</span>
            <span class="truncate">{{ event.message || event.type }}</span>
          </div>
        </div>
      </div>

      <!-- Metrics -->
      <div v-if="metrics" class="mt-4">
        <MetricsCard :metrics="metrics" />
      </div>

      <!-- Report -->
      <div v-if="report" class="mt-4 bg-cyber-card rounded-xl border border-cyber-border">
        <div class="flex items-center justify-between px-6 pt-4 pb-2">
          <h3 class="font-display text-xs text-cyber-cyan tracking-wider">REPORT</h3>
          <div class="flex gap-2">
            <button
              class="px-3 py-1 text-xs font-mono rounded border border-cyber-cyan/40 text-cyber-cyan hover:bg-cyber-cyan/10 transition-colors"
              @click="exportMarkdown(report)"
            >MD</button>
            <button
              class="px-3 py-1 text-xs font-mono rounded border border-cyber-purple/40 text-cyber-purple hover:bg-cyber-purple/10 transition-colors"
              @click="exportPdf(report)"
            >PDF</button>
            <button
              class="px-3 py-1 text-xs font-mono rounded border border-cyber-green/40 text-cyber-green hover:bg-cyber-green/10 transition-colors"
              @click="exportWord(report)"
            >Word</button>
          </div>
        </div>
        <ReportViewer :report="report" />
      </div>

      <!-- Audit Trail -->
      <div v-if="trail.length" class="mt-4 bg-cyber-card rounded-xl border border-cyber-border">
        <AuditTrail :trail="trail" />
      </div>

      <!-- Error -->
      <div v-if="store.currentTask.status === 'failed'" class="mt-4 p-4 rounded-xl bg-cyber-pink/10 border border-cyber-pink/30">
        <div class="text-sm text-cyber-pink font-display">ERROR</div>
        <div class="text-xs text-gray-400 mt-1 font-mono">{{ store.currentTask.error }}</div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!store.currentTask" class="flex flex-col items-center justify-center h-[60vh] text-gray-600">
      <div class="font-display text-4xl mb-4 tracking-widest opacity-20">DR</div>
      <div class="text-sm">输入研究主题开始</div>
    </div>
  </div>
</template>
