import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

// 创建 axios 实例
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000',
  // 后端分析接口可能较慢，这里设较高默认值；具体接口可再单独覆盖
  timeout: 90000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 获取认证token的函数
const getAuthToken = () => {
  try {
    // 直接从localStorage获取token，避免循环依赖
    return localStorage.getItem('token')
  } catch (error) {
    console.warn('无法获取认证token:', error)
    return null
  }
}

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 添加认证 token
    const token = getAuthToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // 添加请求时间戳
    config.metadata = { startTime: new Date() }
    
    return config
  },
  (error) => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    const { config } = response
    
    // 计算请求耗时
    if (config.metadata?.startTime) {
      const duration = new Date() - config.metadata.startTime
      console.log(`API ${config.method?.toUpperCase()} ${config.url} 耗时: ${duration}ms`)
    }
    
    // 统一处理响应数据
    // 目标：始终返回实际数据，去除包装层
    const { data } = response
    
    if (data && typeof data === 'object') {
      // 情况1：后端返回标准格式 { success, code, message, data }
      if (data.success !== undefined) {
        if (data.success && (data.code === 200 || data.code === 201)) {
          return data.data || data
        } else {
          ElMessage.error(data.message || '请求失败')
          return Promise.reject(new Error(data.message || '请求失败'))
        }
      }
      
      // 情况2：后端直接返回数据（无包装）
      // 直接返回 data，让 Store 层统一处理
      return data
    }
    
    // 情况3：非对象响应（如文本、数字等）
    return data
  },
  async (error) => {
    console.error('响应错误:', error)
    
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case 400:
          // 400错误通常包含具体的验证错误信息，不在这里显示通用错误
          // 让具体的API调用方处理这些错误，避免重复显示
          break
        case 401:
          // ✅ 检查是否应该静默处理401错误
          try {
            const authStore = useAuthStore()
            const shouldSilent = authStore.shouldSilentAuth()
            
            if (shouldSilent) {
              console.log('长时间未使用，静默处理401错误')
              // 静默清除认证状态，不显示错误提示
              authStore.clearAuthState()
            } else {
              // 主动登录失败，显示错误提示
              ElMessage.error('登录已过期，请重新登录')
            }
          } catch (e) {
            console.warn('处理401错误失败:', e)
            ElMessage.error('登录已过期，请重新登录')
          }
          break
        case 403:
          ElMessage.error('没有权限访问该资源')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 422:
          ElMessage.error(data?.message || '请求参数错误')
          break
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error(data?.message || `请求失败 (${status})`)
      }
    } else if (error.request) {
      ElMessage.error('网络连接失败，请检查网络')
    } else {
      ElMessage.error('请求配置错误')
    }
    
    return Promise.reject(error)
  }
)

export default request
