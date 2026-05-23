<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { Search, Setting } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
</script>

<template>
  <aside class="w-16 bg-cyber-card border-r border-cyber-border flex flex-col items-center py-4 gap-2">
    <div class="mb-6">
      <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-cyber-cyan to-cyber-purple flex items-center justify-center">
        <span class="font-display text-xs font-bold text-cyber-bg">DR</span>
      </div>
    </div>

    <el-tooltip content="研究" placement="right">
      <button
        class="w-10 h-10 rounded-lg flex items-center justify-center transition-all"
        :class="route.path === '/' ? 'bg-cyber-cyan/20 text-cyber-cyan shadow-glow-sm' : 'text-gray-500 hover:text-cyber-cyan hover:bg-cyber-border/50'"
        @click="router.push('/')"
      >
        <el-icon :size="20"><Search /></el-icon>
      </button>
    </el-tooltip>

    <el-tooltip content="模型配置" placement="right">
      <button
        class="w-10 h-10 rounded-lg flex items-center justify-center transition-all"
        :class="route.path === '/settings' ? 'bg-cyber-cyan/20 text-cyber-cyan shadow-glow-sm' : 'text-gray-500 hover:text-cyber-cyan hover:bg-cyber-border/50'"
        @click="router.push('/settings')"
      >
        <el-icon :size="20"><Setting /></el-icon>
      </button>
    </el-tooltip>
  </aside>
</template>
