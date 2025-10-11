<template>
  <div id="app" :data-theme="theme">
    <router-view />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const theme = computed(() => authStore.theme)

onMounted(() => {
  // 初始化主题
  authStore.initTheme()
})
</script>

<style>
#app {
  min-height: 100vh;
  background-color: var(--bg-color);
  color: var(--text-color);
  transition: background-color 0.3s ease, color 0.3s ease;
}
</style>
