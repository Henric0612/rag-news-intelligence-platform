<template>
  <div class="empty-state">
    <div class="empty-icon">
      <el-icon :size="iconSize">
        <component :is="icon" />
      </el-icon>
    </div>
    <h3 class="empty-title">{{ title }}</h3>
    <p class="empty-description">{{ description }}</p>
    <div class="empty-actions" v-if="$slots.actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: '暂无数据'
  },
  description: {
    type: String,
    default: '当前没有可显示的内容'
  },
  icon: {
    type: String,
    default: 'Document'
  },
  iconSize: {
    type: Number,
    default: 64
  }
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-3xl) var(--space-lg);
  text-align: center;
  min-height: 300px;
}

.empty-icon {
  margin-bottom: var(--space-lg);
  color: var(--text-tertiary);
  opacity: 0.6;
}

.empty-title {
  margin: 0 0 var(--space-md) 0;
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.empty-description {
  margin: 0 0 var(--space-xl) 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  max-width: 400px;
  line-height: var(--leading-relaxed);
}

.empty-actions {
  display: flex;
  gap: var(--space-md);
  flex-wrap: wrap;
  justify-content: center;
}
</style>
