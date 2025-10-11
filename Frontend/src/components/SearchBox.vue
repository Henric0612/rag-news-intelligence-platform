<template>
  <div class="search-box">
    <el-input
      v-model="query"
      placeholder="请输入您的问题..."
      size="large"
      class="search-input"
      @keyup.enter="handleSearch"
      @input="handleInput"
      clearable
      data-testid="search-input"
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
      <template #suffix>
        <el-button
          type="primary"
          :loading="loading"
          @click="handleSearch"
          class="search-btn"
          data-testid="search-button"
        >
          搜索
        </el-button>
      </template>
    </el-input>
    
    <!-- 搜索建议 -->
    <div v-if="suggestions.length > 0 && showSuggestions" class="suggestions" data-testid="search-suggestions">
      <div
        v-for="(suggestion, index) in suggestions"
        :key="index"
        class="suggestion-item"
        @click="selectSuggestion(suggestion)"
      >
        <el-icon><Search /></el-icon>
        <span>{{ suggestion }}</span>
      </div>
    </div>
    
    <!-- 搜索历史 -->
    <div v-if="searchHistory.length > 0 && showHistory" class="search-history">
      <div class="history-header">
        <span>搜索历史</span>
        <el-button type="text" @click="clearHistory">清空</el-button>
      </div>
      <div
        v-for="(item, index) in searchHistory"
        :key="index"
        class="history-item"
        @click="selectHistory(item.query)"
      >
        <el-icon><Clock /></el-icon>
        <span>{{ item.query }}</span>
        <span class="time">{{ formatTime(item.created_at) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Clock } from '@element-plus/icons-vue'
import { getSearchSuggestions, getSearchHistory } from '@/api/search'

// 简单的防抖函数
const debounce = (func, delay) => {
  let timeoutId
  return (...args) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => func.apply(null, args), delay)
  }
}

const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['search', 'suggestion-select'])

// 响应式数据
const query = ref('')
const suggestions = ref([])
const searchHistory = ref([])
const showSuggestions = ref(false)
const showHistory = ref(false)

// 获取搜索建议
const fetchSuggestions = async (searchQuery) => {
  if (!searchQuery || typeof searchQuery !== 'string' || searchQuery.length < 2) {
    suggestions.value = []
    return
  }
  
  try {
    const response = await getSearchSuggestions(searchQuery)
    suggestions.value = response.data || []
  } catch (error) {
    console.error('获取搜索建议失败:', error)
    suggestions.value = []
  }
}

// 创建防抖版本的获取建议函数
const debouncedFetchSuggestions = debounce(fetchSuggestions, 300)

// 获取搜索历史
const fetchSearchHistory = async () => {
  try {
    const response = await getSearchHistory({ page: 1, size: 10 })
    searchHistory.value = response.data?.history || []
  } catch (error) {
    console.error('获取搜索历史失败:', error)
  }
}

// 处理输入
const handleInput = (value) => {
  // 确保value是字符串类型
  const stringValue = String(value || '')
  query.value = stringValue
  
  if (stringValue.trim()) {
    showSuggestions.value = true
    showHistory.value = false
    // 使用防抖版本
    debouncedFetchSuggestions(stringValue)
  } else {
    showSuggestions.value = false
    showHistory.value = true
    suggestions.value = []
  }
}

// 处理搜索
const handleSearch = () => {
  const trimmedQuery = query.value?.trim()
  
  if (!trimmedQuery) {
    ElMessage.warning('请输入搜索内容')
    return
  }
  
  // 输入长度验证
  if (trimmedQuery.length > 500) {
    ElMessage.warning('搜索内容不能超过500个字符')
    return
  }
  
  // 输入内容验证（防止特殊字符注入）
  if (/[<>'"]/.test(trimmedQuery)) {
    ElMessage.warning('搜索内容包含非法字符')
    return
  }
  
  emit('search', trimmedQuery)
  showSuggestions.value = false
  showHistory.value = false
}

// 选择建议
const selectSuggestion = (suggestion) => {
  query.value = suggestion
  emit('suggestion-select', suggestion)
  showSuggestions.value = false
}

// 选择历史
const selectHistory = (historyQuery) => {
  query.value = historyQuery
  emit('search', historyQuery)
  showHistory.value = false
}

// 清空历史
const clearHistory = async () => {
  try {
    // 这里可以调用清空历史的API
    searchHistory.value = []
    ElMessage.success('搜索历史已清空')
  } catch (error) {
    console.error('清空搜索历史失败:', error)
  }
}

// 格式化时间
const formatTime = (timeString) => {
  const date = new Date(timeString)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) { // 1分钟内
    return '刚刚'
  } else if (diff < 3600000) { // 1小时内
    return `${Math.floor(diff / 60000)}分钟前`
  } else if (diff < 86400000) { // 1天内
    return `${Math.floor(diff / 3600000)}小时前`
  } else {
    return date.toLocaleDateString()
  }
}

// 监听焦点事件
const handleFocus = () => {
  if (!query.value.trim()) {
    showHistory.value = true
    showSuggestions.value = false
  }
}

// 监听失焦事件
const handleBlur = () => {
  setTimeout(() => {
    showSuggestions.value = false
    showHistory.value = false
  }, 200)
}

// 组件挂载
onMounted(() => {
  fetchSearchHistory()
})

// 暴露方法给父组件
defineExpose({
  query,
  handleSearch,
  clearHistory
})
</script>

<style scoped>
.search-box {
  position: relative;
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}

.search-input {
  width: 100%;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 28px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  padding: 0 24px;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.search-input :deep(.el-input__wrapper):hover {
  box-shadow: 0 6px 20px rgba(64, 158, 255, 0.2);
  border-color: #409eff;
}

.search-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 6px 24px rgba(64, 158, 255, 0.25);
  border-color: #409eff;
}

.search-input :deep(.el-input__inner) {
  font-size: 16px;
  padding: 0 12px;
  line-height: 1.6;
}

.search-btn {
  border-radius: 24px;
  padding: 10px 28px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
  transition: all 0.3s ease;
}

.search-btn:hover {
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
  transform: translateY(-2px);
}

.search-btn:active {
  transform: translateY(0);
}

.suggestions {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  z-index: 1000;
  max-height: 350px;
  overflow-y: auto;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.suggestion-item {
  display: flex;
  align-items: center;
  padding: 14px 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
}

.suggestion-item:hover {
  background-color: #ecf5ff;
  border-left-color: #409eff;
  padding-left: 24px;
}

.suggestion-item .el-icon {
  margin-right: 12px;
  color: #909399;
  font-size: 16px;
  transition: color 0.2s ease;
}

.suggestion-item:hover .el-icon {
  color: #409eff;
}

.search-history {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  z-index: 1000;
  max-height: 350px;
  overflow-y: auto;
  animation: slideDown 0.3s ease;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 2px solid #e4e7ed;
  font-weight: 600;
  color: #303133;
  background: #f8f9fa;
  border-radius: 12px 12px 0 0;
}

.history-item {
  display: flex;
  align-items: center;
  padding: 14px 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
}

.history-item:hover {
  background-color: #ecf5ff;
  border-left-color: #409eff;
  padding-left: 24px;
}

.history-item .el-icon {
  margin-right: 12px;
  color: #909399;
  font-size: 16px;
  transition: color 0.2s ease;
}

.history-item:hover .el-icon {
  color: #409eff;
}

.history-item .time {
  margin-left: auto;
  font-size: 12px;
  color: #909399;
  padding: 2px 8px;
  background: #f5f7fa;
  border-radius: 12px;
}

.history-item:hover .time {
  background: white;
}

/* 暗色主题适配 */
.dark .search-input :deep(.el-input__wrapper) {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.dark .search-input :deep(.el-input__wrapper):hover {
  box-shadow: 0 6px 20px rgba(64, 158, 255, 0.3);
}

.dark .suggestions,
.dark .search-history {
  background: #2d2d2d;
  border-color: #4c4d4f;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

.dark .suggestion-item:hover,
.dark .history-item:hover {
  background-color: #3a3a3a;
  border-left-color: #667eea;
}

.dark .suggestion-item:hover .el-icon,
.dark .history-item:hover .el-icon {
  color: #667eea;
}

.dark .history-header {
  border-bottom-color: #4c4d4f;
  color: #e5eaf3;
  background: #1f1f1f;
}

.dark .history-item .time {
  background: #1f1f1f;
  color: #a8abb2;
}

.dark .history-item:hover .time {
  background: #2d2d2d;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .search-box {
    max-width: 100%;
  }
  
  .search-input :deep(.el-input__wrapper) {
    padding: 0 16px;
  }
  
  .search-btn {
    padding: 8px 20px;
  }
  
  .suggestions,
  .search-history {
    max-height: 250px;
  }
  
  .suggestion-item,
  .history-item {
    padding: 12px 16px;
  }
  
  .suggestion-item:hover,
  .history-item:hover {
    padding-left: 20px;
  }
}

@media (max-width: 480px) {
  .search-input :deep(.el-input__inner) {
    font-size: 14px;
  }
  
  .search-btn {
    padding: 6px 16px;
    font-size: 14px;
  }
}
</style>
