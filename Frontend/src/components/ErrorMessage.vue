<template>
  <div v-if="show" class="error-message">
    <el-alert
      :title="title"
      :description="description"
      type="error"
      :closable="closable"
      @close="handleClose"
      show-icon
    >
      <template #default>
        <div class="error-content">
          <p class="error-main">{{ title }}</p>
          <p v-if="description" class="error-desc">{{ description }}</p>
          <div v-if="suggestions && suggestions.length > 0" class="error-suggestions">
            <p class="suggestion-title">建议：</p>
            <ul class="suggestion-list">
              <li v-for="suggestion in suggestions" :key="suggestion">
                {{ suggestion }}
              </li>
            </ul>
          </div>
          <div v-if="showActions" class="error-actions">
            <el-button 
              v-if="actionText" 
              type="primary" 
              size="small" 
              @click="handleAction"
            >
              {{ actionText }}
            </el-button>
          </div>
        </div>
      </template>
    </el-alert>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '操作失败'
  },
  description: {
    type: String,
    default: ''
  },
  suggestions: {
    type: Array,
    default: () => []
  },
  actionText: {
    type: String,
    default: ''
  },
  closable: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['close', 'action'])

const handleClose = () => {
  emit('close')
}

const handleAction = () => {
  emit('action')
}
</script>

<style scoped>
.error-message {
  margin: 16px 0;
}

.error-content {
  padding: 8px 0;
}

.error-main {
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #f56c6c;
}

.error-desc {
  margin: 8px 0;
  color: #606266;
  line-height: 1.5;
}

.error-suggestions {
  margin: 12px 0;
}

.suggestion-title {
  font-weight: 500;
  margin: 0 0 8px 0;
  color: #409eff;
}

.suggestion-list {
  margin: 0;
  padding-left: 20px;
  color: #606266;
}

.suggestion-list li {
  margin: 4px 0;
  line-height: 1.4;
}

.error-actions {
  margin: 16px 0 0 0;
  text-align: right;
}
</style>
