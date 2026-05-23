import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getModelConfig, updateModelConfig, testModelConnection, resetModelConfig, type SlotConfig } from '../api/models'

export const useConfigStore = defineStore('config', () => {
  const slots = ref<SlotConfig[]>([])
  const loading = ref(false)

  async function loadConfig() {
    loading.value = true
    try {
      slots.value = await getModelConfig()
    } finally {
      loading.value = false
    }
  }

  async function saveConfig() {
    loading.value = true
    try {
      await updateModelConfig(slots.value)
    } finally {
      loading.value = false
    }
  }

  async function testConnection(modelName: string, apiKey: string, apiBase: string) {
    return await testModelConnection(modelName, apiKey, apiBase)
  }

  async function resetConfig() {
    loading.value = true
    try {
      await resetModelConfig()
      await loadConfig()
    } finally {
      loading.value = false
    }
  }

  return { slots, loading, loadConfig, saveConfig, testConnection, resetConfig }
})
