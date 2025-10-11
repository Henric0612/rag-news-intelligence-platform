<template>
  <div class="email-verification-page">
    <div class="verification-container">
      <div class="verification-header">
        <div class="logo">
          <el-icon class="logo-icon"><DataAnalysis /></el-icon>
          <h1>XU News AI RAG</h1>
        </div>
        <p class="verification-subtitle">邮箱验证</p>
      </div>
      
      <div class="verification-form-container">
        <!-- 验证成功 -->
        <div v-if="verificationStatus === 'success'" class="success-content">
          <div class="success-icon">
            <el-icon><Check /></el-icon>
          </div>
          <h2>邮箱验证成功</h2>
          <p>您的邮箱已成功验证，现在可以正常使用系统功能了</p>
          <el-button
            type="primary"
            size="large"
            @click="goToDashboard"
            class="continue-btn tech-button"
          >
            继续使用
          </el-button>
        </div>
        
        <!-- 验证失败 -->
        <div v-else-if="verificationStatus === 'error'" class="error-content">
          <div class="error-icon">
            <el-icon><Close /></el-icon>
          </div>
          <h2>验证失败</h2>
          <p>{{ errorMessage }}</p>
          <div class="error-actions">
            <el-button
              type="primary"
              size="large"
              @click="resendVerification"
              :loading="loading"
              class="resend-btn tech-button"
            >
              重新发送验证邮件
            </el-button>
            <el-button
              size="large"
              @click="goToLogin"
              class="login-btn"
            >
              返回登录
            </el-button>
          </div>
        </div>
        
        <!-- 验证中 -->
        <div v-else class="verifying-content">
          <div class="loading-icon">
            <el-icon class="is-loading"><Loading /></el-icon>
          </div>
          <h2>正在验证邮箱...</h2>
          <p>请稍候，我们正在验证您的邮箱地址</p>
        </div>
      </div>
      
      <div class="verification-footer">
        <DarkModeToggle />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DataAnalysis, Check, Close, Loading } from '@element-plus/icons-vue'
import DarkModeToggle from '@/components/DarkModeToggle.vue'
import { verifyEmail, resendVerification as resendVerificationAPI } from '@/api/auth'

const router = useRouter()
const route = useRoute()

const verificationStatus = ref('verifying') // 'verifying', 'success', 'error'
const errorMessage = ref('')
const loading = ref(false)

// 验证邮箱
const verifyEmailToken = async (token) => {
  try {
    const response = await verifyEmail({ token })
    verificationStatus.value = 'success'
    ElMessage.success(response.message || '邮箱验证成功')
  } catch (error) {
    console.error('邮箱验证失败:', error)
    verificationStatus.value = 'error'
    errorMessage.value = error.response?.data?.message || '验证失败，请稍后重试'
  }
}

// 重新发送验证邮件
const resendVerification = async () => {
  try {
    loading.value = true
    const response = await resendVerificationAPI()
    ElMessage.success(response.message || '验证邮件已重新发送')
  } catch (error) {
    console.error('重新发送验证邮件失败:', error)
    ElMessage.error(error.response?.data?.message || '发送失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

// 跳转到仪表板
const goToDashboard = () => {
  router.push('/')
}

// 跳转到登录页
const goToLogin = () => {
  router.push('/login')
}

// 页面加载时验证邮箱
onMounted(() => {
  const token = route.query.token
  if (token) {
    verifyEmailToken(token)
  } else {
    verificationStatus.value = 'error'
    errorMessage.value = '缺少验证令牌'
  }
})
</script>

<style scoped>
.email-verification-page {
  min-height: 100vh;
  background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-lg);
}

.verification-container {
  width: 100%;
  max-width: 400px;
  background: var(--bg-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  animation: slideInUp 0.5s ease;
}

.verification-header {
  padding: var(--space-2xl) var(--space-xl) var(--space-lg);
  text-align: center;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  color: var(--white);
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  margin-bottom: var(--space-md);
}

.logo-icon {
  font-size: 32px;
}

.logo h1 {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
}

.verification-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  opacity: 0.9;
}

.verification-form-container {
  padding: var(--space-xl);
}

.success-content,
.error-content,
.verifying-content {
  text-align: center;
  padding: var(--space-xl) 0;
}

.success-icon,
.error-icon {
  font-size: 64px;
  margin-bottom: var(--space-lg);
}

.success-icon {
  color: var(--success-color);
}

.error-icon {
  color: var(--error-color);
}

.loading-icon {
  font-size: 64px;
  color: var(--primary-color);
  margin-bottom: var(--space-lg);
}

.success-content h2,
.error-content h2,
.verifying-content h2 {
  margin: 0 0 var(--space-md) 0;
  color: var(--text-primary);
}

.success-content p,
.error-content p,
.verifying-content p {
  margin: 0 0 var(--space-xl) 0;
  color: var(--text-secondary);
}

.continue-btn,
.resend-btn {
  width: 100%;
  height: 48px;
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  border: none;
  transition: all var(--transition-fast);
  margin-bottom: var(--space-md);
}

.continue-btn:hover,
.resend-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.login-btn {
  width: 100%;
  height: 48px;
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  border-radius: var(--radius-md);
}

.error-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.verification-footer {
  padding: var(--space-lg) var(--space-xl);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: center;
  background: var(--bg-secondary);
}

@media (max-width: 480px) {
  .email-verification-page {
    padding: var(--space-md);
  }
  
  .verification-container {
    max-width: 100%;
  }
  
  .verification-header {
    padding: var(--space-xl) var(--space-lg) var(--space-md);
  }
  
  .verification-form-container {
    padding: var(--space-lg);
  }
}
</style>
