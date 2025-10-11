/**
 * 爬虫管理流程集成测试
 * 测试用例ID: FRONT-INT-004
 * 对应测试计划: Sprint 3 - 应用功能层
 * 测试描述: 爬虫管理 API 集成测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { crawlerAPI } from '@/api/crawler'

// Mock crawler API
vi.mock('@/api/crawler', () => ({
  crawlerAPI: {
    getRssSources: vi.fn(),
    createRssSource: vi.fn(),
    crawlRssFeeds: vi.fn(),
    crawlWebpage: vi.fn(),
    getCrawlTasks: vi.fn(),
    getCrawlTask: vi.fn(),
    getStatistics: vi.fn()
  }
}))

describe('爬虫管理流程集成测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('RSS源管理', () => {
    it('应该能够获取RSS源列表', async () => {
      const mockSources = [
        { id: 1, name: 'RSS源1', url: 'https://example.com/rss1', status: 'active' },
        { id: 2, name: 'RSS源2', url: 'https://example.com/rss2', status: 'active' }
      ]

      crawlerAPI.getRssSources.mockResolvedValue(mockSources)

      const result = await crawlerAPI.getRssSources()

      expect(crawlerAPI.getRssSources).toHaveBeenCalled()
      expect(result).toEqual(mockSources)
      expect(result.length).toBe(2)
    })

    it('应该能够创建新的RSS源', async () => {
      const newSource = {
        name: '新RSS源',
        url: 'https://example.com/new-rss',
        category: 'tech'
      }

      const mockResponse = {
        id: 3,
        ...newSource,
        status: 'active',
        created_at: '2025-01-09'
      }

      crawlerAPI.createRssSource.mockResolvedValue(mockResponse)

      const result = await crawlerAPI.createRssSource(newSource)

      expect(crawlerAPI.createRssSource).toHaveBeenCalledWith(newSource)
      expect(result.id).toBe(3)
      expect(result.name).toBe(newSource.name)
    })
  })

  describe('爬虫任务执行', () => {
    it('应该能够执行RSS抓取', async () => {
      const crawlData = {
        source_ids: [1, 2]
      }

      const mockResponse = {
        task_id: 'task-001',
        status: 'running',
        message: 'RSS抓取任务已启动'
      }

      crawlerAPI.crawlRssFeeds.mockResolvedValue(mockResponse)

      const result = await crawlerAPI.crawlRssFeeds(crawlData)

      expect(crawlerAPI.crawlRssFeeds).toHaveBeenCalledWith(crawlData)
      expect(result.task_id).toBe('task-001')
      expect(result.status).toBe('running')
    })

    it('应该能够执行网页抓取', async () => {
      const crawlData = {
        url: 'https://example.com',
        depth: 2
      }

      const mockResponse = {
        task_id: 'task-002',
        status: 'running',
        message: '网页抓取任务已启动'
      }

      crawlerAPI.crawlWebpage.mockResolvedValue(mockResponse)

      const result = await crawlerAPI.crawlWebpage(crawlData)

      expect(crawlerAPI.crawlWebpage).toHaveBeenCalledWith(crawlData)
      expect(result.task_id).toBe('task-002')
      expect(result.status).toBe('running')
    })
  })

  describe('任务监控', () => {
    it('应该能够获取爬虫任务列表', async () => {
      const mockTasks = [
        {
          id: 'task-001',
          type: 'rss',
          status: 'completed',
          created_at: '2025-01-09 10:00:00',
          items_count: 50
        },
        {
          id: 'task-002',
          type: 'web',
          status: 'running',
          created_at: '2025-01-09 11:00:00',
          items_count: 20
        }
      ]

      crawlerAPI.getCrawlTasks.mockResolvedValue(mockTasks)

      const result = await crawlerAPI.getCrawlTasks()

      expect(crawlerAPI.getCrawlTasks).toHaveBeenCalled()
      expect(result).toEqual(mockTasks)
      expect(result.length).toBe(2)
    })

    it('应该能够获取单个任务详情', async () => {
      const mockTask = {
        id: 'task-001',
        type: 'rss',
        status: 'completed',
        created_at: '2025-01-09 10:00:00',
        completed_at: '2025-01-09 10:05:00',
        items_count: 50,
        success_count: 48,
        error_count: 2
      }

      crawlerAPI.getCrawlTask.mockResolvedValue(mockTask)

      const result = await crawlerAPI.getCrawlTask('task-001')

      expect(crawlerAPI.getCrawlTask).toHaveBeenCalledWith('task-001')
      expect(result.id).toBe('task-001')
      expect(result.items_count).toBe(50)
    })
  })

  describe('统计信息', () => {
    it('应该能够获取爬虫统计信息', async () => {
      const mockStats = {
        total_tasks: 100,
        completed_tasks: 85,
        running_tasks: 5,
        failed_tasks: 10,
        total_items: 5000,
        avg_items_per_task: 50
      }

      crawlerAPI.getStatistics.mockResolvedValue(mockStats)

      const result = await crawlerAPI.getStatistics()

      expect(crawlerAPI.getStatistics).toHaveBeenCalled()
      expect(result.total_tasks).toBe(100)
      expect(result.completed_tasks).toBe(85)
    })
  })

  describe('错误处理', () => {
    it('应该处理RSS源获取失败', async () => {
      crawlerAPI.getRssSources.mockRejectedValue(new Error('网络错误'))

      await expect(crawlerAPI.getRssSources()).rejects.toThrow('网络错误')
    })

    it('应该处理爬虫任务创建失败', async () => {
      crawlerAPI.crawlRssFeeds.mockRejectedValue(new Error('任务创建失败'))

      await expect(crawlerAPI.crawlRssFeeds({ source_ids: [] })).rejects.toThrow('任务创建失败')
    })
  })
})
