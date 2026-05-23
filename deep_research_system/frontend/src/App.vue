<script setup lang="ts">
import AppSidebar from './components/layout/AppSidebar.vue'
</script>

<template>
  <div class="flex h-screen bg-cyber-bg text-gray-200 font-body">
    <AppSidebar />
    <main class="flex-1 overflow-auto">
      <router-view />
    </main>
  </div>
</template>
