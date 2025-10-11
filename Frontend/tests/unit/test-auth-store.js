/**
 * 认证Store单元测试
 * 测试用例ID: AUTH-001~004 (间接覆盖)
 * 对应测试计划: Sprint 1 - 基础设施层
 * 测试描述: 用户注册、登录、Token管理、密码重置、邮箱验证
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

// Mock Vue Router
vi.mock('vue-router', () => ({
  useRouter: vi.fn()
}))

// Mock API calls
vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  register: vi.fn(),
  getUserInfo: vi.fn(),
  logout: vi.fn(),
  refreshToken: vi.fn(),
  requestPasswordReset: vi.fn(),
  verifyResetToken: vi.fn(),
  resetPassword: vi.fn(),
  verifyEmail: vi.fn(),
  resendVerification: vi.fn()
}))

describe('认证Store单元测试', () => {
  let authStore
  let mockRouter

  beforeEach(() => {
    setActivePinia(createPinia())
    
    // 设置localStorage Mock
    localStorage.setItem = vi.fn()
    localStorage.getItem = vi.fn()
    localStorage.removeItem = vi.fn()
    localStorage.clear = vi.fn()
    
    authStore = useAuthStore()
    
    mockRouter = {
      push: vi.fn(),
      replace: vi.fn()
    }
    useRouter.mockReturnValue(mockRouter)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('用户注册流程', () => {
    it('应该成功注册新用户', async () => {
      const { register } = await import('@/api/auth')
      const mockResponse = {
        user: { id: 1, username: 'testuser', email: 'test@example.com' },
        tokens: { access_token: 'test-token' }
      }
      register.mockResolvedValue(mockResponse)

      const userData = {
        username: 'testuser',
        email: 'test@example.com',
        password: 'TestPass123!'
      }

      const result = await authStore.registerUser(userData)

      expect(result).toEqual(mockResponse)
      expect(register).toHaveBeenCalledWith(userData)
    })

    it('应该处理注册失败', async () => {
      const { register } = await import('@/api/auth')
      const mockError = new Error('用户名已存在')
      register.mockRejectedValue(mockError)

      const userData = {
        username: 'testuser',
        email: 'test@example.com',
        password: 'TestPass123!'
      }

      await expect(authStore.registerUser(userData)).rejects.toThrow('用户名已存在')
    })
  })

  describe('用户登录流程', () => {
    it('应该成功登录用户', async () => {
      const { login } = await import('@/api/auth')
      const mockResponse = {
        user: { id: 1, username: 'testuser', email: 'test@example.com' },
        tokens: { access_token: 'test-token' }
      }
      login.mockResolvedValue(mockResponse)

      const credentials = {
        username: 'testuser',
        password: 'TestPass123!'
      }

      const result = await authStore.loginUser(credentials)

      expect(result).toEqual(mockResponse)
      expect(authStore.token).toBe('test-token')
      expect(authStore.user).toEqual(mockResponse.user)
      expect(authStore.isLoggedIn).toBe(true)
    })

    it('应该处理登录失败', async () => {
      const { login } = await import('@/api/auth')
      const mockError = new Error('用户名或密码错误')
      login.mockRejectedValue(mockError)

      const credentials = {
        username: 'testuser',
        password: 'wrongpassword'
      }

      await expect(authStore.loginUser(credentials)).rejects.toThrow('用户名或密码错误')
      expect(authStore.token).toBe('')
      expect(authStore.user).toBeNull()
      expect(authStore.isLoggedIn).toBe(false)
    })
  })

  describe('Token刷新流程', () => {
    it('应该成功刷新Token', async () => {
      const { refreshToken } = await import('@/api/auth')
      const mockResponse = {
        tokens: { access_token: 'new-token' }
      }
      refreshToken.mockResolvedValue(mockResponse)

      authStore.token = 'old-token'

      const result = await authStore.refreshToken()

      expect(result).toBe(true)
      expect(authStore.token).toBe('new-token')
      expect(localStorage.setItem).toHaveBeenCalledWith('token', 'new-token')
    })

    it('应该处理Token刷新失败', async () => {
      const { refreshToken } = await import('@/api/auth')
      refreshToken.mockRejectedValue(new Error('Token无效'))

      authStore.token = 'invalid-token'

      const result = await authStore.refreshToken()

      expect(result).toBe(false)
    })
  })

  describe('密码重置流程', () => {
    it('应该成功请求密码重置', async () => {
      const { requestPasswordReset } = await import('@/api/auth')
      const mockResponse = {
        message: '重置邮件已发送'
      }
      requestPasswordReset.mockResolvedValue(mockResponse)

      const email = 'test@example.com'
      const result = await requestPasswordReset({ email })

      expect(result).toEqual(mockResponse)
      expect(requestPasswordReset).toHaveBeenCalledWith({ email })
    })

    it('应该成功验证重置令牌', async () => {
      const { verifyResetToken } = await import('@/api/auth')
      const mockResponse = {
        valid: true,
        user: { id: 1, username: 'testuser', email: 'test@example.com' }
      }
      verifyResetToken.mockResolvedValue(mockResponse)

      const token = 'reset-token'
      const result = await verifyResetToken({ token })

      expect(result).toEqual(mockResponse)
      expect(verifyResetToken).toHaveBeenCalledWith({ token })
    })

    it('应该成功重置密码', async () => {
      const { resetPassword } = await import('@/api/auth')
      const mockResponse = {
        message: '密码重置成功'
      }
      resetPassword.mockResolvedValue(mockResponse)

      const data = {
        token: 'reset-token',
        password: 'NewPass123!'
      }
      const result = await resetPassword(data)

      expect(result).toEqual(mockResponse)
      expect(resetPassword).toHaveBeenCalledWith(data)
    })
  })

  describe('邮箱验证流程', () => {
    it('应该成功验证邮箱', async () => {
      const { verifyEmail } = await import('@/api/auth')
      const mockResponse = {
        user: { id: 1, username: 'testuser', email: 'test@example.com' },
        message: '邮箱验证成功'
      }
      verifyEmail.mockResolvedValue(mockResponse)

      const token = 'verification-token'
      const result = await verifyEmail({ token })

      expect(result).toEqual(mockResponse)
      expect(verifyEmail).toHaveBeenCalledWith({ token })
    })

    it('应该成功重新发送验证邮件', async () => {
      const { resendVerification } = await import('@/api/auth')
      const mockResponse = {
        message: '验证邮件已重新发送'
      }
      resendVerification.mockResolvedValue(mockResponse)

      const result = await resendVerification()

      expect(result).toEqual(mockResponse)
    })
  })

  describe('用户登出流程', () => {
    it('应该成功登出用户', async () => {
      const { logout } = await import('@/api/auth')
      logout.mockResolvedValue({})

      authStore.token = 'test-token'
      authStore.user = { id: 1, username: 'testuser' }

      await authStore.logout()

      expect(authStore.token).toBe('')
      expect(authStore.user).toBeNull()
      expect(authStore.isLoggedIn).toBe(false)
      expect(localStorage.removeItem).toHaveBeenCalledWith('token')
    })
  })

  describe('认证状态检查', () => {
    it('应该检查有效的认证状态', async () => {
      const { getUserInfo } = await import('@/api/auth')
      const mockUser = { id: 1, username: 'testuser', email: 'test@example.com' }
      getUserInfo.mockResolvedValue(mockUser)

      authStore.token = 'valid-token'

      const result = await authStore.checkAuth()

      expect(result).toBe(true)
      expect(authStore.user).toEqual(mockUser)
    })

    it('应该处理无效的认证状态', async () => {
      const { getUserInfo } = await import('@/api/auth')
      const mockError = new Error('Token无效')
      mockError.response = { status: 401 }
      getUserInfo.mockRejectedValue(mockError)

      authStore.token = 'invalid-token'

      const result = await authStore.checkAuth()

      expect(result).toBe(false)
      expect(authStore.token).toBe('')
      expect(authStore.user).toBeNull()
    })
  })

  describe('主题切换', () => {
    it('应该切换主题', () => {
      expect(authStore.theme).toBe('light')

      authStore.toggleTheme()
      expect(authStore.theme).toBe('dark')

      authStore.toggleTheme()
      expect(authStore.theme).toBe('light')
    })

    it('应该从localStorage加载主题', () => {
      // 清除之前的Mock
      vi.clearAllMocks()
      
      // Mock localStorage.getItem to return 'dark' for theme
      localStorage.getItem.mockImplementation((key) => {
        if (key === 'theme') return 'dark'
        if (key === 'token') return ''
        return null
      })
      
      // 重新创建Pinia实例
      const newPinia = createPinia()
      setActivePinia(newPinia)
      
      // 重新创建store实例
      const newAuthStore = useAuthStore()
      expect(newAuthStore.theme).toBe('dark')
    })
  })

  describe('错误处理', () => {
    it('应该处理网络错误', async () => {
      const { login } = await import('@/api/auth')
      const networkError = new Error('网络连接失败')
      networkError.request = true
      login.mockRejectedValue(networkError)

      const credentials = {
        username: 'testuser',
        password: 'TestPass123!'
      }

      await expect(authStore.loginUser(credentials)).rejects.toThrow('网络连接失败')
    })

    it('应该处理服务器错误', async () => {
      const { login } = await import('@/api/auth')
      const serverError = new Error('服务器内部错误')
      serverError.response = { status: 500 }
      login.mockRejectedValue(serverError)

      const credentials = {
        username: 'testuser',
        password: 'TestPass123!'
      }

      await expect(authStore.loginUser(credentials)).rejects.toThrow('服务器内部错误')
    })
  })
})
