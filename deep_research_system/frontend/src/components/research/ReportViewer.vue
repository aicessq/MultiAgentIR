<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  report: any
  claimGraph?: any[]
}>()

const sections = computed(() => {
  if (!props.report) return []
  if (props.report.sections) return props.report.sections
  return []
})

const title = computed(() => props.report?.title || '')
const summary = computed(() => {
  const es = props.report?.executive_summary
  if (!es) return ''
  return typeof es === 'string' ? es : es.content || ''
})
const asOfDate = computed(() => props.report?.as_of_date || '')
const riskRegister = computed(() => props.report?.risk_register || [])

function confidenceClass(c: string): string {
  if (c === 'high') return 'text-green-400 bg-green-400/10'
  if (c === 'low') return 'text-red-400 bg-red-400/10'
  return 'text-yellow-400 bg-yellow-400/10'
}

function impactClass(impact: string): string {
  if (impact === 'high') return 'text-red-400'
  if (impact === 'low') return 'text-gray-400'
  return 'text-yellow-400'
}

const claimTypeMap = computed(() => {
  const map: Record<string, string> = {}
  if (props.claimGraph) {
    for (const c of props.claimGraph) {
      if (c.claim_id && c.claim_type) map[c.claim_id] = c.claim_type
    }
  }
  return map
})

function claimTypeClass(claimType: string): string {
  switch (claimType) {
    case 'factual_claim': return 'text-blue-400 bg-blue-400/10 border-blue-400/30'
    case 'analytical_claim': return 'text-green-400 bg-green-400/10 border-green-400/30'
    case 'forecast_claim': return 'text-purple-400 bg-purple-400/10 border-purple-400/30'
    case 'risk_claim': return 'text-orange-400 bg-orange-400/10 border-orange-400/30'
    case 'research_limitation': return 'text-red-400 bg-red-400/10 border-red-400/30'
    default: return 'text-gray-400 bg-gray-400/10 border-gray-400/30'
  }
}

function claimTypeLabel(claimType: string): string {
  switch (claimType) {
    case 'factual_claim': return 'FACT'
    case 'analytical_claim': return 'ANALYSIS'
    case 'forecast_claim': return 'FORECAST'
    case 'risk_claim': return 'RISK'
    case 'research_limitation': return 'LIMITATION'
    default: return claimType?.toUpperCase() || ''
  }
}
</script>

<template>
  <div v-if="report" class="px-6 pb-4">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-2">
      <h2 class="font-display text-xl text-cyber-cyan tracking-wider">{{ title }}</h2>
      <span v-if="asOfDate" class="text-[10px] font-mono text-gray-500 bg-cyber-bg px-2 py-0.5 rounded">
        as of {{ asOfDate }}
      </span>
    </div>

    <!-- Executive Summary -->
    <div v-if="summary" class="mb-6">
      <p class="text-sm text-gray-300 leading-relaxed border-l-2 border-cyber-cyan pl-4">{{ summary }}</p>
    </div>

    <!-- Sections -->
    <div v-for="(section, i) in sections" :key="i" class="mb-6">
      <h3 class="text-sm font-display text-cyber-purple mb-2 tracking-wider">{{ section.heading }}</h3>
      <div class="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">{{ section.content }}</div>

      <!-- Key Claims -->
      <div v-if="section.key_claims?.length" class="mt-3 space-y-1.5">
        <div class="text-[11px] text-cyber-cyan font-display">KEY CLAIMS</div>
        <div v-for="(kc, j) in section.key_claims" :key="j" class="border border-cyber-border/40 rounded-lg p-2">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-[10px] font-mono text-cyber-purple font-bold">{{ kc.claim_id }}</span>
            <span
              v-if="claimTypeMap[kc.claim_id]"
              class="text-[9px] px-1 py-0.5 rounded border font-mono"
              :class="claimTypeClass(claimTypeMap[kc.claim_id])"
            >{{ claimTypeLabel(claimTypeMap[kc.claim_id]) }}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded" :class="confidenceClass(kc.confidence)">
              {{ kc.confidence }}
            </span>
            <span v-if="kc.evidence_ids?.length" class="text-[10px] text-gray-500">
              {{ kc.evidence_ids.length }} evidence
            </span>
          </div>
          <div class="text-xs text-gray-300">{{ kc.sentence }}</div>
        </div>
      </div>

      <!-- Uncertainties -->
      <div v-if="section.uncertainties?.length" class="mt-2 space-y-0.5">
        <div class="text-[11px] text-yellow-400 font-display">UNCERTAINTIES</div>
        <div v-for="(u, j) in section.uncertainties" :key="j" class="text-[11px] text-gray-400">- {{ u }}</div>
      </div>

      <!-- Dropped Claims -->
      <div v-if="section.dropped_claims?.length" class="mt-2 space-y-0.5">
        <div class="text-[11px] text-gray-500 font-display">DROPPED CLAIMS</div>
        <div v-for="(dc, j) in section.dropped_claims" :key="j" class="text-[11px] text-gray-500 italic">- {{ dc }}</div>
      </div>

      <!-- Claim IDs (legacy) -->
      <div v-if="section.claim_ids?.length && !section.key_claims?.length" class="mt-2 flex flex-wrap gap-1">
        <span v-for="(cid, j) in section.claim_ids" :key="j" class="text-[10px] font-mono text-cyber-purple/80 bg-cyber-purple/10 px-2 py-0.5 rounded border border-cyber-purple/20">
          {{ cid }}
        </span>
      </div>

      <!-- Citations -->
      <div v-if="section.citations?.length" class="mt-2 flex flex-wrap gap-1">
        <span v-for="(url, j) in section.citations" :key="j" class="text-[10px] font-mono text-cyber-cyan/60 bg-cyber-cyan/5 px-2 py-0.5 rounded">
          {{ url }}
        </span>
      </div>
    </div>

    <!-- Risk Register -->
    <div v-if="riskRegister.length" class="mt-6">
      <div class="text-sm font-display text-cyber-orange mb-3 tracking-wider">RISK REGISTER</div>
      <div class="space-y-3">
        <div v-for="(risk, i) in riskRegister" :key="i" class="border border-cyber-orange/20 rounded-lg p-3 bg-cyber-orange/5">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-sm text-gray-300 font-bold">{{ risk.risk }}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded" :class="impactClass(risk.impact)">
              {{ risk.likelihood || '?' }} / {{ risk.impact || '?' }}
            </span>
          </div>
          <div v-if="risk.mechanism" class="text-xs text-gray-400 mb-1">{{ risk.mechanism }}</div>
          <div v-if="risk.evidence_claim_ids?.length" class="text-[10px] text-gray-500">
            Evidence: {{ risk.evidence_claim_ids.join(', ') }}
          </div>
          <div v-if="risk.monitoring_indicators?.length" class="text-[10px] text-gray-500 mt-1">
            Monitoring: {{ risk.monitoring_indicators.join(', ') }}
          </div>
          <div v-if="risk.uncertainties?.length" class="text-[10px] text-yellow-400/70 mt-1">
            Uncertainties: {{ risk.uncertainties.join('; ') }}
          </div>
        </div>
      </div>
    </div>

    <!-- Limitations -->
    <div v-if="report.limitations?.length" class="mt-4 p-3 rounded-lg bg-cyber-orange/5 border border-cyber-orange/20">
      <div class="text-xs text-cyber-orange font-display mb-1">LIMITATIONS</div>
      <ul class="text-xs text-gray-400 list-disc list-inside">
        <li v-for="(l, i) in report.limitations" :key="i">{{ l }}</li>
      </ul>
    </div>
  </div>
</template>
