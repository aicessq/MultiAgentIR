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
  synthesizer: 'SYNTHESIZER',
  supplementary_search: 'SUPPLEMENTARY SEARCH',
}

function getAgentLabel(agent: string): string {
  if (agentLabels[agent]) return agentLabels[agent]
  if (agent.startsWith('h_')) return `HYPOTHESIS ${agent.slice(2)}`
  return agent.toUpperCase()
}

// Severity color mapping
function severityClass(severity: string): string {
  switch (severity) {
    case 'critical': return 'text-red-400 bg-red-400/10 border-red-400/30'
    case 'high': return 'text-orange-400 bg-orange-400/10 border-orange-400/30'
    case 'medium': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30'
    case 'low': return 'text-gray-400 bg-gray-400/10 border-gray-400/30'
    default: return 'text-gray-400 bg-gray-400/10 border-gray-400/30'
  }
}

function confidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'text-green-400'
  if (confidence >= 0.6) return 'text-yellow-400'
  return 'text-red-400'
}

// Structured output rendering per agent type
const isPlanner = computed(() => props.agent === 'planner')
const isSearcher = computed(() => props.agent === 'searcher')
const isReader = computed(() => props.agent === 'reader')
const isAnalyzer = computed(() => props.agent === 'analyzer')
const isCritic = computed(() => props.agent === 'critic')
const isWriter = computed(() => props.agent === 'writer')
const isValidator = computed(() => props.agent === 'validator')
const isSynthesizer = computed(() => props.agent === 'synthesizer')
const isDebateBranch = computed(() => props.agent.startsWith('h_'))

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
          {{ getAgentLabel(agent) }}
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
    <div v-if="tab === 'output'" class="text-xs font-mono text-gray-400 bg-cyber-bg rounded-lg p-3 max-h-80 overflow-auto">
      <!-- Streaming in progress -->
      <div v-if="detail?.streamContent && !detail?.output" class="text-gray-300 whitespace-pre-wrap break-all">
        {{ detail.streamContent }}<span class="animate-pulse text-cyber-cyan">|</span>
      </div>

      <!-- ===== PLANNER output ===== -->
      <div v-else-if="isPlanner && detail?.output" class="space-y-3">
        <div v-if="detail.output.research_goal" class="text-gray-300">
          <span class="text-cyber-cyan">目标：</span>{{ detail.output.research_goal }}
        </div>
        <div v-if="detail.output.assumptions?.length" class="text-gray-400">
          <span class="text-cyber-purple">假设：</span>
          <span v-for="(a, i) in detail.output.assumptions" :key="i">{{ a }}<span v-if="i < detail.output.assumptions.length - 1">; </span></span>
        </div>
        <div v-if="detail.output.sub_questions?.length" class="space-y-2">
          <div class="text-cyber-cyan text-[11px]">子问题</div>
          <div v-for="sq in detail.output.sub_questions" :key="sq.id" class="border border-cyber-border/50 rounded-lg p-2">
            <div class="text-gray-300"><span class="text-cyber-purple">{{ sq.id }}：</span>{{ sq.question }}</div>
            <div v-if="sq.hypothesis" class="text-gray-400 mt-1"><span class="text-yellow-400">假设：</span>{{ sq.hypothesis }}</div>
            <div v-if="sq.scope" class="text-gray-500 mt-1"><span class="text-gray-400">范围：</span>{{ sq.scope }}</div>
            <div v-if="sq.counter_evidence_needed?.length" class="text-gray-500 mt-1">
              <span class="text-red-400">反证需求：</span>{{ sq.counter_evidence_needed.join('; ') }}
            </div>
          </div>
        </div>
        <div v-if="detail.output.hypotheses?.length" class="space-y-1">
          <div class="text-cyber-purple text-[11px]">竞争假设</div>
          <div v-for="(h, i) in detail.output.hypotheses" :key="i" class="text-gray-300 border-l-2 border-cyber-purple/50 pl-2">{{ h }}</div>
        </div>
      </div>

      <!-- ===== SEARCHER output ===== -->
      <div v-else-if="isSearcher && detail?.output" class="space-y-3">
        <div v-if="detail.output.sub_question_id" class="text-gray-400">
          <span class="text-cyber-cyan">子问题：</span>{{ detail.output.sub_question_id }}
        </div>
        <div v-if="detail.output.sources?.length" class="space-y-2">
          <div class="text-cyber-cyan text-[11px]">来源 ({{ detail.output.sources.length }})</div>
          <div v-for="(src, i) in detail.output.sources" :key="i" class="border border-cyber-border/50 rounded-lg p-2">
            <div class="text-gray-300 text-[11px] truncate">{{ src.title }}</div>
            <div class="text-gray-500 text-[10px] truncate">{{ src.url }}</div>
            <div class="flex gap-2 mt-1">
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-cyber-cyan/10 text-cyber-cyan">{{ src.source_type }}</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded" :class="src.credibility_score >= 0.8 ? 'bg-green-400/10 text-green-400' : src.credibility_score >= 0.6 ? 'bg-yellow-400/10 text-yellow-400' : 'bg-red-400/10 text-red-400'">
                可信度 {{ src.credibility_score }}
              </span>
              <span v-if="src.publish_date" class="text-[10px] text-gray-500">{{ src.publish_date }}</span>
            </div>
            <div v-if="src.snippet" class="text-gray-400 text-[10px] mt-1 line-clamp-2">{{ src.snippet }}</div>
          </div>
        </div>
      </div>

      <!-- ===== READER output ===== -->
      <div v-else-if="isReader && detail?.output" class="space-y-3">
        <div v-if="detail.output.atomic_facts?.length" class="space-y-1">
          <div class="text-cyber-cyan text-[11px]">原子事实 ({{ detail.output.atomic_facts.length }})</div>
          <div v-for="(fact, i) in detail.output.atomic_facts" :key="i" class="text-gray-300 border-l-2 border-cyber-cyan/30 pl-2 text-[11px]">{{ fact }}</div>
        </div>
        <div v-if="detail.output.evidence?.length" class="space-y-2">
          <div class="text-cyber-cyan text-[11px]">证据 ({{ detail.output.evidence.length }})</div>
          <div v-for="(ev, i) in detail.output.evidence" :key="i" class="border border-cyber-border/50 rounded-lg p-2">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-cyber-purple text-[10px] font-bold">{{ ev.evidence_id }}</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded" :class="ev.supports === 'supports' ? 'bg-green-400/10 text-green-400' : ev.supports === 'contradicts' ? 'bg-red-400/10 text-red-400' : 'bg-gray-400/10 text-gray-400'">
                {{ ev.supports }}
              </span>
              <span class="text-[10px]" :class="confidenceColor(ev.confidence)">置信度 {{ ev.confidence }}</span>
            </div>
            <div class="text-gray-300 text-[11px]">{{ ev.claim }}</div>
            <div v-if="ev.quote_or_summary" class="text-gray-500 text-[10px] mt-1 italic">"{{ ev.quote_or_summary }}"</div>
            <div class="text-gray-600 text-[10px] mt-1 truncate">{{ ev.source_url }}</div>
            <div v-if="ev.limitations?.length" class="text-orange-400/60 text-[10px] mt-1">局限：{{ ev.limitations.join('; ') }}</div>
          </div>
        </div>
        <div v-if="detail.output.uncertainties?.length" class="space-y-1">
          <div class="text-yellow-400 text-[11px]">不确定性</div>
          <div v-for="(u, i) in detail.output.uncertainties" :key="i" class="text-gray-400 text-[11px]">- {{ u }}</div>
        </div>
      </div>

      <!-- ===== ANALYZER output ===== -->
      <div v-else-if="isAnalyzer && detail?.output" class="space-y-3">
        <div v-if="detail.output.confidence_level" class="text-gray-400">
          <span class="text-cyber-cyan">整体置信度：</span>{{ detail.output.confidence_level }}
        </div>
        <div v-if="detail.output.claims?.length" class="space-y-2">
          <div class="text-cyber-cyan text-[11px]">论点图谱 ({{ detail.output.claims.length }})</div>
          <div v-for="claim in detail.output.claims" :key="claim.claim_id" class="border border-cyber-border/50 rounded-lg p-2">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-cyber-purple text-[10px] font-bold">{{ claim.claim_id }}</span>
              <span class="text-[10px]" :class="confidenceColor(claim.confidence)">置信度 {{ claim.confidence }}</span>
              <span v-if="claim.supporting_count" class="text-green-400 text-[10px]">+{{ claim.supporting_count }}</span>
              <span v-if="claim.contradicting_count" class="text-red-400 text-[10px]">-{{ claim.contradicting_count }}</span>
            </div>
            <div class="text-gray-300 text-[11px]">{{ claim.claim_text }}</div>
            <div v-if="claim.evidence_ids?.length" class="text-gray-500 text-[10px] mt-1">
              证据：{{ claim.evidence_ids.join(', ') }}
            </div>
            <div v-if="claim.caveats?.length" class="text-orange-400/60 text-[10px] mt-1">限制：{{ claim.caveats.join('; ') }}</div>
          </div>
        </div>
        <div v-if="detail.output.trends?.length" class="space-y-1">
          <div class="text-cyber-cyan text-[11px]">趋势</div>
          <div v-for="(t, i) in detail.output.trends" :key="i" class="text-gray-300 text-[11px]">- {{ t }}</div>
        </div>
        <div v-if="detail.output.contradictions?.length" class="space-y-1">
          <div class="text-red-400 text-[11px]">矛盾点</div>
          <div v-for="(c, i) in detail.output.contradictions" :key="i" class="text-gray-300 text-[11px]">- {{ c }}</div>
        </div>
        <div v-if="detail.output.gaps?.length" class="space-y-1">
          <div class="text-yellow-400 text-[11px]">研究空白</div>
          <div v-for="(g, i) in detail.output.gaps" :key="i" class="text-gray-400 text-[11px]">- {{ g }}</div>
        </div>
      </div>

      <!-- ===== CRITIC output ===== -->
      <div v-else-if="isCritic && detail?.output" class="space-y-3">
        <div v-if="detail.output.overall_assessment" class="flex items-center gap-2">
          <span class="text-cyber-cyan text-[11px]">评估：</span>
          <span class="text-[10px] px-2 py-0.5 rounded font-bold" :class="detail.output.overall_assessment === 'pass' ? 'bg-green-400/10 text-green-400' : detail.output.overall_assessment === 'needs_research' ? 'bg-orange-400/10 text-orange-400' : 'bg-yellow-400/10 text-yellow-400'">
            {{ detail.output.overall_assessment }}
          </span>
          <span v-if="detail.output.needs_more_research" class="text-[10px] px-2 py-0.5 rounded bg-red-400/10 text-red-400 border border-red-400/30">需要补搜</span>
        </div>
        <div v-if="detail.output.findings?.length" class="space-y-2">
          <div class="text-cyber-cyan text-[11px]">审稿发现 ({{ detail.output.findings.length }})</div>
          <div v-for="(f, i) in detail.output.findings" :key="i" class="border border-cyber-border/50 rounded-lg p-2">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-[10px] px-1.5 py-0.5 rounded border font-bold" :class="severityClass(f.severity)">{{ f.severity }}</span>
              <span class="text-gray-500 text-[10px]">{{ f.target_type }}: {{ f.target_id }}</span>
            </div>
            <div class="text-gray-300 text-[11px]">{{ f.issue_description }}</div>
            <div v-if="f.fix_instruction" class="text-cyber-cyan/80 text-[11px] mt-1">修复：{{ f.fix_instruction }}</div>
            <div v-if="f.suggested_search_queries?.length" class="text-gray-500 text-[10px] mt-1">
              补搜建议：{{ f.suggested_search_queries.join('; ') }}
            </div>
          </div>
        </div>
        <div v-if="detail.output.missing_evidence?.length" class="space-y-1">
          <div class="text-orange-400 text-[11px]">缺失证据</div>
          <div v-for="(m, i) in detail.output.missing_evidence" :key="i" class="text-gray-400 text-[11px]">- {{ m }}</div>
        </div>
        <div v-if="detail.output.logic_flaws?.length" class="space-y-1">
          <div class="text-red-400 text-[11px]">逻辑漏洞</div>
          <div v-for="(l, i) in detail.output.logic_flaws" :key="i" class="text-gray-400 text-[11px]">- {{ l }}</div>
        </div>
      </div>

      <!-- ===== WRITER output ===== -->
      <div v-else-if="isWriter && detail?.output" class="space-y-3">
        <div v-if="detail.output.title" class="text-gray-300 font-bold">{{ detail.output.title }}</div>
        <div v-if="detail.output.executive_summary" class="text-gray-400 text-[11px] border-l-2 border-cyber-cyan/50 pl-2 line-clamp-3">{{ detail.output.executive_summary }}</div>
        <div v-if="detail.output.sections?.length" class="space-y-1">
          <div class="text-cyber-cyan text-[11px]">章节 ({{ detail.output.sections.length }})</div>
          <div v-for="(sec, i) in detail.output.sections" :key="i" class="flex items-center gap-2 text-[11px]">
            <span class="text-gray-300">{{ sec.heading }}</span>
            <span v-if="sec.claim_ids?.length" class="text-cyber-purple text-[10px]">[{{ sec.claim_ids.join(', ') }}]</span>
            <span v-if="sec.citations?.length" class="text-gray-500 text-[10px]">{{ sec.citations.length }} 条引用</span>
          </div>
        </div>
        <div v-if="detail.output.limitations?.length" class="text-orange-400 text-[11px]">
          局限性：{{ detail.output.limitations.length }} 条
        </div>
      </div>

      <!-- ===== VALIDATOR output ===== -->
      <div v-else-if="isValidator && detail?.output" class="space-y-3">
        <div class="flex items-center gap-3">
          <span class="text-[11px] px-2 py-0.5 rounded font-bold" :class="detail.output.valid ? 'bg-green-400/10 text-green-400 border border-green-400/30' : 'bg-red-400/10 text-red-400 border border-red-400/30'">
            {{ detail.output.valid ? '通过' : '未通过' }}
          </span>
          <span v-if="detail.output.score" class="text-gray-300 text-[11px]">评分：{{ detail.output.score }}</span>
        </div>
        <div v-if="detail.output.quality_scores" class="grid grid-cols-2 gap-2">
          <div v-for="(val, key) in detail.output.quality_scores" :key="key" class="text-[10px]">
            <span class="text-gray-500">{{ key }}：</span>
            <span class="text-gray-300">{{ val }}</span>
          </div>
        </div>
        <div v-if="detail.output.issues?.length" class="space-y-1">
          <div class="text-red-400 text-[11px]">问题 ({{ detail.output.issues.length }})</div>
          <div v-for="(issue, i) in detail.output.issues" :key="i" class="text-gray-400 text-[11px] border-l-2 border-red-400/30 pl-2">
            <span v-if="issue.severity" class="text-[10px] px-1 py-0.5 rounded mr-1" :class="severityClass(issue.severity)">{{ issue.severity }}</span>
            {{ issue.problem || issue }}
            <span v-if="issue.location" class="text-gray-500"> ({{ issue.location }})</span>
          </div>
        </div>
        <div v-if="detail.output.warnings?.length" class="space-y-1">
          <div class="text-yellow-400 text-[11px]">警告</div>
          <div v-for="(w, i) in detail.output.warnings" :key="i" class="text-gray-400 text-[11px]">- {{ w }}</div>
        </div>
      </div>

      <!-- ===== SYNTHESIZER output ===== -->
      <div v-else-if="isSynthesizer && detail?.output" class="space-y-3">
        <div v-if="detail.output.conditional_conclusions?.length" class="space-y-1">
          <div class="text-cyber-cyan text-[11px]">条件化结论</div>
          <div v-for="(c, i) in detail.output.conditional_conclusions" :key="i" class="text-gray-300 text-[11px] border-l-2 border-cyber-cyan/30 pl-2">{{ c }}</div>
        </div>
        <div v-if="detail.output.key_disagreements?.length" class="space-y-1">
          <div class="text-red-400 text-[11px]">关键分歧</div>
          <div v-for="(d, i) in detail.output.key_disagreements" :key="i" class="text-gray-300 text-[11px]">
            <template v-if="typeof d === 'string'">- {{ d }}</template>
            <template v-else>
              <div class="border border-cyber-border/50 rounded p-1.5">
                <div class="text-gray-300">{{ d.question }}</div>
                <div v-if="d.positions" class="text-gray-500 text-[10px] mt-1">
                  <span v-for="(pos, branch) in d.positions" :key="branch" class="mr-2">{{ branch }}: {{ pos }}</span>
                </div>
              </div>
            </template>
          </div>
        </div>
        <div v-if="detail.output.consensus_points?.length" class="space-y-1">
          <div class="text-green-400 text-[11px]">共识</div>
          <div v-for="(c, i) in detail.output.consensus_points" :key="i" class="text-gray-300 text-[11px]">- {{ c }}</div>
        </div>
        <div v-if="detail.output.hypothesis_assessment?.length" class="space-y-2">
          <div class="text-cyber-purple text-[11px]">假设评估</div>
          <div v-for="(ha, i) in detail.output.hypothesis_assessment" :key="i" class="border border-cyber-border/50 rounded-lg p-2">
            <div class="text-gray-300 text-[11px]">{{ ha.hypothesis }}</div>
            <div class="flex gap-2 mt-1">
              <span class="text-[10px] px-1.5 py-0.5 rounded font-bold" :class="ha.verdict === 'supported' ? 'bg-green-400/10 text-green-400' : ha.verdict === 'refuted' ? 'bg-red-400/10 text-red-400' : ha.verdict === 'partially_supported' ? 'bg-yellow-400/10 text-yellow-400' : 'bg-gray-400/10 text-gray-400'">
                {{ ha.verdict }}
              </span>
              <span class="text-[10px]" :class="confidenceColor(ha.confidence)">置信度 {{ ha.confidence }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ===== DEBATE BRANCH output (h_*) ===== -->
      <div v-else-if="isDebateBranch && detail?.output" class="space-y-3">
        <div v-if="detail.output.hypothesis" class="text-gray-300">
          <span class="text-cyber-purple">假设：</span>{{ detail.output.hypothesis }}
        </div>
        <div v-if="detail.output.position" class="text-gray-400 text-[11px]">
          <span class="text-cyber-cyan">立场：</span>{{ detail.output.position }}
        </div>
        <div v-if="detail.output.supporting_claims?.length" class="space-y-1">
          <div class="text-green-400 text-[11px]">支撑性判断</div>
          <div v-for="(c, i) in detail.output.supporting_claims" :key="i" class="text-gray-300 text-[11px]">+ {{ c }}</div>
        </div>
        <div v-if="detail.output.contradicting_claims?.length" class="space-y-1">
          <div class="text-red-400 text-[11px]">反驳性判断</div>
          <div v-for="(c, i) in detail.output.contradicting_claims" :key="i" class="text-gray-300 text-[11px]">- {{ c }}</div>
        </div>
        <div v-if="detail.output.evidence?.length" class="space-y-2">
          <div class="text-cyber-cyan text-[11px]">证据 ({{ detail.output.evidence.length }})</div>
          <div v-for="(ev, i) in detail.output.evidence" :key="i" class="border border-cyber-border/50 rounded-lg p-2">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-cyber-purple text-[10px] font-bold">{{ ev.evidence_id }}</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded" :class="ev.supports === 'supports' ? 'bg-green-400/10 text-green-400' : ev.supports === 'contradicts' ? 'bg-red-400/10 text-red-400' : 'bg-gray-400/10 text-gray-400'">
                {{ ev.supports }}
              </span>
            </div>
            <div class="text-gray-300 text-[11px]">{{ ev.claim }}</div>
          </div>
        </div>
      </div>

      <!-- ===== Fallback: raw JSON ===== -->
      <pre v-else-if="formattedOutput" class="m-0 whitespace-pre-wrap break-all">{{ formattedOutput }}</pre>

      <!-- Waiting -->
      <div v-else class="text-gray-600 italic">等待输出...</div>
    </div>

    <!-- Activity log tab -->
    <div v-if="tab === 'log'" class="max-h-80 overflow-auto space-y-1">
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
