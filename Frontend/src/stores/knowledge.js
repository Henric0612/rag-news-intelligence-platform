import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { 
  getKnowledgeList, 
  getKnowledgeDetail, 
  createKnowledge, 
  updateKnowledge, 
  deleteKnowledge,
  batchDeleteKnowledge,
  getKnowledgeStats,
  syncVectorForItem,
  batchSyncVectors
} from '@/api/knowledge'
import { ElMessage } from 'element-plus'

export const useKnowledgeStore = defineStore('knowledge', () => {
  // 状态
  const knowledgeList = ref([])
  const currentKnowledge = ref(null)
  const stats = ref({})
  const loading = ref(false)
  const pagination = ref({
    page: 1,
    pageSize: 20,
    total: 0
  })
  const filters = ref({
    category: '',
    source_type: '',
    keyword: ''
  })

  // 计算属性
  const hasData = computed(() => knowledgeList.value.length > 0)
  const totalPages = computed(() => Math.ceil(pagination.value.total / pagination.value.pageSize))

  // 获取知识库列表
  const fetchKnowledgeList = async (params = {}) => {
    try {
      loading.value = true
      const queryParams = {
        page: pagination.value.page,
        page_size: pagination.value.pageSize,
        ...filters.value,
        ...params
      }
      
      const response = await getKnowledgeList(queryParams)
      
      if (response && response.items) {
        knowledgeList.value = response.items
        pagination.value.total = response.total || 0
        pagination.value.page = response.page || 1
        pagination.value.pageSize = response.per_page || 20
      } else {
        knowledgeList.value = response || []
        pagination.value.total = knowledgeList.value.length
      }
      
      return knowledgeList.value
    } catch (error) {
      console.error('获取知识库列表失败:', error)
      ElMessage.error('获取知识库列表失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  // 获取知识库详情
  const fetchKnowledgeDetail = async (id) => {
    try {
      loading.value = true
      const response = await getKnowledgeDetail(id)
      currentKnowledge.value = response
      return response
    } catch (error) {
      console.error('获取知识库详情失败:', error)
      ElMessage.error('获取知识库详情失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  // 创建知识库条目
  const createKnowledgeItem = async (data) => {
    try {
      loading.value = true
      const response = await createKnowledge(data)
      
      // 刷新列表和统计数据
      await fetchKnowledgeList()
      await fetchStats()
      
      ElMessage.success('创建成功')
      return response
    } catch (error) {
      console.error('创建知识库条目失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 更新知识库条目
  const updateKnowledgeItem = async (id, data) => {
    try {
      loading.value = true
      const response = await updateKnowledge(id, data)
      
      // 更新列表中的对应项
      const index = knowledgeList.value.findIndex(item => item.id === id)
      if (index !== -1) {
        knowledgeList.value[index] = { ...knowledgeList.value[index], ...data }
      }
      
      // 更新当前详情
      if (currentKnowledge.value && currentKnowledge.value.id === id) {
        currentKnowledge.value = { ...currentKnowledge.value, ...data }
      }
      
      ElMessage.success('更新成功')
      return response
    } catch (error) {
      console.error('更新知识库条目失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 删除知识库条目
  const deleteKnowledgeItem = async (id) => {
    try {
      loading.value = true
      await deleteKnowledge(id)
      
      // 从列表中移除
      knowledgeList.value = knowledgeList.value.filter(item => item.id !== id)
      pagination.value.total -= 1
      
      // 清除当前详情
      if (currentKnowledge.value && currentKnowledge.value.id === id) {
        currentKnowledge.value = null
      }
      
      // 🔄 删除后立即刷新统计数据
      await fetchStats()
      
      ElMessage.success('删除成功')
    } catch (error) {
      console.error('删除知识库条目失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 批量删除知识库条目
  const batchDeleteKnowledgeItems = async (ids) => {
    try {
      loading.value = true
      await batchDeleteKnowledge(ids)
      
      // 从列表中移除
      knowledgeList.value = knowledgeList.value.filter(item => !ids.includes(item.id))
      pagination.value.total -= ids.length
      
      // 🔄 批量删除后立即刷新统计数据
      await fetchStats()
      
      ElMessage.success(`成功删除 ${ids.length} 个条目`)
    } catch (error) {
      console.error('批量删除知识库条目失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 获取统计信息
  const fetchStats = async () => {
    try {
      const response = await getKnowledgeStats()
      console.log('📊 Stats API Response:', response)
      console.log('📊 Stats vectorized:', response?.vectorized)
      console.log('📊 Stats not_vectorized:', response?.not_vectorized)
      stats.value = response || {}
      console.log('📊 Stats value after assignment:', stats.value)
      return stats.value
    } catch (error) {
      console.error('获取统计信息失败:', error)
      ElMessage.error('获取统计信息失败')
      throw error
    }
  }

  // 设置分页
  const setPagination = (page, pageSize) => {
    pagination.value.page = page
    pagination.value.pageSize = pageSize
  }

  // 设置筛选条件
  const setFilters = (newFilters) => {
    filters.value = { ...filters.value, ...newFilters }
  }

  // 重置筛选条件
  const resetFilters = () => {
    filters.value = {
      category: '',
      source_type: '',
      keyword: ''
    }
  }

  // 搜索
  const search = async (keyword) => {
    setFilters({ keyword })
    return await fetchKnowledgeList()
  }

  // 单条目向量同步
  const syncVectorForKnowledgeItem = async (id, forceResync = false) => {
    try {
      loading.value = true
      const response = await syncVectorForItem(id, forceResync)
      
      // 更新列表中的对应项
      const index = knowledgeList.value.findIndex(item => item.id === id)
      if (index !== -1 && response.vector_id) {
        knowledgeList.value[index].vector_id = response.vector_id
        knowledgeList.value[index].status = 'processed'
      }
      
      // 更新当前详情
      if (currentKnowledge.value && currentKnowledge.value.id === id && response.vector_id) {
        currentKnowledge.value.vector_id = response.vector_id
        currentKnowledge.value.status = 'processed'
      }
      
      // 🔄 向量同步成功后立即刷新统计数据
      await fetchStats()
      
      ElMessage.success(response.message || '向量同步成功')
      return response
    } catch (error) {
      console.error('向量同步失败:', error)
      ElMessage.error('向量同步失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  // 批量向量同步
  const batchSyncVectorsForItems = async (params = {}) => {
    try {
      loading.value = true
      const response = await batchSyncVectors(params)
      
      // 刷新列表和统计数据以获取最新状态
      await fetchKnowledgeList()
      await fetchStats()
      
      ElMessage.success(response.message || '批量同步完成')
      return response
    } catch (error) {
      console.error('批量向量同步失败:', error)
      ElMessage.error('批量向量同步失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  // 重置状态
  const reset = () => {
    knowledgeList.value = []
    currentKnowledge.value = null
    stats.value = {}
    pagination.value = {
      page: 1,
      pageSize: 20,
      total: 0
    }
    resetFilters()
  }

  return {
    // 状态
    knowledgeList,
    currentKnowledge,
    stats,
    loading,
    pagination,
    filters,
    
    // 计算属性
    hasData,
    totalPages,
    
    // 方法
    fetchKnowledgeList,
    fetchKnowledgeDetail,
    createKnowledgeItem,
    updateKnowledgeItem,
    deleteKnowledgeItem,
    batchDeleteKnowledgeItems,
    fetchStats,
    setPagination,
    setFilters,
    resetFilters,
    search,
    reset,
    syncVectorForKnowledgeItem,
    batchSyncVectorsForItems
  }
})
