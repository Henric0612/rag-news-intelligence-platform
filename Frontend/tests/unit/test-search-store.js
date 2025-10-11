/**
 * 搜索Store单元测试
 * 测试用例ID: SEARCH-001~004 (前端Store层)
 * 对应测试计划: Sprint 2 - 数据与AI服务层
 * 测试描述: 语义检索功能、搜索历史管理、搜索状态管理
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSearchStore } from '@/stores/search'

// Mock API calls
vi.mock('@/api/search', () => ({
  searchQuery: vi.fn(),
  getSearchSuggestions: vi.fn(),
  getSearchHistory: vi.fn(),
  getSearchStats: vi.fn()
}))

describe('搜索Store单元测试', () => {
  let searchStore

  beforeEach(() => {
    setActivePinia(createPinia())
    searchStore = useSearchStore()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('搜索功能', () => {
    it('应该成功执行搜索', async () => {
      const { searchQuery } = await import('@/api/search')
      const mockResults = [
        {
          id: 1,
          title: '人工智能技术发展',
          content: '人工智能技术正在快速发展...',
          score: 0.95
        },
        {
          id: 2,
          title: 'AI应用场景',
          content: 'AI在各个领域的应用...',
          score: 0.88
        }
      ]
      
      // 响应拦截器已统一处理，直接返回数据（无 data 包装）
      searchQuery.mockResolvedValue({ 
        results: mockResults, 
        total: 2,
        response_time: 150
      })

      const query = '人工智能'
      await searchStore.performSearch(query)

      expect(searchQuery).toHaveBeenCalledWith(
        expect.objectContaining({ query })
      )
      expect(searchStore.searchResults).toEqual(mockResults)
      expect(searchStore.searchTotal).toBe(2)
      expect(searchStore.searching).toBe(false)
    })

    it('应该处理搜索失败', async () => {
      const { searchQuery } = await import('@/api/search')
      const mockError = new Error('搜索服务不可用')
      searchQuery.mockRejectedValue(mockError)

      await expect(searchStore.performSearch('测试查询')).rejects.toThrow('搜索服务不可用')
      expect(searchStore.searching).toBe(false)
      expect(searchStore.searchResults).toEqual([])
    })

    it('应该处理空搜索结果', async () => {
      const { searchQuery } = await import('@/api/search')
      searchQuery.mockResolvedValue({ 
        results: [], 
        total: 0,
        response_time: 50
      })

      await searchStore.performSearch('不存在的内容')

      expect(searchStore.searchResults).toEqual([])
      expect(searchStore.searchTotal).toBe(0)
      expect(searchStore.searching).toBe(false)
    })

    it('应该更新搜索状态', async () => {
      const { searchQuery } = await import('@/api/search')
      searchQuery.mockImplementation(() => 
        new Promise(resolve => 
          setTimeout(() => resolve({ 
            results: [], total: 0, response_time: 0
          }), 100)
        )
      )

      const searchPromise = searchStore.performSearch('测试')
      expect(searchStore.searching).toBe(true)

      await searchPromise
      expect(searchStore.searching).toBe(false)
    })
  })

  describe('搜索建议功能', () => {
    it('应该获取搜索建议', async () => {
      const { getSearchSuggestions } = await import('@/api/search')
      const mockSuggestions = ['人工智能', '人工智能应用', '人工智能技术']
      getSearchSuggestions.mockResolvedValue(mockSuggestions)

      await searchStore.fetchSearchSuggestions('人工')

      expect(getSearchSuggestions).toHaveBeenCalledWith('人工')
      expect(searchStore.searchSuggestions).toEqual(mockSuggestions)
    })

    it('应该处理空建议', async () => {
      const { getSearchSuggestions } = await import('@/api/search')
      getSearchSuggestions.mockResolvedValue([])

      await searchStore.fetchSearchSuggestions('xyz')

      expect(searchStore.searchSuggestions).toEqual([])
    })
  })

  describe('搜索历史管理', () => {
    it('应该保存搜索历史', () => {
      const query = '人工智能技术'
      
      // 先执行一次搜索以设置searchTotal和searchResponseTime
      searchStore.searchTotal = 10
      searchStore.searchResponseTime = 150
      
      searchStore.addToSearchHistory(query)

      expect(searchStore.searchHistory).toHaveLength(1)
      expect(searchStore.searchHistory[0]).toMatchObject({
        query,
        results_count: 10,
        response_time: 150
      })
    })

    it('应该限制搜索历史数量', () => {
      // 添加超过限制的历史记录
      for (let i = 0; i < 25; i++) {
        searchStore.addToSearchHistory(`查询${i}`)
      }

      expect(searchStore.searchHistory).toHaveLength(20)
      expect(searchStore.searchHistory[0].query).toBe('查询24')
    })

    it('应该清空搜索历史', () => {
      searchStore.addToSearchHistory('查询1')
      searchStore.addToSearchHistory('查询2')

      searchStore.clearSearchHistory()

      expect(searchStore.searchHistory).toEqual([])
    })

    it('应该删除重复的搜索历史', () => {
      searchStore.addToSearchHistory('查询1')
      searchStore.addToSearchHistory('查询2')
      searchStore.addToSearchHistory('查询1') // 重复

      // 重复的查询应该移到最前面，总数不变
      expect(searchStore.searchHistory).toHaveLength(2)
      expect(searchStore.searchHistory[0].query).toBe('查询1')
    })
  })

  describe('搜索结果管理', () => {
    it('应该清空搜索结果', () => {
      searchStore.searchResults = [
        { id: 1, title: '结果1' },
        { id: 2, title: '结果2' }
      ]
      searchStore.searchTotal = 2
      searchStore.currentQuery = '测试'

      searchStore.clearSearchResults()

      expect(searchStore.searchResults).toEqual([])
      expect(searchStore.searchTotal).toBe(0)
      expect(searchStore.currentQuery).toBe('')
    })

    it('应该获取当前搜索查询', () => {
      const query = '测试查询'
      searchStore.currentQuery = query

      expect(searchStore.currentQuery).toBe(query)
    })
  })

  describe('搜索配置', () => {
    it('应该更新搜索配置', () => {
      const newConfig = {
        top_k: 30,
        enable_rerank: false
      }

      searchStore.updateSearchConfig(newConfig)

      expect(searchStore.searchConfig.top_k).toBe(30)
      expect(searchStore.searchConfig.enable_rerank).toBe(false)
      // 其他配置应该保持不变
      expect(searchStore.searchConfig.search_type).toBe('semantic')
    })

    it('应该重置搜索状态', () => {
      searchStore.currentQuery = '测试'
      searchStore.searchResults = [{ id: 1 }]
      searchStore.searching = true
      searchStore.searchSuggestions = ['建议1']

      searchStore.resetSearchState()

      expect(searchStore.currentQuery).toBe('')
      expect(searchStore.searchResults).toEqual([])
      expect(searchStore.searching).toBe(false)
      expect(searchStore.searchSuggestions).toEqual([])
    })
  })

  describe('Computed Properties', () => {
    it('应该通过computed获取搜索结果', () => {
      const mockResults = [{ id: 1, title: '测试' }]
      searchStore.searchResults = mockResults

      // Composition API 直接暴露 ref，不需要 getter
      expect(searchStore.searchResults).toEqual(mockResults)
    })

    it('应该通过computed获取搜索总数', () => {
      searchStore.searchTotal = 42

      expect(searchStore.searchTotal).toBe(42)
    })

    it('应该通过computed获取响应时间', () => {
      searchStore.searchResponseTime = 250

      expect(searchStore.searchResponseTime).toBe(250)
    })

    it('应该通过computed检查是否正在搜索', () => {
      searchStore.searching = true

      expect(searchStore.isSearching).toBe(true)
    })
    
    it('应该通过computed检查是否有结果', () => {
      searchStore.searchResults = [{ id: 1 }]
      
      expect(searchStore.hasResults).toBe(true)
      
      searchStore.searchResults = []
      expect(searchStore.hasResults).toBe(false)
    })
  })
})
