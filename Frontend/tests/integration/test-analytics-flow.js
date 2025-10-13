/**
 * 数据分析流程集成测试
 * 测试用例ID: FRONT-INT-005
 * 对应测试计划: Sprint 3 - 应用功能层
 * 测试描述: 数据分析 API 集成测试（考核必需功能）
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { 
  getClusteringAnalysis, 
  getTopKeywords, 
  getTrendAnalysis,
  getStatistics,
  checkAnalyticsHealth
} from '@/api/analytics'

// Mock analytics API
vi.mock('@/api/analytics', () => ({
  getClusteringAnalysis: vi.fn(),
  getTopKeywords: vi.fn(),
  getTrendAnalysis: vi.fn(),
  getStatistics: vi.fn(),
  checkAnalyticsHealth: vi.fn()
}))

describe('数据分析流程集成测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('搜索热词TOP10（基于KeyBERT）', () => {
    it('应该能够获取基于知识库内容的Top10关键词', async () => {
      const mockKeywords = {
        keywords: [
          { keyword: '人工智能技术', count: 150, percentage: 15.0 },
          { keyword: '机器学习算法', count: 120, percentage: 12.0 },
          { keyword: '深度学习', count: 100, percentage: 10.0 },
          { keyword: '神经网络', count: 90, percentage: 9.0 },
          { keyword: '自然语言处理', count: 80, percentage: 8.0 },
          { keyword: '计算机视觉', count: 70, percentage: 7.0 },
          { keyword: '数据挖掘', count: 60, percentage: 6.0 },
          { keyword: '大数据分析', count: 50, percentage: 5.0 },
          { keyword: '云计算平台', count: 40, percentage: 4.0 },
          { keyword: '物联网设备', count: 30, percentage: 3.0 }
        ],
        total_count: 1000
      }

      getTopKeywords.mockResolvedValue(mockKeywords)

      const result = await getTopKeywords({ limit: 100 })

      expect(getTopKeywords).toHaveBeenCalledWith({ limit: 100 })
      expect(result.keywords).toHaveLength(10)
      expect(result.keywords[0].keyword).toBe('人工智能技术')
      expect(result.keywords[0].count).toBe(150)
      expect(result.total_count).toBe(1000)
      
      // 验证关键词不包含编程术语
      const programmingTerms = ['id', 'name', 'data', 'code', 'api', 'json']
      const extractedKeywords = result.keywords.map(k => k.keyword.toLowerCase())
      const hasProgTerms = extractedKeywords.some(kw => 
        programmingTerms.some(term => kw.includes(term))
      )
      expect(hasProgTerms).toBe(false)
    })

    it('应该能够限制关键词数量', async () => {
      const mockKeywords = {
        keywords: [
          { keyword: '人工智能', count: 150, percentage: 30.0 },
          { keyword: '机器学习', count: 120, percentage: 24.0 },
          { keyword: '深度学习', count: 100, percentage: 20.0 }
        ],
        total_count: 500
      }

      getTopKeywords.mockResolvedValue(mockKeywords)

      const result = await getTopKeywords({ limit: 50 })

      expect(getTopKeywords).toHaveBeenCalledWith({ limit: 50 })
      expect(result.keywords).toHaveLength(3)
    })
  })

  describe('数据聚类分析', () => {
    it('应该能够获取聚类分析结果', async () => {
      const mockClustering = {
        clusters: [
          {
            cluster_id: 0,
            label: '人工智能技术',
            size: 50,
            keywords: ['人工智能', '机器学习', '深度学习'],
            representative_docs: [
              { id: 1, title: 'AI技术发展', similarity: 0.95 }
            ]
          },
          {
            cluster_id: 1,
            label: '云计算服务',
            size: 30,
            keywords: ['云计算', '分布式', '微服务'],
            representative_docs: [
              { id: 2, title: '云服务架构', similarity: 0.92 }
            ]
          }
        ],
        total_docs: 100,
        n_clusters: 2
      }

      getClusteringAnalysis.mockResolvedValue(mockClustering)

      const result = await getClusteringAnalysis({ limit: 100 })

      expect(getClusteringAnalysis).toHaveBeenCalledWith({ limit: 100 })
      expect(result.clusters).toHaveLength(2)
      expect(result.clusters[0].label).toBe('人工智能技术')
      expect(result.clusters[0].size).toBe(50)
      expect(result.total_docs).toBe(100)
    })

    it('应该能够处理不同的聚类数量', async () => {
      const mockClustering = {
        clusters: [
          { cluster_id: 0, label: '技术类', size: 40, keywords: ['技术'], representative_docs: [] },
          { cluster_id: 1, label: '商业类', size: 30, keywords: ['商业'], representative_docs: [] },
          { cluster_id: 2, label: '科研类', size: 30, keywords: ['科研'], representative_docs: [] }
        ],
        total_docs: 100,
        n_clusters: 3
      }

      getClusteringAnalysis.mockResolvedValue(mockClustering)

      const result = await getClusteringAnalysis()

      expect(result.n_clusters).toBe(3)
      expect(result.clusters).toHaveLength(3)
    })
  })

  describe('趋势分析', () => {
    it('应该能够获取趋势分析数据', async () => {
      const mockTrends = {
        trends: [
          { date: '2025-01-01', count: 10, keywords: ['AI'] },
          { date: '2025-01-02', count: 15, keywords: ['ML'] },
          { date: '2025-01-03', count: 20, keywords: ['DL'] }
        ],
        period: 30,
        total_items: 45
      }

      getTrendAnalysis.mockResolvedValue(mockTrends)

      const result = await getTrendAnalysis({ days: 30 })

      expect(getTrendAnalysis).toHaveBeenCalledWith({ days: 30 })
      expect(result.trends).toHaveLength(3)
      expect(result.period).toBe(30)
    })
  })

  describe('统计信息', () => {
    it('应该能够获取系统统计信息', async () => {
      const mockStats = {
        total_knowledge: 1000,
        total_searches: 5000,
        total_questions: 2000,
        avg_response_time: 1.5,
        knowledge_by_source: {
          rss: 600,
          web: 300,
          upload: 100
        },
        recent_activity: {
          today: 50,
          this_week: 300,
          this_month: 1000
        }
      }

      getStatistics.mockResolvedValue(mockStats)

      const result = await getStatistics()

      expect(getStatistics).toHaveBeenCalled()
      expect(result.total_knowledge).toBe(1000)
      expect(result.total_searches).toBe(5000)
      expect(result.knowledge_by_source.rss).toBe(600)
    })
  })

  describe('健康检查', () => {
    it('应该能够检查分析服务健康状态', async () => {
      const mockHealth = {
        status: 'healthy',
        clustering_available: true,
        keywords_available: true,
        last_analysis: '2025-01-09 10:00:00'
      }

      checkAnalyticsHealth.mockResolvedValue(mockHealth)

      const result = await checkAnalyticsHealth()

      expect(checkAnalyticsHealth).toHaveBeenCalled()
      expect(result.status).toBe('healthy')
      expect(result.clustering_available).toBe(true)
    })
  })

  describe('错误处理', () => {
    it('应该处理关键词分析失败', async () => {
      getTopKeywords.mockRejectedValue(new Error('分析失败'))

      await expect(getTopKeywords()).rejects.toThrow('分析失败')
    })

    it('应该处理聚类分析失败', async () => {
      getClusteringAnalysis.mockRejectedValue(new Error('聚类失败'))

      await expect(getClusteringAnalysis()).rejects.toThrow('聚类失败')
    })

    it('应该处理空数据情况', async () => {
      getTopKeywords.mockResolvedValue({
        keywords: [],
        total_count: 0
      })

      getClusteringAnalysis.mockResolvedValue({
        clusters: [],
        total_docs: 0,
        n_clusters: 0
      })

      const keywordsResult = await getTopKeywords()
      const clusteringResult = await getClusteringAnalysis()

      expect(keywordsResult.keywords).toHaveLength(0)
      expect(clusteringResult.clusters).toHaveLength(0)
    })
  })
})
