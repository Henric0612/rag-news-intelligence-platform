/**
 * 爬虫相关API
 */
import request from './request'

export const crawlerAPI = {
  // RSS源管理
  getRssSources(params = {}) {
    return request({
      url: '/api/crawler/rss/sources',
      method: 'get',
      params
    })
  },

  createRssSource(data) {
    return request({
      url: '/api/crawler/rss/sources',
      method: 'post',
      data
    })
  },

  updateRssSource(id, data) {
    return request({
      url: `/api/crawler/rss/sources/${id}`,
      method: 'put',
      data
    })
  },

  deleteRssSource(id) {
    return request({
      url: `/api/crawler/rss/sources/${id}`,
      method: 'delete'
    })
  },

  // RSS抓取
  crawlRssFeeds(data) {
    return request({
      url: '/api/crawler/rss/crawl',
      method: 'post',
      data
    })
  },

  crawlRssSource(sourceId) {
    return request({
      url: `/api/crawler/rss/sources/${sourceId}/crawl`,
      method: 'post'
    })
  },

  // 网页抓取
  crawlWebpage(data) {
    return request({
      url: '/api/crawler/web/crawl',
      method: 'post',
      data
    })
  },

  // 爬取任务管理
  getCrawlTasks(params = {}) {
    return request({
      url: '/api/crawler/tasks',
      method: 'get',
      params
    })
  },

  // 清空所有任务记录
  clearAllTasks() {
    return request({
      url: '/api/crawler/tasks/clear',
      method: 'delete'
    })
  },

  getCrawlTask(id) {
    return request({
      url: `/api/crawler/tasks/${id}`,
      method: 'get'
    })
  },

  // 统计信息
  getStatistics() {
    return request({
      url: '/api/crawler/statistics',
      method: 'get'
    })
  },

  // 任务监控
  monitorCrawlTasks(params = {}) {
    return request({
      url: '/api/crawler/monitor',
      method: 'get',
      params
    })
  },

  // 定时任务
  scheduleCrawling() {
    return request({
      url: '/api/crawler/schedule',
      method: 'post'
    })
  },

  // 数据源管理
  getDataSources() {
    return request({
      url: '/api/crawler/data-sources',
      method: 'get'
    })
  },

  // 数据质量检查
  checkDataQuality(params = {}) {
    return request({
      url: '/api/crawler/data-quality',
      method: 'get',
      params
    })
  }
}
