import request from './request'
import { searchCache, withCache } from '@/utils/cache'

// 智能搜索（带缓存）
export const searchQuery = withCache(
  (data) => request.post('/api/search/query', data),
  (data) => `/api/search/query:${JSON.stringify(data)}`,
  2 * 60 * 1000 // 搜索缓存2分钟
)

// 获取搜索历史
export const getSearchHistory = withCache(
  (params = {}) => request.get('/api/search/history', { params }),
  (params) => `/api/search/history:${JSON.stringify(params)}`,
  1 * 60 * 1000 // 历史缓存1分钟
)

// 获取搜索建议（带缓存）
export const getSearchSuggestions = withCache(
  (query) => request.get('/api/search/suggestions', { params: { q: query } }),
  (query) => `/api/search/suggestions:${query}`,
  30 * 1000 // 建议缓存30秒
)

// 结果重排
export const rerankResults = (data) => {
  return request.post('/api/search/rerank', data)
}

// 获取搜索统计（带缓存）
export const getSearchStats = withCache(
  () => request.get('/api/search/stats'),
  () => '/api/search/stats',
  5 * 60 * 1000 // 统计缓存5分钟
)

// 搜索服务健康检查
export const searchHealthCheck = () => {
  return request.get('/api/search/health')
}
