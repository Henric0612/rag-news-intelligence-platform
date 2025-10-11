import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { searchQuery, getSearchHistory, getSearchSuggestions, getSearchStats } from '@/api/search'
import { useAsyncState } from '@/composables/useAsyncState'

/**
 * 搜索Store - 使用Composition API
 * 管理搜索状态、历史、建议和统计
 */
export const useSearchStore = defineStore('search', () => {
  // ==================== State ====================
  
  // 异步状态管理
  const { loading: searching, error: searchError, execute } = useAsyncState()
  
  // 搜索状态
  const currentQuery = ref('')
  const searchResults = ref([])
  const searchTotal = ref(0)
  const searchResponseTime = ref(0)
  
  // 搜索历史
  const searchHistory = ref([])
  const searchSuggestions = ref([])
  
  // 搜索统计
  const searchStats = ref({
    total_searches: 0,
    avg_response_time: 0,
    recent_queries: []
  })
  
  // 搜索配置
  const searchConfig = ref({
    top_k: 20,
    search_type: 'semantic',
    enable_rerank: true,
    enable_web_fallback: false
  })
  
  // ==================== Computed ====================
  
  // 是否有搜索结果
  const hasResults = computed(() => searchResults.value.length > 0)
  
  // 是否正在搜索
  const isSearching = computed(() => searching.value)
  
  // 格式化的响应时间
  const formattedResponseTime = computed(() => {
    const time = searchResponseTime.value
    return time < 1000 ? `${time}ms` : `${(time / 1000).toFixed(2)}s`
  })
  
  // 搜索历史数量
  const historyCount = computed(() => searchHistory.value.length)
  
  // ==================== Actions ====================
  
  /**
   * 执行搜索
   * @param {string} query - 搜索查询
   * @param {object} options - 搜索选项
   * @returns {Promise<object>} 搜索结果
   */
  const performSearch = async (query, options = {}) => {
    if (!query?.trim()) {
      throw new Error('搜索内容不能为空')
    }
    
    currentQuery.value = query
    
    return execute(async () => {
      const searchOptions = {
        ...searchConfig.value,
        ...options
      }
      
      const response = await searchQuery({
        query,
        ...searchOptions
      })
      
      // 响应拦截器已统一处理，直接使用 response
      if (response && response.results) {
        searchResults.value = response.results
        searchTotal.value = response.total || 0
        searchResponseTime.value = response.response_time || 0
        
        // 添加到搜索历史
        addToSearchHistory(query)
        
        return response
      } else {
        searchResults.value = []
        searchTotal.value = 0
        searchResponseTime.value = 0
        throw new Error('搜索响应格式错误')
      }
    })
  }
  
  /**
   * 获取搜索建议
   * @param {string} query - 搜索查询
   */
  const fetchSearchSuggestions = async (query) => {
    if (!query || query.length < 2) {
      searchSuggestions.value = []
      return
    }
    
    try {
      const response = await getSearchSuggestions(query)
      // 响应拦截器已统一处理，直接使用 response
      searchSuggestions.value = Array.isArray(response) ? response : (response.suggestions || [])
    } catch (error) {
      console.error('获取搜索建议失败:', error)
      searchSuggestions.value = []
    }
  }
  
  /**
   * 获取搜索历史
   * @param {object} params - 查询参数
   */
  const fetchSearchHistory = async (params = {}) => {
    try {
      const response = await getSearchHistory(params)
      // 响应拦截器已统一处理，直接使用 response
      searchHistory.value = Array.isArray(response) ? response : (response.history || [])
    } catch (error) {
      console.error('获取搜索历史失败:', error)
      searchHistory.value = []
    }
  }
  
  /**
   * 获取搜索统计
   */
  const fetchSearchStats = async () => {
    try {
      const response = await getSearchStats()
      // 响应拦截器已统一处理，直接使用 response
      searchStats.value = response || {}
    } catch (error) {
      console.error('获取搜索统计失败:', error)
    }
  }
  
  /**
   * 添加到搜索历史
   * @param {string} query - 搜索查询
   */
  const addToSearchHistory = (query) => {
    const existingIndex = searchHistory.value.findIndex(item => item.query === query)
    
    if (existingIndex !== -1) {
      // 如果已存在，移到最前面
      searchHistory.value.splice(existingIndex, 1)
    }
    
    // 添加到最前面
    searchHistory.value.unshift({
      query,
      results_count: searchTotal.value,
      response_time: searchResponseTime.value,
      created_at: new Date().toISOString()
    })
    
    // 限制历史记录数量
    if (searchHistory.value.length > 20) {
      searchHistory.value = searchHistory.value.slice(0, 20)
    }
  }
  
  /**
   * 清空搜索历史
   */
  const clearSearchHistory = () => {
    searchHistory.value = []
  }
  
  /**
   * 清空搜索结果
   */
  const clearSearchResults = () => {
    searchResults.value = []
    searchTotal.value = 0
    searchResponseTime.value = 0
    currentQuery.value = ''
  }
  
  /**
   * 更新搜索配置
   * @param {object} config - 配置对象
   */
  const updateSearchConfig = (config) => {
    searchConfig.value = { ...searchConfig.value, ...config }
  }
  
  /**
   * 重置搜索状态
   */
  const resetSearchState = () => {
    currentQuery.value = ''
    searchResults.value = []
    searchTotal.value = 0
    searchResponseTime.value = 0
    searching.value = false
    searchSuggestions.value = []
  }
  
  // ==================== Return ====================
  
  return {
    // State
    currentQuery,
    searchResults,
    searchTotal,
    searchResponseTime,
    searching,
    searchError,
    searchHistory,
    searchSuggestions,
    searchStats,
    searchConfig,
    
    // Computed
    hasResults,
    isSearching,
    formattedResponseTime,
    historyCount,
    
    // Actions
    performSearch,
    fetchSearchSuggestions,
    fetchSearchHistory,
    fetchSearchStats,
    addToSearchHistory,
    clearSearchHistory,
    clearSearchResults,
    updateSearchConfig,
    resetSearchState
  }
}, {
  persist: {
    key: 'search-store',
    storage: localStorage,
    paths: ['searchHistory', 'searchConfig']
  }
})
