/**
 * 知识库管理流程集成测试
 * 测试用例ID: FRONT-INT-003
 * 对应测试计划: Sprint 3 - 应用功能层
 * 测试描述: 知识库Store + Mock API集成测试
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useKnowledgeStore } from '@/stores/knowledge'

// Mock API
vi.mock('@/api/knowledge', () => ({
  getKnowledgeList: vi.fn(),
  getKnowledgeDetail: vi.fn(),
  createKnowledge: vi.fn(),
  updateKnowledge: vi.fn(),
  deleteKnowledge: vi.fn(),
  batchDeleteKnowledge: vi.fn()
}))

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn()
  }
}))

describe('知识库管理流程集成测试', () => {
  let pinia
  let knowledgeStore

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    knowledgeStore = useKnowledgeStore()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('知识库列表加载', () => {
    it('应该完成列表加载流程', async () => {
      const { getKnowledgeList } = await import('@/api/knowledge')
      const mockList = [
        { id: 1, title: '文档1', content: '内容1', source: 'upload' },
        { id: 2, title: '文档2', content: '内容2', source: 'crawler' }
      ]
      
      getKnowledgeList.mockResolvedValue({
        items: mockList,
        total: 2,
        page: 1,
        per_page: 20
      })

      // 加载列表
      await knowledgeStore.fetchKnowledgeList()

      // 验证API被调用
      expect(getKnowledgeList).toHaveBeenCalled()

      // 验证Store状态
      expect(knowledgeStore.knowledgeList).toEqual(mockList)
      expect(knowledgeStore.pagination.total).toBe(2)
      expect(knowledgeStore.hasData).toBe(true)
    })

    it('应该处理分页参数', async () => {
      const { getKnowledgeList } = await import('@/api/knowledge')
      getKnowledgeList.mockResolvedValue({
        items: [],
        total: 0,
        page: 2,
        per_page: 10
      })

      // 设置分页
      knowledgeStore.setPagination(2, 10)

      // 加载列表
      await knowledgeStore.fetchKnowledgeList()

      // 验证API调用包含分页参数
      expect(getKnowledgeList).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 2,
          page_size: 10
        })
      )
    })
  })

  describe('知识库创建流程', () => {
    it('应该完成创建流程', async () => {
      const { createKnowledge, getKnowledgeList } = await import('@/api/knowledge')
      const newItem = {
        title: '新文档',
        content: '新内容',
        source: 'upload'
      }
      
      const mockResponse = {
        id: 3,
        ...newItem
      }
      
      createKnowledge.mockResolvedValue(mockResponse)
      getKnowledgeList.mockResolvedValue({ items: [], total: 0 })

      // 创建知识库条目
      await knowledgeStore.createKnowledgeItem(newItem)

      // 验证API被调用
      expect(createKnowledge).toHaveBeenCalledWith(newItem)

      // 验证刷新列表
      expect(getKnowledgeList).toHaveBeenCalled()
    })
  })

  describe('知识库更新流程', () => {
    it('应该完成更新流程', async () => {
      const { updateKnowledge, getKnowledgeList } = await import('@/api/knowledge')
      
      // 先设置初始数据
      getKnowledgeList.mockResolvedValue({
        items: [
          { id: 1, title: '文档1', content: '内容1' }
        ],
        total: 1
      })
      await knowledgeStore.fetchKnowledgeList()

      const updateData = {
        title: '更新后的文档',
        content: '更新后的内容'
      }
      
      const mockResponse = {
        id: 1,
        ...updateData
      }
      
      updateKnowledge.mockResolvedValue(mockResponse)

      // 更新知识库条目
      await knowledgeStore.updateKnowledgeItem(1, updateData)

      // 验证API被调用
      expect(updateKnowledge).toHaveBeenCalledWith(1, updateData)

      // 验证本地状态更新
      const updatedItem = knowledgeStore.knowledgeList.find(item => item.id === 1)
      expect(updatedItem.title).toBe('更新后的文档')
    })
  })

  describe('知识库删除流程', () => {
    it('应该完成删除流程', async () => {
      const { deleteKnowledge, getKnowledgeList } = await import('@/api/knowledge')
      
      // 先设置初始数据
      getKnowledgeList.mockResolvedValue({
        items: [
          { id: 1, title: '文档1', content: '内容1' },
          { id: 2, title: '文档2', content: '内容2' }
        ],
        total: 2
      })
      await knowledgeStore.fetchKnowledgeList()

      deleteKnowledge.mockResolvedValue({ success: true })

      // 删除知识库条目
      await knowledgeStore.deleteKnowledgeItem(1)

      // 验证API被调用
      expect(deleteKnowledge).toHaveBeenCalledWith(1)

      // 验证本地状态更新
      expect(knowledgeStore.knowledgeList.length).toBe(1)
      expect(knowledgeStore.knowledgeList.find(item => item.id === 1)).toBeUndefined()
      expect(knowledgeStore.pagination.total).toBe(1)
    })

    it('应该支持批量删除', async () => {
      const { batchDeleteKnowledge, getKnowledgeList } = await import('@/api/knowledge')
      
      // 先设置初始数据
      getKnowledgeList.mockResolvedValue({
        items: [
          { id: 1, title: '文档1' },
          { id: 2, title: '文档2' },
          { id: 3, title: '文档3' }
        ],
        total: 3
      })
      await knowledgeStore.fetchKnowledgeList()

      batchDeleteKnowledge.mockResolvedValue({ success: true })

      // 批量删除
      await knowledgeStore.batchDeleteKnowledgeItems([1, 2])

      // 验证API被调用
      expect(batchDeleteKnowledge).toHaveBeenCalledWith([1, 2])

      // 验证本地状态更新
      expect(knowledgeStore.knowledgeList.length).toBe(1)
      expect(knowledgeStore.pagination.total).toBe(1)
    })
  })

  describe('知识库过滤和搜索', () => {
    it('应该支持过滤功能', async () => {
      const { getKnowledgeList } = await import('@/api/knowledge')
      getKnowledgeList.mockResolvedValue({
        items: [
          { id: 1, title: '文档1', source: 'upload' }
        ],
        total: 1
      })

      // 设置过滤条件
      knowledgeStore.setFilters({ source: 'upload' })

      // 加载列表
      await knowledgeStore.fetchKnowledgeList()

      // 验证API调用包含过滤参数
      expect(getKnowledgeList).toHaveBeenCalledWith(
        expect.objectContaining({
          source: 'upload'
        })
      )
    })

    it('应该支持搜索功能', async () => {
      const { getKnowledgeList } = await import('@/api/knowledge')
      getKnowledgeList.mockResolvedValue({
        items: [
          { id: 1, title: '机器学习', content: '内容' }
        ],
        total: 1
      })

      // 执行搜索
      await knowledgeStore.search('机器学习')

      // 验证API调用包含搜索参数
      expect(getKnowledgeList).toHaveBeenCalledWith(
        expect.objectContaining({
          keyword: '机器学习'
        })
      )
    })

    it('应该能够清除过滤条件', async () => {
      const { getKnowledgeList } = await import('@/api/knowledge')
      getKnowledgeList.mockResolvedValue({ items: [], total: 0 })

      // 设置过滤条件
      knowledgeStore.setFilters({ source: 'upload' })
      expect(knowledgeStore.filters.source).toBe('upload')

      // 重置
      knowledgeStore.reset()

      // 验证过滤条件被清除
      expect(knowledgeStore.filters.source).toBeUndefined()
    })
  })

  describe('知识库详情', () => {
    it('应该能够获取知识库详情', async () => {
      const { getKnowledgeDetail } = await import('@/api/knowledge')
      const mockDetail = {
        id: 1,
        title: '文档1',
        content: '详细内容',
        source: 'upload',
        created_at: '2025-01-09'
      }
      
      getKnowledgeDetail.mockResolvedValue(mockDetail)

      // 获取详情
      await knowledgeStore.fetchKnowledgeDetail(1)

      // 验证API被调用
      expect(getKnowledgeDetail).toHaveBeenCalledWith(1)

      // 验证Store状态
      expect(knowledgeStore.currentKnowledge).toEqual(mockDetail)
    })
  })

  describe('错误处理', () => {
    it('应该处理加载错误', async () => {
      const { getKnowledgeList } = await import('@/api/knowledge')
      getKnowledgeList.mockRejectedValue(new Error('网络错误'))

      // 执行加载（不应该抛出错误，内部已处理）
      try {
        await knowledgeStore.fetchKnowledgeList()
      } catch (e) {
        // Store 内部捕获了错误
      }

      // 验证加载状态被重置
      expect(knowledgeStore.loading).toBe(false)
      expect(knowledgeStore.knowledgeList).toEqual([])
    })

    it('应该处理创建错误', async () => {
      const { createKnowledge } = await import('@/api/knowledge')
      createKnowledge.mockRejectedValue(new Error('创建失败'))

      // 执行创建
      await expect(
        knowledgeStore.createKnowledgeItem({ title: '测试' })
      ).rejects.toThrow()

      // 验证加载状态被重置
      expect(knowledgeStore.loading).toBe(false)
    })
  })

  describe('统计信息', () => {
    it('应该能够获取统计信息', async () => {
      const { getKnowledgeList } = await import('@/api/knowledge')
      
      // Mock stats API
      const mockStats = {
        total: 100,
        by_source: {
          upload: 60,
          crawler: 40
        }
      }

      // 注意：实际实现中可能需要单独的 stats API
      getKnowledgeList.mockResolvedValue({
        items: [],
        total: 100,
        stats: mockStats
      })

      await knowledgeStore.fetchKnowledgeList()

      // 验证统计信息
      expect(knowledgeStore.pagination.total).toBe(100)
    })
  })
})
