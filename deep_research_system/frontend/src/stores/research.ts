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
      }, () => {
        // SSE error callback — connection dropped
        _sseSource = null
        if (loading.value) {
          loading.value = false
        }
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
        // Guard: skip if a new task has been started since this poll was scheduled
        if (currentTask.value?.task_id && currentTask.value.task_id !== taskId) return
        // Preserve existing result if poll response doesn't include one
        if (!task.result && currentTask.value?.result) {
          task.result = currentTask.value.result
        }
        // Preserve report from report_update if poll result has no report
        if (task.result && !task.result.report && currentTask.value?.result?.report) {
          task.result.report = currentTask.value.result.report
        }
        currentTask.value = task

        if (task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') {
          clearInterval(_pollInterval!)
          _pollInterval = null
          loading.value = false
          // Don't close SSE here — let the done event handle final result delivery
        }
      } catch {
        if (_pollInterval) clearInterval(_pollInterval)
        _pollInterval = null
        loading.value = false
      }
    }, 2000)
  }

  function flushAgentTokens(agent: string) {
    const tokens = _tokenBuffer[agent]
    if (!tokens) return
    delete _tokenBuffer[agent]
    if (!agentDetails.value[agent]) {
      agentDetails.value[agent] = { activityLog: [] }
    }
    const detail = agentDetails.value[agent]
    if (!detail.streamContent) detail.streamContent = ''
    detail.streamContent += tokens
    detail.message = detail.streamContent.slice(-80)
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

    // Handle initial state event from SSE stream
    if (event.type === 'state' && event.data) {
      const taskData = event.data
      if (!taskData.result && currentTask.value?.result) {
        taskData.result = currentTask.value.result
      }
      currentTask.value = taskData
      return
    }

    if (event.agent) {
      const agent = event.agent
      // Ensure agent detail exists
      if (!agentDetails.value[agent]) {
        agentDetails.value[agent] = { activityLog: [] }
      }
      const detail = agentDetails.value[agent]

      // Update node state based on event type
      if (event.type === 'stage_start') {
        nodeStates.value[agent] = 'running'
        // Reset streamContent for fresh start
        detail.streamContent = ''
      } else if (event.type === 'stage_complete') {
        nodeStates.value[agent] = 'completed'
        // Flush any remaining tokens for this agent
        flushAgentTokens(agent)
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

    // Handle report_update — push intermediate/final report to task result
    if (event.type === 'report_update' && event.output && currentTask.value) {
      if (!currentTask.value.result) {
        currentTask.value.result = { report: event.output, metrics: {}, audit_trail: [] }
      } else {
        currentTask.value.result.report = event.output
      }
    }

    // Close SSE on done or cancelled
    if (event.type === 'done' || event.type === 'cancelled') {
      flushTokens()  // flush any remaining buffered tokens
      loading.value = false
      // Update task with final result from done event
      if (event.type === 'done' && event.result && currentTask.value) {
        // Preserve report from report_update if done result doesn't include it
        const incoming = event.result
        if (incoming && !incoming.report && currentTask.value?.result?.report) {
          incoming.report = currentTask.value.result.report
        }
        currentTask.value.result = incoming
        currentTask.value.status = 'completed'
        currentTask.value.progress = 100
        if (event.current_stage) {
          currentTask.value.current_stage = event.current_stage
        }
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
