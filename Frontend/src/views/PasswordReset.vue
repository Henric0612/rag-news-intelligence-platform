<template>
  <div class="password-reset-page">
    <div class="reset-container">
      <div class="reset-header">
        <div class="logo">
          <el-icon class="logo-icon"><DataAnalysis /></el-icon>
          <h1>XU News AI RAG</h1>
        </div>
        <p class="reset-subtitle">密码重置</p>
      </div>
      
      <div class="reset-form-container">
        <!-- 步骤1: 输入邮箱 -->
        <div v-if="currentStep === 1" class="step-content">
          <el-form
            ref="emailFormRef"
            :model="emailForm"
            :rules="emailRules"
            class="reset-form"
            @submit.prevent="handleRequestReset"
          >
            <el-form-item prop="email">
              <el-input
                v-model="emailForm.email"
                placeholder="请输入注册时使用的邮箱地址"
                size="large"
                :prefix-icon="Message"
                class="tech-input"
                data-testid="reset-email"
              />
            </el-form-item>
            
            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="loading"
                @click="handleRequestReset"
                class="reset-btn tech-button"
                data-testid="request-reset-button"
              >
                发送重置邮件
              </el-button>
            </el-form-item>
            
            <div class="form-footer">
              <el-link @click="goToLogin">返回登录</el-link>
            </div>
          </el-form>
        </div>
        
        <!-- 步骤2: 输入新密码 -->
        <div v-if="currentStep === 2" class="step-content">
          <div class="user-info" v-if="userInfo">
            <el-icon class="user-icon"><User /></el-icon>
            <span>为 {{ userInfo.username }} 重置密码</span>
          </div>
          
          <el-form
            ref="passwordFormRef"
            :model="passwordForm"
            :rules="passwordRules"
            class="reset-form"
            @submit.prevent="handleResetPassword"
          >
            <el-form-item prop="password">
              <el-input
                v-model="passwordForm.password"
                type="password"
                placeholder="请输入新密码"
                size="large"
                :prefix-icon="Lock"
                show-password
                class="tech-input"
              />
              <PasswordStrengthIndicator 
                :password="passwordForm.password" 
                :show-requirements="true"
              />
            </el-form-item>
            
            <el-form-item prop="confirmPassword">
              <el-input
                v-model="passwordForm.confirmPassword"
                type="password"
                placeholder="请确认新密码"
                size="large"
                :prefix-icon="Lock"
                show-password
                class="tech-input"
                @keyup.enter="handleResetPassword"
              />
            </el-form-item>
            
            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="loading"
                @click="handleResetPassword"
                class="reset-btn tech-button"
              >
                重置密码
              </el-button>
            </el-form-item>
          </el-form>
        </div>
        
        <!-- 步骤3: 重置成功 -->
        <div v-if="currentStep === 3" class="step-content success-step">
          <div class="success-icon">
            <el-icon><Check /></el-icon>
          </div>
          <h2>密码重置成功</h2>
          <p>您的密码已成功重置，请使用新密码登录</p>
          <el-button
            type="primary"
            size="large"
            @click="goToLogin"
            class="login-btn tech-button"
          >
            前往登录
          </el-button>
        </div>
      </div>
      
      <div class="reset-footer">
        <DarkModeToggle />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Message, DataAnalysis, Check } from '@element-plus/icons-vue'
import DarkModeToggle from '@/components/DarkModeToggle.vue'
import PasswordStrengthIndicator from '@/components/PasswordStrengthIndicator.vue'
import { requestPasswordReset, verifyResetToken, resetPassword } from '@/api/auth'

const router = useRouter()
const route = useRoute()

const currentStep = ref(1)
const loading = ref(false)
const userInfo = ref(null)
const resetToken = ref('')

const emailFormRef = ref()
const passwordFormRef = ref()

// 邮箱表单
const emailForm = reactive({
  email: ''
})

const emailRules = {
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ]
}

// 密码表单
const passwordForm = reactive({
  password: '',
  confirmPassword: ''
})

const passwordRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (!value) {
          callback(new Error('请输入新密码'))
        } else if (value.length < 8) {
          callback(new Error('密码长度至少8位'))
        } else if (value.length > 128) {
          callback(new Error('密码长度不能超过128位'))
        } else if (!/[a-z]/.test(value)) {
          callback(new Error('密码必须包含小写字母'))
        } else if (!/[A-Z]/.test(value)) {
          callback(new Error('密码必须包含大写字母'))
        } else if (!/\d/.test(value)) {
          callback(new Error('密码必须包含数字'))
        } else if (!/[!@#$%^&*(),.?":{}|<>]/.test(value)) {
          callback(new Error('密码必须包含特殊字符'))
        } else if (/(.)\1{2,}/.test(value)) {
          callback(new Error('密码不能包含连续3个或以上相同字符'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.password) {
          callback(new Error('两次输入密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 处理请求重置
const handleRequestReset = async () => {
  try {
    await emailFormRef.value.validate()
    loading.value = true
    
    const response = await requestPasswordReset({ email: emailForm.email })
    ElMessage.success(response.message || '重置邮件已发送，请检查您的邮箱')
    
    // 这里可以跳转到提示页面，或者显示提示信息
    ElMessage.info('请检查您的邮箱并点击重置链接')
    
  } catch (error) {
    console.error('请求密码重置失败:', error)
    if (error.response?.data?.message) {
      ElMessage.error(error.response.data.message)
    } else {
      ElMessage.error('请求失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}

// 处理重置密码
const handleResetPassword = async () => {
  try {
    await passwordFormRef.value.validate()
    loading.value = true
    
    const response = await resetPassword({
      token: resetToken.value,
      password: passwordForm.password
    })
    
    ElMessage.success(response.message || '密码重置成功')
    currentStep.value = 3
    
  } catch (error) {
    console.error('重置密码失败:', error)
    if (error.response?.data?.message) {
      ElMessage.error(error.response.data.message)
    } else {
      ElMessage.error('重置失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}

// 验证重置令牌
const verifyToken = async (token) => {
  try {
    const response = await verifyResetToken({ token })
    if (response.valid) {
      userInfo.value = response.user
      resetToken.value = token
      currentStep.value = 2
    } else {
      ElMessage.error('重置链接无效或已过期')
      goToLogin()
    }
  } catch (error) {
    console.error('验证令牌失败:', error)
    ElMessage.error('重置链接无效或已过期')
    goToLogin()
  }
}

// 跳转到登录页
const goToLogin = () => {
  router.push('/login')
}

// 页面加载时检查是否有重置令牌
onMounted(() => {
  const token = route.query.token
  if (token) {
    verifyToken(token)
  }
})
</script>

<style scoped>
.password-reset-page {
  min-height: 100vh;
  background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-lg);
}

.reset-container {
  width: 100%;
  max-width: 400px;
  background: var(--bg-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  animation: slideInUp 0.5s ease;
}

.reset-header {
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

.reset-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  opacity: 0.9;
}

.reset-form-container {
  padding: var(--space-xl);
}

.step-content {
  width: 100%;
}

.reset-form {
  width: 100%;
}

.reset-form .el-form-item {
  margin-bottom: var(--space-lg);
}

.reset-btn {
  width: 100%;
  height: 48px;
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  border: none;
  transition: all var(--transition-fast);
}

.reset-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.form-footer {
  text-align: center;
  margin-top: var(--space-lg);
}

.user-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  padding: var(--space-md);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-lg);
  color: var(--text-secondary);
}

.user-icon {
  font-size: 16px;
}

.success-step {
  text-align: center;
  padding: var(--space-xl) 0;
}

.success-icon {
  font-size: 64px;
  color: var(--success-color);
  margin-bottom: var(--space-lg);
}

.success-step h2 {
  margin: 0 0 var(--space-md) 0;
  color: var(--text-primary);
}

.success-step p {
  margin: 0 0 var(--space-xl) 0;
  color: var(--text-secondary);
}

.login-btn {
  width: 100%;
  height: 48px;
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  border: none;
  transition: all var(--transition-fast);
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.reset-footer {
  padding: var(--space-lg) var(--space-xl);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: center;
  background: var(--bg-secondary);
}

@media (max-width: 480px) {
  .password-reset-page {
    padding: var(--space-md);
  }
  
  .reset-container {
    max-width: 100%;
  }
  
  .reset-header {
    padding: var(--space-xl) var(--space-lg) var(--space-md);
  }
  
  .reset-form-container {
    padding: var(--space-lg);
  }
}
</style>
