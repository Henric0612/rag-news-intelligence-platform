<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <div class="logo">
          <el-icon class="logo-icon"><DataAnalysis /></el-icon>
          <h1>RAG News Intelligence Platform</h1>
        </div>
        <p class="login-subtitle">智能新闻问答系统</p>
      </div>
      
      <div class="login-form-container">
        <el-tabs v-model="activeTab" class="login-tabs">
          <el-tab-pane label="登录" name="login" data-testid="login-tab">
            <el-form
              ref="loginFormRef"
              :model="loginForm"
              :rules="loginRules"
              class="login-form"
              @submit.prevent="handleLogin"
            >
              <el-form-item prop="username">
                <el-input
                  v-model="loginForm.username"
                  placeholder="请输入用户名或邮箱"
                  size="large"
                  :prefix-icon="User"
                  class="tech-input"
                  data-testid="login-username-input"
                />
              </el-form-item>
              
              <el-form-item prop="password">
                <el-input
                  v-model="loginForm.password"
                  type="password"
                  placeholder="请输入密码"
                  size="large"
                  :prefix-icon="Lock"
                  show-password
                  class="tech-input"
                  @keyup.enter="handleLogin"
                  data-testid="login-password-input"
                />
              </el-form-item>
              
              <el-form-item>
                <el-button
                  type="primary"
                  size="large"
                  :loading="authStore.loading"
                  @click="handleLogin"
                  class="login-btn tech-button"
                  data-testid="login-submit-button"
                >
                  登录
                </el-button>
              </el-form-item>
              
              <el-form-item>
                <div class="form-footer">
                  <el-link @click="goToPasswordReset">忘记密码？</el-link>
                </div>
              </el-form-item>
            </el-form>
          </el-tab-pane>
          
          <el-tab-pane label="注册" name="register" data-testid="register-tab">
            <!-- 注册错误提示 -->
            <div v-if="registerError" class="register-error">
              <el-alert
                :title="registerError.title"
                :description="registerError.description"
                type="error"
                :closable="true"
                @close="clearRegisterError"
                show-icon
              >
                <template #default>
                  <div v-if="registerError.suggestions" class="error-suggestions">
                    <p><strong>建议：</strong></p>
                    <ul>
                      <li v-for="suggestion in registerError.suggestions" :key="suggestion">
                        {{ suggestion }}
                      </li>
                    </ul>
                  </div>
                  <div class="error-actions">
                    <el-button 
                      v-if="registerError.showLoginButton" 
                      type="primary" 
                      size="small" 
                      @click="switchToLogin"
                    >
                      切换到登录
                    </el-button>
                  </div>
                </template>
              </el-alert>
            </div>
            
            <el-form
              ref="registerFormRef"
              :model="registerForm"
              :rules="registerRules"
              class="login-form"
              @submit.prevent="handleRegister"
            >
              <el-form-item prop="username">
                <el-input
                  v-model="registerForm.username"
                  placeholder="请输入用户名"
                  size="large"
                  :prefix-icon="User"
                  class="tech-input"
                  data-testid="register-username"
                />
              </el-form-item>
              
              <el-form-item prop="email">
                <el-input
                  v-model="registerForm.email"
                  placeholder="请输入邮箱"
                  size="large"
                  :prefix-icon="Message"
                  class="tech-input"
                  data-testid="register-email"
                />
              </el-form-item>
              
              <el-form-item prop="password">
                <el-input
                  v-model="registerForm.password"
                  type="password"
                  placeholder="请输入密码"
                  size="large"
                  :prefix-icon="Lock"
                  show-password
                  class="tech-input"
                  data-testid="register-password"
                />
                <PasswordStrengthIndicator 
                  :password="registerForm.password" 
                  :show-requirements="true"
                />
              </el-form-item>
              
              <el-form-item prop="confirmPassword">
                <el-input
                  v-model="registerForm.confirmPassword"
                  type="password"
                  placeholder="请确认密码"
                  size="large"
                  :prefix-icon="Lock"
                  show-password
                  class="tech-input"
                  @keyup.enter="handleRegister"
                  data-testid="register-confirm-password"
                />
              </el-form-item>
              
              <el-form-item>
                <el-button
                  type="primary"
                  size="large"
                  :loading="authStore.loading"
                  @click="handleRegister"
                  class="login-btn tech-button"
                  data-testid="register-button"
                >
                  注册
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </div>
      
      <div class="login-footer">
        <DarkModeToggle />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { User, Lock, Message, DataAnalysis } from '@element-plus/icons-vue'
import DarkModeToggle from '@/components/DarkModeToggle.vue'
import PasswordStrengthIndicator from '@/components/PasswordStrengthIndicator.vue'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref('login')
const loginFormRef = ref()
const registerFormRef = ref()

// 注册错误状态
const registerError = ref(null)

// 登录表单
const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules = {
  username: [
    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (!value) {
          callback(new Error('请输入用户名或邮箱'))
        } else if (value.includes('@')) {
          // 如果是邮箱格式，验证邮箱
          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
          if (!emailRegex.test(value)) {
            callback(new Error('请输入正确的邮箱格式'))
          } else {
            callback()
          }
        } else {
          // 如果是用户名，验证长度
          if (value.length < 3 || value.length > 20) {
            callback(new Error('用户名长度在 3 到 20 个字符'))
          } else {
            callback()
          }
        }
      },
      trigger: 'blur'
    }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (!value) {
          callback(new Error('请输入密码'))
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
  ]
}

// 注册表单
const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (!value) {
          callback(new Error('请输入密码'))
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
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 处理登录
const handleLogin = async () => {
  try {
    await loginFormRef.value.validate()
    await authStore.loginUser(loginForm)
    router.push('/')
  } catch (error) {
    console.error('登录失败:', error)
  }
}

// 处理注册
const handleRegister = async () => {
  try {
    await registerFormRef.value.validate()
    const { confirmPassword, ...userData } = registerForm
    await authStore.registerUser(userData)
    
    // 注册成功后切换到登录标签页
    activeTab.value = 'login'
    
    // 清空注册表单
    Object.assign(registerForm, {
      username: '',
      email: '',
      password: '',
      confirmPassword: ''
    })
    
    // 显示成功提示
    ElMessage.success('注册成功！请使用新账号登录')
    
  } catch (error) {
    // 错误处理已在authStore中完成，这里只记录日志
    console.error('注册失败:', error)
    
    // 设置详细的错误信息
    if (error.message) {
      if (error.message.includes('用户名已存在')) {
        registerError.value = {
          title: '用户名已存在',
          description: '该用户名已被其他用户使用，请选择其他用户名',
          suggestions: [
            '尝试在用户名后添加数字，如：lihaiyin123',
            '尝试在用户名前添加前缀，如：user_lihaiyin',
            '如果这是您的账号，请直接登录'
          ],
          showLoginButton: true
        }
      } else if (error.message.includes('邮箱已被注册')) {
        registerError.value = {
          title: '邮箱已被注册',
          description: '该邮箱地址已被注册，请使用其他邮箱或直接登录',
          suggestions: [
            '使用其他邮箱地址注册',
            '如果这是您的邮箱，请直接登录',
            '如果忘记了密码，可以使用密码重置功能'
          ],
          showLoginButton: true
        }
      } else if (error.message.includes('密码')) {
        registerError.value = {
          title: '密码不符合要求',
          description: error.message,
          suggestions: [
            '确保密码长度至少8位',
            '包含大小写字母、数字和特殊字符',
            '避免使用常见弱密码'
          ],
          showLoginButton: false
        }
      } else {
        registerError.value = {
          title: '注册失败',
          description: error.message,
          suggestions: [
            '请检查网络连接',
            '稍后重试',
            '如问题持续，请联系管理员'
          ],
          showLoginButton: false
        }
      }
    }
  }
}

// 清除注册错误
const clearRegisterError = () => {
  registerError.value = null
}

// 切换到登录
const switchToLogin = () => {
  activeTab.value = 'login'
  clearRegisterError()
}

// 跳转到密码重置页面
const goToPasswordReset = () => {
  router.push('/password-reset')
}
</script>

<style scoped>
.register-error {
  margin-bottom: 16px;
}

.error-suggestions {
  margin: 12px 0;
}

.error-suggestions ul {
  margin: 8px 0 0 0;
  padding-left: 20px;
}

.error-suggestions li {
  margin: 4px 0;
  line-height: 1.4;
  color: #606266;
}

.error-actions {
  margin: 16px 0 0 0;
  text-align: right;
}

.login-page {
  min-height: 100vh;
  background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-lg);
}

.login-container {
  width: 100%;
  max-width: 400px;
  background: var(--bg-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  animation: slideInUp 0.5s ease;
}

.login-header {
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

.login-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  opacity: 0.9;
}

.login-form-container {
  padding: var(--space-xl);
}

.login-tabs :deep(.el-tabs__header) {
  margin-bottom: var(--space-xl);
}

.login-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.login-tabs :deep(.el-tabs__item) {
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.login-tabs :deep(.el-tabs__item.is-active) {
  color: var(--primary-color);
}

.login-form {
  width: 100%;
}

.login-form .el-form-item {
  margin-bottom: var(--space-lg);
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

.login-footer {
  padding: var(--space-lg) var(--space-xl);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: center;
  background: var(--bg-secondary);
}

@media (max-width: 480px) {
  .login-page {
    padding: var(--space-md);
  }
  
  .login-container {
    max-width: 100%;
  }
  
  .login-header {
    padding: var(--space-xl) var(--space-lg) var(--space-md);
  }
  
  .login-form-container {
    padding: var(--space-lg);
  }
}
</style>
