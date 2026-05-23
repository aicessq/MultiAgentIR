<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  report: any
}>()

const sections = computed(() => {
  if (!props.report) return []
  if (props.report.sections) return props.report.sections
  return []
})

const title = computed(() => props.report?.title || '')
const summary = computed(() => props.report?.executive_summary || '')
</script>

<template>
  <div v-if="report" class="px-6 pb-4">
    <h2 class="font-display text-xl text-cyber-cyan mb-2 tracking-wider">{{ title }}</h2>
    <p v-if="summary" class="text-sm text-gray-300 mb-6 leading-relaxed border-l-2 border-cyber-cyan pl-4">{{ summary }}</p>

    <div v-for="(section, i) in sections" :key="i" class="mb-6">
      <h3 class="text-sm font-display text-cyber-purple mb-2 tracking-wider">{{ section.heading }}</h3>
      <div class="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">{{ section.content }}</div>
      <div v-if="section.claim_ids?.length" class="mt-2 flex flex-wrap gap-1">
        <span v-for="(cid, j) in section.claim_ids" :key="j" class="text-[10px] font-mono text-cyber-purple/80 bg-cyber-purple/10 px-2 py-0.5 rounded border border-cyber-purple/20">
          {{ cid }}
        </span>
      </div>
      <div v-if="section.citations?.length" class="mt-2 flex flex-wrap gap-1">
        <span v-for="(url, j) in section.citations" :key="j" class="text-[10px] font-mono text-cyber-cyan/60 bg-cyber-cyan/5 px-2 py-0.5 rounded">
          {{ url }}
        </span>
      </div>
    </div>

    <div v-if="report.limitations?.length" class="mt-4 p-3 rounded-lg bg-cyber-orange/5 border border-cyber-orange/20">
      <div class="text-xs text-cyber-orange font-display mb-1">LIMITATIONS</div>
      <ul class="text-xs text-gray-400 list-disc list-inside">
        <li v-for="(l, i) in report.limitations" :key="i">{{ l }}</li>
      </ul>
    </div>
  </div>
</template>
