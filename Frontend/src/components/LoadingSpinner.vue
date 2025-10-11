<template>
  <div class="loading-spinner" :class="{ 'loading-overlay': overlay }">
    <div class="spinner">
      <el-icon class="spinner-icon" :size="size">
        <Loading />
      </el-icon>
      <p v-if="text" class="loading-text">{{ text }}</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  text: {
    type: String,
    default: '加载中...'
  },
  size: {
    type: Number,
    default: 24
  },
  overlay: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.loading-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-xl);
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.8);
  z-index: var(--z-modal);
  backdrop-filter: blur(4px);
}

[data-theme="dark"] .loading-overlay {
  background: rgba(0, 0, 0, 0.8);
}

.spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
}

.spinner-icon {
  animation: spin 1s linear infinite;
  color: var(--primary-color);
}

.loading-text {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
