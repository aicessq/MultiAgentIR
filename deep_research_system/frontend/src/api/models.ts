import client from './client'

export interface SlotConfig {
  slot: string
  model_name: string
  api_key: string
  api_base: string
  has_key: boolean
}

export async function getModelConfig() {
  const { data } = await client.get('/models/config')
  return data.data.slots as SlotConfig[]
}

export async function updateModelConfig(slots: SlotConfig[]) {
  const { data } = await client.put('/models/config', slots)
  return data.data
}

export async function testModelConnection(model_name: string, api_key: string, api_base: string) {
  const { data } = await client.post('/models/test', { model_name, api_key, api_base })
  return data.data as { connected: boolean; message: string }
}

export async function resetModelConfig() {
  const { data } = await client.post('/models/reset')
  return data.data
}
