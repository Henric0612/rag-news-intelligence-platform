import request from './request'

// 用户注册
export const register = (data) => {
  return request.post('/api/auth/register', data)
}

// 用户登录
export const login = (data) => {
  return request.post('/api/auth/login', data)
}

// 获取用户信息
export const getUserInfo = () => {
  return request.get('/api/auth/me')
}

// 刷新 token
export const refreshToken = () => {
  return request.post('/api/auth/refresh')
}

// 用户登出
export const logout = () => {
  return request.post('/api/auth/logout')
}

// 请求密码重置
export const requestPasswordReset = (data) => {
  return request.post('/api/auth/request-password-reset', data)
}

// 验证重置令牌
export const verifyResetToken = (data) => {
  return request.post('/api/auth/verify-reset-token', data)
}

// 重置密码
export const resetPassword = (data) => {
  return request.post('/api/auth/reset-password', data)
}

// 验证邮箱
export const verifyEmail = (data) => {
  return request.post('/api/auth/verify-email', data)
}

// 重新发送验证邮件
export const resendVerification = () => {
  return request.post('/api/auth/resend-verification')
}