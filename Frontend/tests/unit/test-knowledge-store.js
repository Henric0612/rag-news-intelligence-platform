/**
 * 知识库Store单元测试
 * 测试用例ID: KNOW-API-001~004 (前端Store层)
 * 对应测试计划: Sprint 2 - 数据与AI服务层
 * 测试描述: 知识库管理、CRUD操作、筛选搜索
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useKnowledgeStore } from '@/stores/knowledge'

// Mock API calls
vi.mock('@/api/knowledge', () => ({
  getKnowledgeList: vi.fn(),
  getKnowledgeDetail: vi.fn(),
  createKnowledge: vi.fn(),
  updateKnowledge: vi.fn(),
  deleteKnowledge: vi.fn(),
  batchDeleteKnowledge: vi.fn(),
  getKnowledgeStats: vi.fn()
}))

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn()
  }
}))

describe('知识库Store单元测试', () => {
  let knowledgeStore

  beforeEach(() => {
    setActivePinia(createPinia())
    knowledgeStore = useKnowledgeStore()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('知识库列表管理', () => {
    it('应该成功获取知识库列表', async () => {
      const { getKnowledgeList } = await import('@/api/knowledge')
      const mockList = [
        { id: 1, title: '人工智能基础', content: 'AI基础知识...', source: 'upload', created_at: '2024-01-01' },
        { id: 2, title: '机器学习入门', content: 'ML入门教程...', source: 'crawler', created_at: '2024-01-02' }
      ]
      
      getKnowledgeList.mockResolvedValue({
        items: mockList,
        total: 2,
        page: 1,
        per_page: 20
      })

      await knowledgeStore.fetchKnowledgeList()

      expect(getKnowledgeList).toHaveBeenCalled()
      expect(knowledgeStore.knowledgeList).toEqual(mockList)
      expect(knowledgeStore.pagination.total).toBe(2)
      expect(knowledgeStore.loading).toBe(false)
    })

    it('应该处理获取列表失败', async () => {
      const { getKnowledgeList } = await import('@/api/knowledge')
      const mockError = new Error('网络错误')
      getKnowledgeList.mockRejectedValue(mockError)

      await expect(knowledgeStore.fetchKnowledgeList()).rejects.toThrow('网络错误')
      expect(knowledgeStore.loading).toBe(false)
    })

    it('应该支持分页', async () => {
      const { getKnowledgeList } = await import('@/api/knowledge')
      
      getKnowledgeList.mockResolvedValue({
        items: [],
        total: 100,
        page: 2,
        per_page: 10
      })

      knowledgeStore.setPagination(2, 10)
      await knowledgeStore.fetchKnowledgeList()

      expect(getKnowledgeList).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 2,
          page_size: 10
        })
      )
      expect(knowledgeStore.pagination.page).toBe(2)
      expect(knowledgeStore.pagination.pageSize).toBe(10)
    })
  })

  describe('知识库项目操作', () => {
    it('应该成功获取单个知识库项目', async () => {
      const { getKnowledgeDetail } = await import('@/api/knowledge')
      const mockItem = {
        id: 1,
        title: '测试知识',
        content: '测试内容',
        source: 'upload'
      }
      
      getKnowledgeDetail.mockResolvedValue(mockItem)

      const item = await knowledgeStore.fetchKnowledgeDetail(1)

      expect(getKnowledgeDetail).toHaveBeenCalledWith(1)
      expect(item).toEqual(mockItem)
      expect(knowledgeStore.currentKnowledge).toEqual(mockItem)
    })

    it('应该成功创建知识库项目', async () => {
      const { createKnowledge, getKnowledgeList } = await import('@/api/knowledge')
      const newItem = {
        title: '新知识',
        content: '新内容',
        source: 'upload'
      }
      const mockResponse = { id: 3, ...newItem }
      
      createKnowledge.mockResolvedValue(mockResponse)
      getKnowledgeList.mockResolvedValue({ items: [], total: 0 })

      const result = await knowledgeStore.createKnowledgeItem(newItem)

      expect(createKnowledge).toHaveBeenCalledWith(newItem)
      expect(result).toEqual(mockResponse)
      // 验证刷新了列表
      expect(getKnowledgeList).toHaveBeenCalled()
    })

    it('应该成功更新知识库项目', async () => {
      const { updateKnowledge } = await import('@/api/knowledge')
      const updateData = { title: '更新后的标题' }
      const mockResponse = { success: true }
      
      // 先添加一个项目到列表
      knowledgeStore.knowledgeList = [
        { id: 1, title: '原标题', content: '内容' }
      ]
      
      updateKnowledge.mockResolvedValue(mockResponse)

      const result = await knowledgeStore.updateKnowledgeItem(1, updateData)

      expect(updateKnowledge).toHaveBeenCalledWith(1, updateData)
      expect(result).toEqual(mockResponse)
      // 验证列表中的项目已更新
      expect(knowledgeStore.knowledgeList[0].title).toBe('更新后的标题')
    })

    it('应该成功删除知识库项目', async () => {
      const { deleteKnowledge } = await import('@/api/knowledge')
      
      // 先添加项目到列表
      knowledgeStore.knowledgeList = [
        { id: 1, title: '项目1' },
        { id: 2, title: '项目2' },
        { id: 3, title: '项目3' }
      ]
      knowledgeStore.pagination.total = 3
      
      deleteKnowledge.mockResolvedValue({ success: true })

      await knowledgeStore.deleteKnowledgeItem(2)

      expect(deleteKnowledge).toHaveBeenCalledWith(2)
      expect(knowledgeStore.knowledgeList).toHaveLength(2)
      expect(knowledgeStore.knowledgeList.find(item => item.id === 2)).toBeUndefined()
      expect(knowledgeStore.pagination.total).toBe(2)
    })
  })

  describe('筛选和搜索', () => {
    it('应该设置筛选条件', () => {
      knowledgeStore.setFilters({
        category: 'AI',
        source_type: 'upload'
      })

      expect(knowledgeStore.filters.category).toBe('AI')
      expect(knowledgeStore.filters.source_type).toBe('upload')
    })

    it('应该重置筛选条件', () => {
      knowledgeStore.setFilters({
        category: 'AI',
        source_type: 'upload',
        keyword: '测试'
      })

      knowledgeStore.resetFilters()

      expect(knowledgeStore.filters).toEqual({
        category: '',
        source_type: '',
        keyword: ''
      })
    })

    it('应该支持关键词搜索', async () => {
      const { getKnowledgeList } = await import('@/api/knowledge')
      
      getKnowledgeList.mockResolvedValue({
        items: [],
        total: 0
      })

      await knowledgeStore.search('人工智能')

      expect(knowledgeStore.filters.keyword).toBe('人工智能')
      expect(getKnowledgeList).toHaveBeenCalledWith(
        expect.objectContaining({
          keyword: '人工智能'
        })
      )
    })
  })

  describe('批量操作', () => {
    it('应该支持批量删除', async () => {
      const { batchDeleteKnowledge } = await import('@/api/knowledge')
      
      // 先添加项目到列表
      knowledgeStore.knowledgeList = [
        { id: 1, title: '项目1' },
        { id: 2, title: '项目2' },
        { id: 3, title: '项目3' }
      ]
      knowledgeStore.pagination.total = 3
      
      batchDeleteKnowledge.mockResolvedValue({ success: true })

      await knowledgeStore.batchDeleteKnowledgeItems([1, 3])

      expect(batchDeleteKnowledge).toHaveBeenCalledWith([1, 3])
      expect(knowledgeStore.knowledgeList).toHaveLength(1)
      expect(knowledgeStore.knowledgeList[0].id).toBe(2)
      expect(knowledgeStore.pagination.total).toBe(1)
    })
  })

  describe('统计信息', () => {
    it('应该获取知识库统计信息', async () => {
      const { getKnowledgeStats } = await import('@/api/knowledge')
      const mockStats = {
        total: 100,
        by_source: {
          upload: 60,
          crawler: 40
        },
        by_category: {
          AI: 50,
          ML: 30,
          DL: 20
        }
      }
      
      getKnowledgeStats.mockResolvedValue(mockStats)

      const stats = await knowledgeStore.fetchStats()

      expect(getKnowledgeStats).toHaveBeenCalled()
      expect(stats).toEqual(mockStats)
      expect(knowledgeStore.stats).toEqual(mockStats)
    })
  })

  describe('状态管理', () => {
    it('应该正确设置分页', () => {
      knowledgeStore.setPagination(3, 50)

      expect(knowledgeStore.pagination.page).toBe(3)
      expect(knowledgeStore.pagination.pageSize).toBe(50)
    })

    it('应该重置所有状态', () => {
      // 设置一些状态
      knowledgeStore.knowledgeList = [{ id: 1 }]
      knowledgeStore.currentKnowledge = { id: 1 }
      knowledgeStore.stats = { total: 100 }
      knowledgeStore.setPagination(5, 30)
      knowledgeStore.setFilters({ keyword: '测试' })

      // 重置
      knowledgeStore.reset()

      expect(knowledgeStore.knowledgeList).toEqual([])
      expect(knowledgeStore.currentKnowledge).toBeNull()
      expect(knowledgeStore.stats).toEqual({})
      expect(knowledgeStore.pagination).toEqual({
        page: 1,
        pageSize: 20,
        total: 0
      })
      expect(knowledgeStore.filters).toEqual({
        category: '',
        source_type: '',
        keyword: ''
      })
    })
  })

  describe('计算属性', () => {
    it('应该正确计算hasData', () => {
      expect(knowledgeStore.hasData).toBe(false)

      knowledgeStore.knowledgeList = [{ id: 1 }]
      expect(knowledgeStore.hasData).toBe(true)
    })

    it('应该正确计算totalPages', () => {
      knowledgeStore.pagination.total = 100
      knowledgeStore.pagination.pageSize = 20

      expect(knowledgeStore.totalPages).toBe(5)

      knowledgeStore.pagination.total = 95
      expect(knowledgeStore.totalPages).toBe(5)

      knowledgeStore.pagination.total = 101
      expect(knowledgeStore.totalPages).toBe(6)
    })
  })
})
