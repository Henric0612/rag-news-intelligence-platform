<template>
  <div class="not-found-page">
    <div class="not-found-container">
      <div class="error-code">404</div>
      <h1 class="error-title">页面不存在</h1>
      <p class="error-description">
        抱歉，您访问的页面不存在或已被移除。
      </p>
      <div class="error-actions">
        <el-button 
          type="primary" 
          :icon="HomeFilled"
          @click="goHome"
          class="tech-button"
        >
          返回首页
        </el-button>
        <el-button 
          :icon="Refresh"
          @click="goBack"
          class="tech-button"
        >
          返回上页
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { HomeFilled, Refresh } from '@element-plus/icons-vue'

const router = useRouter()

const goHome = () => {
  router.push('/')
}

const goBack = () => {
  router.go(-1)
}
</script>

<style scoped>
.not-found-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
  padding: var(--space-lg);
}

.not-found-container {
  text-align: center;
  max-width: 500px;
  animation: slideInUp 0.5s ease;
}

.error-code {
  font-size: 120px;
  font-weight: var(--font-bold);
  color: var(--primary-color);
  line-height: 1;
  margin-bottom: var(--space-lg);
  text-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
}

.error-title {
  font-size: var(--text-3xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--space-md) 0;
}

.error-description {
  font-size: var(--text-lg);
  color: var(--text-secondary);
  margin: 0 0 var(--space-2xl) 0;
  line-height: var(--leading-relaxed);
}

.error-actions {
  display: flex;
  gap: var(--space-md);
  justify-content: center;
  flex-wrap: wrap;
}

@media (max-width: 480px) {
  .error-code {
    font-size: 80px;
  }
  
  .error-title {
    font-size: var(--text-2xl);
  }
  
  .error-description {
    font-size: var(--text-base);
  }
  
  .error-actions {
    flex-direction: column;
    align-items: center;
  }
}
</style>
