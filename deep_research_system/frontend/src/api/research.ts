import client from './client'

export interface ResearchRequest {
  query: string
  task_type?: string
  depth?: string
  budget_level?: string
  max_sources?: number
}

export interface TaskResult {
  task_id: string
  status: string
  progress: number
  current_stage: string
  selected_topology: string
  created_at: string
  result: {
    report?: any
    claim_graph?: any[]
    metrics?: any
    audit_trail?: any[]
  } | null
  error?: string
}

export async function createResearch(req: ResearchRequest) {
  const { data } = await client.post('/research', req)
  return data.data as TaskResult
}

export async function createResearchSync(req: ResearchRequest) {
  const { data } = await client.post('/research/sync', req)
  return data.data as TaskResult
}

export async function getResearch(taskId: string) {
  const { data } = await client.get(`/research/${taskId}`)
  return data.data as TaskResult
}

export function streamResearch(taskId: string, onEvent: (event: any) => void, onError?: () => void): EventSource {
  const es = new EventSource(`/api/research/${taskId}/stream`)
  es.onmessage = (msg) => {
    try {
      onEvent(JSON.parse(msg.data))
    } catch {}
  }
  es.onerror = () => {
    es.close()
    onError?.()
  }
  return es
}

export async function cancelResearch(taskId: string) {
  const { data } = await client.post(`/research/${taskId}/cancel`)
  return data.data
}
