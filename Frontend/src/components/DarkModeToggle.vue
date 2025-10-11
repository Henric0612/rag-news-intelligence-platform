<template>
  <el-button
    :icon="isDark ? Sunny : Moon"
    circle
    size="small"
    @click="toggleTheme"
    class="theme-toggle"
    :title="isDark ? '切换到亮色模式' : '切换到暗色模式'"
  />
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { Sunny, Moon } from '@element-plus/icons-vue'

const authStore = useAuthStore()

const isDark = computed(() => authStore.theme === 'dark')

const toggleTheme = () => {
  authStore.toggleTheme()
}
</script>

<style scoped>
.theme-toggle {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.theme-toggle:hover {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: var(--white);
  transform: scale(1.05);
}

.theme-toggle:active {
  transform: scale(0.95);
}
</style>
