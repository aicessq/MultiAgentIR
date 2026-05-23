import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createResearch, getResearch, streamResearch, cancelResearch, type TaskResult } from '../api/research'

export interface AgentDetail {
  model?: string
  message?: string
  output?: any
  streamContent?: string
  latencyMs?: number
  tokens?: number
  activityLog: string[]
}

export const useResearchStore = defineStore('research', () => {
  const currentTask = ref<TaskResult | null>(null)
  const loading = ref(false)
  const events = ref<any[]>([])
  const nodeStates = ref<Record<string, string>>({})
  const agentDetails = ref<Record<string, AgentDetail>>({})
  let _sseSource: EventSource | null = null
  let _pollInterval: ReturnType<typeof setInterval> | null = null
  let _tokenBuffer: Record<string, string> = {}
  let _tokenFlushTimer: ReturnType<typeof setTimeout> | null = null

  async function submitResearch(query: string, taskType: string, depth: string) {
    loading.value = true
    events.value = []
    nodeStates.value = {}
    agentDetails.value = {}

    try {
      const task = await createResearch({ query, task_type: taskType, depth })
      currentTask.value = task

      // Wire up SSE for real-time events
      _sseSource = streamResearch(task.task_id, (event) => {
        addEvent(event)
      })

      // Fallback polling in case SSE drops
      pollTask(task.task_id)
    } catch (e: any) {
      loading.value = false
      throw e
    }
  }

  function pollTask(taskId: string) {
    if (_pollInterval) clearInterval(_pollInterval)
    _pollInterval = setInterval(async () => {
      try {
        const task = await getResearch(taskId)
        currentTask.value = task

        if (task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') {
          clearInterval(_pollInterval!)
          _pollInterval = null
          loading.value = false
          if (_sseSource) {
            _sseSource.close()
            _sseSource = null
          }
        }
      } catch {
        if (_pollInterval) clearInterval(_pollInterval)
        _pollInterval = null
        loading.value = false
      }
    }, 2000)
  }

  function addEvent(event: any) {
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false })

    // Skip stream tokens — they go through the batched token buffer instead
    if (event.type === 'agent_stream_token') {
      if (event.agent) {
        if (!_tokenBuffer[event.agent]) _tokenBuffer[event.agent] = ''
        _tokenBuffer[event.agent] += event.token
        if (!_tokenFlushTimer) {
          _tokenFlushTimer = setTimeout(flushTokens, 50)
        }
      }
      return
    }

    events.value.push({ ...event, _time: timestamp })
    // Cap events array to prevent DOM bloat
    if (events.value.length > 200) {
      events.value.splice(0, events.value.length - 200)
    }

    if (event.agent) {
      // Ensure agent detail exists
      if (!agentDetails.value[event.agent]) {
        agentDetails.value[event.agent] = { activityLog: [] }
      }
      const detail = agentDetails.value[event.agent]

      // Update node state based on event type
      if (event.type === 'stage_start') {
        nodeStates.value[event.agent] = 'running'
      } else if (event.type === 'stage_complete') {
        nodeStates.value[event.agent] = 'completed'
      }

      // Track agent details from intermediate events
      if (event.type === 'agent_model_selected') {
        detail.model = event.model
        detail.activityLog.push(`[${timestamp}] ${event.message}`)
      }
      if (event.type === 'agent_thinking') {
        detail.message = event.message
        if (event.latency_ms) detail.latencyMs = event.latency_ms
        if (event.tokens) detail.tokens = event.tokens
        detail.activityLog.push(`[${timestamp}] ${event.message}`)
      }
      if (event.type === 'agent_output') {
        detail.output = event.output
        detail.message = event.message
        detail.activityLog.push(`[${timestamp}] ${event.message}`)
      }
      // agent_stream_token is handled in the early return above
      if (event.type === 'subtask_complete') {
        detail.activityLog.push(`[${timestamp}] ${event.message}`)
      }
    }

    if (event.progress && currentTask.value) {
      currentTask.value.progress = event.progress
    }

    // Close SSE on done or cancelled
    if (event.type === 'done' || event.type === 'cancelled') {
      flushTokens()  // flush any remaining buffered tokens
      loading.value = false
      // Update task with final result from done event
      if (event.type === 'done' && event.result && currentTask.value) {
        currentTask.value.result = event.result
        currentTask.value.status = 'completed'
        currentTask.value.progress = 100
      }
      if (event.type === 'cancelled' && currentTask.value) {
        currentTask.value.status = 'cancelled'
      }
      if (_sseSource) {
        _sseSource.close()
        _sseSource = null
      }
      if (_pollInterval) {
        clearInterval(_pollInterval)
        _pollInterval = null
      }
    }
  }

  function flushTokens() {
    _tokenFlushTimer = null
    for (const [agent, tokens] of Object.entries(_tokenBuffer)) {
      if (!tokens) continue
      if (!agentDetails.value[agent]) {
        agentDetails.value[agent] = { activityLog: [] }
      }
      const detail = agentDetails.value[agent]
      if (!detail.streamContent) detail.streamContent = ''
      detail.streamContent += tokens
      detail.message = detail.streamContent.slice(-80)
    }
    _tokenBuffer = {}
  }

  async function cancelTask(taskId: string) {
    await cancelResearch(taskId)
  }

  function reset() {
    currentTask.value = null
    loading.value = false
    events.value = []
    nodeStates.value = {}
    agentDetails.value = {}
    _tokenBuffer = {}
    if (_tokenFlushTimer) {
      clearTimeout(_tokenFlushTimer)
      _tokenFlushTimer = null
    }
    if (_sseSource) {
      _sseSource.close()
      _sseSource = null
    }
    if (_pollInterval) {
      clearInterval(_pollInterval)
      _pollInterval = null
    }
  }

  return { currentTask, loading, events, nodeStates, agentDetails, submitResearch, cancelTask, addEvent, reset }
})
