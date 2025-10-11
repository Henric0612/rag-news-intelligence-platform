<template>
  <PageContainer title="智能搜索" subtitle="基于AI的语义搜索与问答">
    <div class="search-page">
      <!-- 模式切换标签 - 置于顶部 -->
      <div class="mode-tabs">
        <div 
          class="mode-tab" 
          :class="{ active: searchMode === 'search' }"
          @click="switchMode('search')"
        >
          <el-icon><Search /></el-icon>
          <span>搜索模式</span>
        </div>
        <div 
          class="mode-tab" 
          :class="{ active: searchMode === 'chat' }"
          @click="switchMode('chat')"
        >
          <el-icon><ChatDotRound /></el-icon>
          <span>问答模式</span>
        </div>
      </div>
      
      <!-- 搜索模式 -->
      <div v-if="searchMode === 'search'" class="search-mode">
        <!-- 搜索框 - 仅在搜索模式显示 -->
        <div class="search-section">
          <SearchBox
            ref="searchBoxRef"
            :loading="searching"
            @search="handleSearch"
            @suggestion-select="handleSuggestionSelect"
          />
        </div>
        
        <!-- 搜索结果 -->
        <SearchResults
          :results="searchResults"
          :total="searchTotal"
          :response-time="searchResponseTime"
          :query="currentSearchQuery"
          :loading="searching"
          @result-click="handleResultClick"
          @page-change="handlePageChange"
          @size-change="handleSizeChange"
          @retry="handleRetry"
        />
      </div>
      
      <!-- 问答模式 - 完全独立 -->
      <div v-else class="chat-mode">
        <ChatInterface
          ref="chatInterfaceRef"
          @message-sent="handleMessageSent"
          @source-click="handleSourceClick"
        />
      </div>
    </div>
  </PageContainer>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, ChatDotRound } from '@element-plus/icons-vue'
import PageContainer from '@/components/PageContainer.vue'
import SearchBox from '@/components/SearchBox.vue'
import SearchResults from '@/components/SearchResults.vue'
import ChatInterface from '@/components/ChatInterface.vue'
import { searchQuery } from '@/api/search'
import { askQuestion } from '@/api/rag'

// 组件引用
const searchBoxRef = ref(null)
const chatInterfaceRef = ref(null)

// 搜索状态
const searchMode = ref('search') // 'search' | 'chat'
const searching = ref(false)
const searchResults = ref([])
const searchTotal = ref(0)
const searchResponseTime = ref(0)
const currentSearchQuery = ref('') // 搜索模式的查询

// 处理搜索
const handleSearch = async (query) => {
  if (!query.trim()) {
    ElMessage.warning('请输入搜索内容')
    return
  }
  
  currentSearchQuery.value = query
  searching.value = true
  
  try {
    const response = await searchQuery({
      query,
      top_k: 20,
      search_type: 'semantic'
    })
    
    // 拦截器已返回 data.data，这里直接使用 response
    if (response && response.results) {
      searchResults.value = response.results
      searchTotal.value = response.total
      searchResponseTime.value = response.response_time
      
      ElMessage.success(`找到 ${searchTotal.value} 条相关结果`)
    } else {
      throw new Error('搜索响应格式错误')
    }
  } catch (error) {
    console.error('搜索失败:', error)
    ElMessage.error('搜索失败，请稍后重试')
    searchResults.value = []
    searchTotal.value = 0
  } finally {
    searching.value = false
  }
}

// 处理建议选择
const handleSuggestionSelect = (suggestion) => {
  handleSearch(suggestion)
}

// 处理模式切换
const switchMode = async (mode) => {
  if (searchMode.value === mode) return
  
  searchMode.value = mode
  
  // 切换模式时不传递任何内容，保持独立
  await nextTick()
  
  // 可选：切换到问答模式时显示欢迎消息
  if (mode === 'chat' && chatInterfaceRef.value) {
    // ChatInterface 会自动显示欢迎消息
  }
}

// 处理结果点击
const handleResultClick = (result) => {
  // 可以打开详情页面或显示更多信息
  ElMessage.info(`查看详情: ${result.title}`)
}

// 处理分页变化
const handlePageChange = ({ page, size }) => {
  // 重新搜索并分页
  if (currentSearchQuery.value) {
    handleSearch(currentSearchQuery.value)
  }
}

// 处理页面大小变化
const handleSizeChange = ({ page, size }) => {
  // 重新搜索并调整页面大小
  if (currentSearchQuery.value) {
    handleSearch(currentSearchQuery.value)
  }
}

// 处理重试
const handleRetry = () => {
  if (currentSearchQuery.value) {
    handleSearch(currentSearchQuery.value)
  }
}

// 处理消息发送
const handleMessageSent = (message) => {
  console.log('消息已发送:', message)
}

// 处理来源点击
const handleSourceClick = (source) => {
  if (source.url) {
    window.open(source.url, '_blank')
  } else {
    ElMessage.info(`来源: ${source.title}`)
  }
}

onMounted(() => {
  // 初始化
})
</script>

<style scoped>
.search-page {
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* 模式切换标签 - 参考 Google/Perplexity 设计 */
.mode-tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid #e4e7ed;
  margin-bottom: 32px;
  background: white;
  border-radius: 8px 8px 0 0;
  overflow: hidden;
}

.mode-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 15px;
  font-weight: 500;
  color: #606266;
  background: #f5f7fa;
  border-bottom: 3px solid transparent;
  position: relative;
}

.mode-tab:hover {
  background: #ecf5ff;
  color: #409eff;
}

.mode-tab.active {
  background: white;
  color: #409eff;
  border-bottom-color: #409eff;
}

.mode-tab .el-icon {
  font-size: 18px;
}

/* 搜索模式 */
.search-mode {
  display: flex;
  flex-direction: column;
  gap: 24px;
  animation: fadeIn 0.3s ease;
}

.search-section {
  margin-bottom: 8px;
}

/* 问答模式 */
.chat-mode {
  min-height: 600px;
  background: white;
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  overflow: hidden;
  animation: fadeIn 0.3s ease;
}

/* 淡入动画 */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 暗色主题适配 */
.dark .mode-tabs {
  background: #2d2d2d;
  border-bottom-color: #4c4d4f;
}

.dark .mode-tab {
  background: #1f1f1f;
  color: #a8abb2;
}

.dark .mode-tab:hover {
  background: #3a3a3a;
  color: #409eff;
}

.dark .mode-tab.active {
  background: #2d2d2d;
  color: #409eff;
}

.dark .chat-mode {
  background: #2d2d2d;
  border-color: #4c4d4f;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .mode-tabs {
    margin-bottom: 20px;
  }
  
  .mode-tab {
    padding: 12px 16px;
    font-size: 14px;
  }
  
  .mode-tab .el-icon {
    font-size: 16px;
  }
  
  .search-mode {
    gap: 16px;
  }
  
  .chat-mode {
    min-height: 500px;
  }
}

@media (max-width: 480px) {
  .mode-tab span {
    display: none;
  }
  
  .mode-tab {
    padding: 12px;
  }
  
  .mode-tab .el-icon {
    font-size: 20px;
  }
}
</style>
