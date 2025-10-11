<template>
  <div class="page-container">
    <div class="page-header" v-if="showHeader">
      <div class="page-title">
        <h2>{{ title }}</h2>
        <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
      </div>
      <div class="page-actions" v-if="$slots.actions">
        <slot name="actions" />
      </div>
    </div>
    
    <div class="page-content">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: ''
  },
  subtitle: {
    type: String,
    default: ''
  },
  showHeader: {
    type: Boolean,
    default: true
  }
})
</script>

<style scoped>
.page-container {
  min-height: 100%;
  background: var(--bg-color);
}

.page-header {
  padding: var(--space-lg);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-md);
}

.page-title h2 {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.page-subtitle {
  margin: var(--space-xs) 0 0 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.page-actions {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.page-content {
  padding: var(--space-lg);
  min-height: calc(100vh - 200px);
}

@media (max-width: 768px) {
  .page-header {
    padding: var(--space-md);
    flex-direction: column;
    align-items: flex-start;
  }
  
  .page-content {
    padding: var(--space-md);
  }
}
</style>
