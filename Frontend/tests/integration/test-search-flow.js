/**
 * 搜索流程集成测试
 * 测试用例ID: FRONT-INT-001
 * 对应测试计划: Sprint 3 - 应用功能层
 * 测试描述: 搜索Store + Mock API集成测试
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSearchStore } from '@/stores/search'

// Mock API
vi.mock('@/api/search', () => ({
  searchQuery: vi.fn(),
  getSearchSuggestions: vi.fn(),
  getSearchHistory: vi.fn(),
  getSearchStats: vi.fn()
}))

describe('搜索流程集成测试', () => {
  let pinia
  let searchStore

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    searchStore = useSearchStore()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('完整搜索流程', () => {
    it('应该完成从查询到结果展示的完整流程', async () => {
      const { searchQuery } = await import('@/api/search')
      const mockResults = [
        { id: 1, title: '人工智能基础', content: '内容1', score: 0.9 },
        { id: 2, title: '机器学习入门', content: '内容2', score: 0.8 }
      ]
      searchQuery.mockResolvedValue({
        results: mockResults,
        total: 2,
        response_time: 150
      })

      // 执行搜索
      await searchStore.performSearch('人工智能')

      // 验证API被调用
      expect(searchQuery).toHaveBeenCalledWith(
        expect.objectContaining({ query: '人工智能' })
      )

      // 验证Store状态更新
      expect(searchStore.currentQuery).toBe('人工智能')
      expect(searchStore.searchResults).toEqual(mockResults)
      expect(searchStore.searchTotal).toBe(2)
      expect(searchStore.searchResponseTime).toBe(150)
    })

    it('应该处理搜索建议流程', async () => {
      const { getSearchSuggestions } = await import('@/api/search')
      const mockSuggestions = ['人工智能', '人工智能应用', '人工智能技术']
      getSearchSuggestions.mockResolvedValue(mockSuggestions)

      // 获取搜索建议
      await searchStore.fetchSearchSuggestions('人工')

      // 验证API被调用
      expect(getSearchSuggestions).toHaveBeenCalledWith('人工')

      // 验证Store状态
      expect(searchStore.searchSuggestions).toEqual(mockSuggestions)
    })

    it('应该保存搜索历史', async () => {
      const { searchQuery } = await import('@/api/search')
      searchQuery.mockResolvedValue({
        results: [],
        total: 0,
        response_time: 50
      })

      // 执行搜索
      await searchStore.performSearch('测试查询')

      // 验证搜索历史被更新
      expect(searchStore.searchHistory.length).toBeGreaterThan(0)
      expect(searchStore.searchHistory[0].query).toBe('测试查询')
    })

    it('应该处理多次搜索', async () => {
      const { searchQuery } = await import('@/api/search')
      searchQuery.mockResolvedValue({
        results: [],
        total: 0,
        response_time: 50
      })

      // 执行多次搜索
      await searchStore.performSearch('查询1')
      await searchStore.performSearch('查询2')
      await searchStore.performSearch('查询3')

      // 验证搜索历史（最新的在最前面）
      expect(searchStore.searchHistory.length).toBe(3)
      expect(searchStore.searchHistory[0].query).toBe('查询3')
      expect(searchStore.searchHistory[1].query).toBe('查询2')
      expect(searchStore.searchHistory[2].query).toBe('查询1')
      expect(searchQuery).toHaveBeenCalledTimes(3)
    })
  })

  describe('搜索错误处理', () => {
    it('应该处理API错误', async () => {
      const { searchQuery } = await import('@/api/search')
      searchQuery.mockRejectedValue(new Error('网络错误'))

      // 执行搜索并期望抛出错误
      await expect(searchStore.performSearch('测试')).rejects.toThrow()

      // 验证加载状态被重置
      expect(searchStore.searching).toBe(false)
    })

    it('应该处理空查询', async () => {
      // 执行空查询
      await expect(searchStore.performSearch('')).rejects.toThrow('搜索内容不能为空')
      await expect(searchStore.performSearch('   ')).rejects.toThrow('搜索内容不能为空')
    })

    it('应该处理空结果', async () => {
      const { searchQuery } = await import('@/api/search')
      searchQuery.mockResolvedValue({
        results: [],
        total: 0,
        response_time: 100
      })

      await searchStore.performSearch('不存在的内容')

      // 验证空结果被正确处理
      expect(searchStore.searchResults).toEqual([])
      expect(searchStore.searchTotal).toBe(0)
      expect(searchStore.hasResults).toBe(false)
    })
  })

  describe('搜索状态管理', () => {
    it('应该正确管理加载状态', async () => {
      const { searchQuery } = await import('@/api/search')
      searchQuery.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({
          results: [],
          total: 0,
          response_time: 100
        }), 100))
      )

      // 开始搜索
      const searchPromise = searchStore.performSearch('测试')

      // 验证加载状态
      expect(searchStore.searching).toBe(true)

      // 等待搜索完成
      await searchPromise

      // 验证加载完成
      expect(searchStore.searching).toBe(false)
    })

    it('应该在错误时重置加载状态', async () => {
      const { searchQuery } = await import('@/api/search')
      searchQuery.mockRejectedValue(new Error('错误'))

      // 执行搜索
      try {
        await searchStore.performSearch('测试')
      } catch (e) {
        // 忽略错误
      }

      // 验证加载状态被重置
      expect(searchStore.searching).toBe(false)
    })
  })

  describe('搜索历史管理', () => {
    it('应该能够清空搜索历史', async () => {
      const { searchQuery } = await import('@/api/search')
      searchQuery.mockResolvedValue({
        results: [],
        total: 0,
        response_time: 50
      })

      // 添加搜索历史
      await searchStore.performSearch('查询1')
      await searchStore.performSearch('查询2')

      // 清空历史
      searchStore.clearSearchHistory()

      // 验证历史被清空
      expect(searchStore.searchHistory).toEqual([])
    })
  })

  describe('搜索结果管理', () => {
    it('应该能够清空搜索结果', async () => {
      const { searchQuery } = await import('@/api/search')
      searchQuery.mockResolvedValue({
        results: [{ id: 1, title: '测试' }],
        total: 1,
        response_time: 50
      })

      // 执行搜索
      await searchStore.performSearch('测试')
      expect(searchStore.hasResults).toBe(true)

      // 清空结果
      searchStore.clearSearchResults()

      // 验证结果被清空
      expect(searchStore.searchResults).toEqual([])
      expect(searchStore.hasResults).toBe(false)
    })
  })

  describe('搜索配置', () => {
    it('应该能够更新搜索配置', () => {
      const newConfig = {
        limit: 20,
        use_rerank: false
      }

      searchStore.updateSearchConfig(newConfig)

      expect(searchStore.searchConfig.limit).toBe(20)
      expect(searchStore.searchConfig.use_rerank).toBe(false)
    })

    it('应该使用更新后的配置进行搜索', async () => {
      const { searchQuery } = await import('@/api/search')
      searchQuery.mockResolvedValue({
        results: [],
        total: 0,
        response_time: 50
      })

      // 更新配置
      searchStore.updateSearchConfig({ limit: 20 })

      // 执行搜索
      await searchStore.performSearch('测试')

      // 验证API调用包含新配置
      expect(searchQuery).toHaveBeenCalledWith(
        expect.objectContaining({ limit: 20 })
      )
    })
  })
})
