import request from './request'

// 健康检查 - 基础存活检查（最快）
export const getHealth = () => {
  return request.get('/api/health')
}

// 数据库健康检查 - 仅检查数据库（快速）
export const getDatabaseHealth = () => {
  return request.get('/api/health/database')
}

// 就绪检查 - 检查所有服务（可选快速模式）
export const getReadiness = (quickMode = true) => {
  return request.get('/api/ready', {
    params: { quick: quickMode }
  })
}
