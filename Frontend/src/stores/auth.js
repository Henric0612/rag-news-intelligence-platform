import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login, register, getUserInfo, logout as apiLogout, refreshToken as refreshTokenAPI } from '@/api/auth'
import { ElMessage } from 'element-plus'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const token = ref('')
  const user = ref(null)
  const theme = ref(localStorage.getItem('theme') || 'light')
  const loading = ref(false)
  const initialized = ref(false)
  const tokenExpiry = ref(null)  // ✅ Token过期时间戳（毫秒）
  const lastActivity = ref(null)  // ✅ 最后活动时间
  const silentAuth = ref(false)  // ✅ 静默认证模式（不显示错误提示）
  let refreshTimer = null  // ✅ 自动刷新定时器

  // 计算属性
  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const userInfo = computed(() => user.value)

  // 初始化认证状态
  const initAuthState = async () => {
    if (initialized.value) return
    
    try {
      const savedToken = localStorage.getItem('token')
      const savedTokenExpiry = localStorage.getItem('tokenExpiry')
      const savedLastActivity = localStorage.getItem('lastActivity')
      
      // ✅ 恢复最后活动时间
      if (savedLastActivity) {
        lastActivity.value = parseInt(savedLastActivity)
      }
      
      if (savedToken) {
        // 先设置token（用于API请求）
        token.value = savedToken
        
        // ✅ 恢复token过期时间
        if (savedTokenExpiry) {
          tokenExpiry.value = parseInt(savedTokenExpiry)
        }
        
        // ✅ 检查是否长时间未使用（超过24小时）
        const now = Date.now()
        const timeSinceLastActivity = lastActivity.value ? now - lastActivity.value : Infinity
        const isLongInactive = timeSinceLastActivity > 24 * 60 * 60 * 1000 // 24小时
        
        if (isLongInactive) {
          console.log('检测到长时间未使用，启用静默认证模式')
          silentAuth.value = true
        }
        
        // 验证token是否仍然有效，并获取最新用户信息
        try {
          await fetchUserInfo()
          // fetchUserInfo 成功会自动设置 user.value
          
          // ✅ 启动自动刷新定时器
          startTokenRefreshTimer()
          
          // ✅ 更新活动时间
          updateLastActivity()
        } catch (error) {
          console.warn('Token验证失败，清除认证状态:', error)
          clearAuthState()
        }
      }
    } catch (error) {
      console.error('初始化认证状态失败:', error)
      clearAuthState()
    } finally {
      initialized.value = true
    }
  }

  // 清除认证状态
  const clearAuthState = () => {
    token.value = ''
    user.value = null
    tokenExpiry.value = null
    lastActivity.value = null
    silentAuth.value = false
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('tokenExpiry')
    localStorage.removeItem('lastActivity')
    
    // ✅ 停止自动刷新定时器
    stopTokenRefreshTimer()
  }

  // 初始化主题
  const initTheme = () => {
    document.documentElement.setAttribute('data-theme', theme.value)
  }

  // 切换主题
  const toggleTheme = () => {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    localStorage.setItem('theme', theme.value)
    document.documentElement.setAttribute('data-theme', theme.value)
  }

  // 登录
  const loginUser = async (credentials) => {
    try {
      loading.value = true
      const response = await login(credentials)
      
      if (response && response.tokens && response.tokens.access_token) {
        token.value = response.tokens.access_token
        localStorage.setItem('token', response.tokens.access_token)
        
        // ✅ 计算并保存token过期时间
        const expiresIn = response.tokens.expires_in || 3600 // 默认1小时
        tokenExpiry.value = Date.now() + expiresIn * 1000
        localStorage.setItem('tokenExpiry', tokenExpiry.value.toString())
        
        console.log(`Token将在 ${new Date(tokenExpiry.value).toLocaleString()} 过期`)
        
        // 设置用户信息
        user.value = response.user
        localStorage.setItem('user', JSON.stringify(response.user))
        
        // ✅ 重置静默模式并更新活动时间
        silentAuth.value = false
        updateLastActivity()
        
        // ✅ 启动自动刷新定时器
        startTokenRefreshTimer()
        
        ElMessage.success('登录成功')
        return response
      } else {
        throw new Error('登录响应格式错误')
      }
    } catch (error) {
      console.error('登录失败:', error)
      clearAuthState()
      throw error
    } finally {
      loading.value = false
    }
  }

  // 注册
  const registerUser = async (userData) => {
    try {
      loading.value = true
      const response = await register(userData)
      
      ElMessage.success('注册成功，请登录')
      return response
    } catch (error) {
      console.error('注册失败:', error)
      
      // 解析具体的错误信息
      let errorMessage = '注册失败，请稍后重试'
      
      if (error.response && error.response.data) {
        const { message, errors } = error.response.data
        
        if (message) {
          // 后端返回的具体错误信息
          if (message.includes('用户名已存在')) {
            errorMessage = '用户名已存在，请选择其他用户名'
          } else if (message.includes('邮箱已被注册')) {
            errorMessage = '邮箱已被注册，请使用其他邮箱或直接登录'
          } else if (message.includes('缺少必填字段')) {
            errorMessage = '请填写所有必填字段'
          } else if (message.includes('密码')) {
            errorMessage = `密码不符合要求：${message}`
          } else {
            errorMessage = message
          }
        } else if (errors && typeof errors === 'object') {
          // 处理字段验证错误
          const fieldErrors = Object.values(errors).flat()
          if (fieldErrors.length > 0) {
            errorMessage = fieldErrors[0]
          }
        }
      } else if (error.message) {
        // 网络错误或其他错误
        if (error.message.includes('Network Error')) {
          errorMessage = '网络连接失败，请检查网络连接'
        } else if (error.message.includes('timeout')) {
          errorMessage = '请求超时，请稍后重试'
        } else {
          errorMessage = error.message
        }
      }
      
      // 显示具体的错误信息
      ElMessage.error(errorMessage)
      throw new Error(errorMessage)
    } finally {
      loading.value = false
    }
  }

  // 获取用户信息
  const fetchUserInfo = async () => {
    try {
      if (!token.value) return null
      
      const response = await getUserInfo()
      // 处理响应数据：如果response包含user字段，使用user字段；否则使用整个response
      const userData = response.user || response
      user.value = userData
      localStorage.setItem('user', JSON.stringify(userData))
      return userData
    } catch (error) {
      console.error('获取用户信息失败:', error)
      // 如果获取用户信息失败，清除认证状态
      if (error.response?.status === 401) {
        clearAuthState()
      }
      throw error
    }
  }

  // 登出
  const logout = async () => {
    try {
      if (token.value) {
        await apiLogout()
      }
    } catch (error) {
      console.error('登出请求失败:', error)
    } finally {
      // 清除本地状态
      clearAuthState()
      ElMessage.success('已退出登录')
    }
  }

  // 刷新Token
  const refreshToken = async () => {
    try {
      const response = await refreshTokenAPI()
      
      if (response && response.tokens && response.tokens.access_token) {
        token.value = response.tokens.access_token
        localStorage.setItem('token', response.tokens.access_token)
        
        // ✅ 更新token过期时间
        const expiresIn = response.tokens.expires_in || 3600
        tokenExpiry.value = Date.now() + expiresIn * 1000
        localStorage.setItem('tokenExpiry', tokenExpiry.value.toString())
        
        console.log(`Token已刷新，将在 ${new Date(tokenExpiry.value).toLocaleString()} 过期`)
        
        return true
      }
      return false
    } catch (error) {
      console.error('Token刷新失败:', error)
      return false
    }
  }

  // ✅ 更新最后活动时间
  const updateLastActivity = () => {
    lastActivity.value = Date.now()
    localStorage.setItem('lastActivity', lastActivity.value.toString())
  }

  // ✅ 检查是否应该静默处理认证失败
  const shouldSilentAuth = () => {
    // 如果已经设置了静默模式，直接返回
    if (silentAuth.value) return true
    
    // 检查是否长时间未使用（超过12小时）
    const now = Date.now()
    const timeSinceLastActivity = lastActivity.value ? now - lastActivity.value : Infinity
    return timeSinceLastActivity > 12 * 60 * 60 * 1000 // 12小时
  }

  // 检查认证状态
  const checkAuth = async () => {
    if (!token.value) {
      clearAuthState()
      throw new Error('未登录')
    }
    
    try {
      await fetchUserInfo()
      // ✅ 成功获取用户信息后更新活动时间
      updateLastActivity()
      return true
    } catch (error) {
      // 如果是401错误，尝试刷新Token
      if (error.response?.status === 401) {
        const refreshed = await refreshToken()
        if (refreshed) {
          try {
            await fetchUserInfo()
            updateLastActivity()
            return true
          } catch (retryError) {
            console.error('刷新Token后仍无法获取用户信息:', retryError)
          }
        }
      }
      
      // ✅ 检查是否应该静默处理
      const isSilent = shouldSilentAuth()
      if (isSilent) {
        console.log('长时间未使用，静默清除认证状态')
        silentAuth.value = true
      }
      
      clearAuthState()
      throw error
    }
  }

  // ✅ 启动自动刷新定时器
  const startTokenRefreshTimer = () => {
    // 清除旧的定时器
    stopTokenRefreshTimer()
    
    // 每分钟检查一次
    refreshTimer = setInterval(async () => {
      if (!token.value || !tokenExpiry.value) {
        stopTokenRefreshTimer()
        return
      }
      
      // 计算距离过期还有多长时间
      const timeUntilExpiry = tokenExpiry.value - Date.now()
      const fiveMinutes = 5 * 60 * 1000
      
      // 如果在过期前5分钟内，且还没过期，则刷新token
      if (timeUntilExpiry < fiveMinutes && timeUntilExpiry > 0) {
        console.log(`Token即将过期（剩余 ${Math.floor(timeUntilExpiry / 1000)} 秒），自动刷新...`)
        try {
          const success = await refreshToken()
          if (!success) {
            console.error('自动刷新token失败，清除认证状态')
            clearAuthState()
            ElMessage.warning('登录已过期，请重新登录')
          }
        } catch (error) {
          console.error('自动刷新token异常:', error)
          clearAuthState()
          ElMessage.warning('登录已过期，请重新登录')
        }
      } else if (timeUntilExpiry <= 0) {
        // Token已过期
        console.warn('Token已过期')
        clearAuthState()
        ElMessage.warning('登录已过期，请重新登录')
      }
    }, 60 * 1000) // 每分钟检查一次
    
    console.log('自动刷新定时器已启动')
  }
  
  // ✅ 停止自动刷新定时器
  const stopTokenRefreshTimer = () => {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
      console.log('自动刷新定时器已停止')
    }
  }

  return {
    // 状态
    token,
    user,
    theme,
    loading,
    initialized,
    tokenExpiry,
    lastActivity,
    silentAuth,
    
    // 计算属性
    isLoggedIn,
    userInfo,
    
    // 方法
    initAuthState,
    initTheme,
    toggleTheme,
    loginUser,
    registerUser,
    fetchUserInfo,
    logout,
    refreshToken,
    checkAuth,
    clearAuthState,
    startTokenRefreshTimer,
    stopTokenRefreshTimer,
    updateLastActivity,
    shouldSilentAuth
  }
})
