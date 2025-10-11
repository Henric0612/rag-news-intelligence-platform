/**
 * 数据分析相关API
 */
import request from './request'

/**
 * 获取聚类分析报告
 * @param {Object} params - 查询参数
 * @param {number} params.limit - 限制分析的文档数量
 * @returns {Promise}
 */
export const getClusteringAnalysis = (params = {}) => {
  return request.get('/api/analytics/clustering', { params })
}

/**
 * 获取Top关键词（快速接口）
 * @param {Object} params - 查询参数
 * @param {number} params.limit - 限制分析的文档数量
 * @returns {Promise}
 */
export const getTopKeywords = (params = {}) => {
  return request.get('/api/analytics/keywords', { params })
}

/**
 * 获取趋势分析数据
 * @param {Object} params - 查询参数
 * @param {number} params.days - 分析的天数，默认30天
 * @returns {Promise}
 */
export const getTrendAnalysis = (params = {}) => {
  return request.get('/api/analytics/trends', { params })
}

/**
 * 获取知识库统计信息
 * @returns {Promise}
 */
export const getStatistics = () => {
  return request.get('/api/analytics/statistics')
}

/**
 * 数据分析服务健康检查
 * @returns {Promise}
 */
export const checkAnalyticsHealth = () => {
  return request.get('/api/analytics/health')
}

