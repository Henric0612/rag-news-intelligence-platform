<template>
  <div class="search-results">
    <!-- 搜索结果统计 -->
    <div v-if="results.length > 0" class="results-stats">
      <span>找到 {{ total }} 个结果</span>
      <span v-if="responseTime">（用时 {{ responseTime }}ms）</span>
    </div>
    
    <!-- 搜索结果列表 -->
    <div v-if="results.length > 0" class="results-list" data-testid="search-results">
      <div
        v-for="(result, index) in results"
        :key="result.id"
        class="result-item"
        @click="handleResultClick(result)"
      >
        <div class="result-header">
          <h3 class="result-title" v-html="highlightTitle(result.title, query)"></h3>
          <div class="result-meta">
            <el-tag v-if="result.category" size="small" type="info">
              {{ getCategoryLabel(result.category) }}
            </el-tag>
            <el-tag v-if="result.source_type" size="small" type="success">
              {{ getSourceTypeLabel(result.source_type) }}
            </el-tag>
            <span class="similarity-score" v-if="result.similarity_score">
              相关度: {{ (result.similarity_score * 100).toFixed(1) }}%
            </span>
          </div>
        </div>
        
        <div class="result-content" v-html="highlightContent(result.content, query)"></div>
        
        <div class="result-footer">
          <div class="result-source">
            <el-icon><Link /></el-icon>
            <a
              v-if="result.source_url"
              :href="result.source_url"
              target="_blank"
              @click.stop
              class="source-link"
            >
              {{ result.source_url }}
            </a>
            <span v-else class="no-source">无来源链接</span>
          </div>
          <div class="result-time">
            <el-icon><Clock /></el-icon>
            <span>{{ formatTime(result.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 空状态 - 只在有查询时显示 -->
    <div v-else-if="!loading && query" class="empty-state">
      <el-empty description="暂无搜索结果">
        <template #image>
          <el-icon size="64" color="#c0c4cc"><Search /></el-icon>
        </template>
        <el-button type="primary" @click="$emit('retry')">重新搜索</el-button>
      </el-empty>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="3" animated />
      <el-skeleton :rows="3" animated />
      <el-skeleton :rows="3" animated />
    </div>
    
    <!-- 分页 -->
    <div v-if="total > pageSize" class="pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Link, Clock } from '@element-plus/icons-vue'

const props = defineProps({
  results: {
    type: Array,
    default: () => []
  },
  total: {
    type: Number,
    default: 0
  },
  responseTime: {
    type: Number,
    default: 0
  },
  query: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['result-click', 'page-change', 'size-change', 'retry'])

// 响应式数据
const currentPage = ref(1)
const pageSize = ref(20)

// 处理结果点击
const handleResultClick = (result) => {
  emit('result-click', result)
}

// 处理分页大小变化
const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  emit('size-change', { page: currentPage.value, size })
}

// 处理当前页变化
const handleCurrentChange = (page) => {
  currentPage.value = page
  emit('page-change', { page, size: pageSize.value })
}

// 高亮标题
const highlightTitle = (title, query) => {
  if (!query || !title) return title
  
  const regex = new RegExp(`(${query})`, 'gi')
  return title.replace(regex, '<mark>$1</mark>')
}

// 高亮内容
const highlightContent = (content, query) => {
  if (!query || !content) return content
  
  const regex = new RegExp(`(${query})`, 'gi')
  return content.replace(regex, '<mark>$1</mark>')
}

// 获取分类标签
const getCategoryLabel = (category) => {
  const labels = {
    'politics': '政治',
    'economy': '经济',
    'technology': '科技',
    'society': '社会'
  }
  return labels[category] || category
}

// 获取来源类型标签
const getSourceTypeLabel = (sourceType) => {
  const labels = {
    'rss': 'RSS订阅',
    'web': '网页抓取',
    'upload': '文件上传'
  }
  return labels[sourceType] || sourceType
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
  } else if (diff < 604800000) { // 1周内
    return `${Math.floor(diff / 86400000)}天前`
  } else {
    return date.toLocaleDateString()
  }
}

// 监听结果变化，重置分页
watch(() => props.results, () => {
  currentPage.value = 1
})
</script>

<style scoped>
.search-results {
  width: 100%;
}

.results-stats {
  margin-bottom: 16px;
  color: #606266;
  font-size: 14px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-item {
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.result-item:hover {
  border-color: #409eff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.1);
  transform: translateY(-2px);
}

.result-header {
  margin-bottom: 12px;
}

.result-title {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  line-height: 1.4;
}

.result-title :deep(mark) {
  background-color: #fff2cc;
  color: #d48806;
  padding: 2px 4px;
  border-radius: 3px;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.similarity-score {
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
}

.result-content {
  margin-bottom: 16px;
  color: #606266;
  line-height: 1.6;
  max-height: 120px;
  overflow: hidden;
  position: relative;
}

.result-content :deep(mark) {
  background-color: #fff2cc;
  color: #d48806;
  padding: 2px 4px;
  border-radius: 3px;
}

.result-content::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 20px;
  background: linear-gradient(transparent, white);
}

.result-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #909399;
}

.result-source,
.result-time {
  display: flex;
  align-items: center;
  gap: 4px;
}

.source-link {
  color: #409eff;
  text-decoration: none;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-link:hover {
  text-decoration: underline;
}

.no-source {
  color: #c0c4cc;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pagination {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

/* 暗色主题适配 */
.dark .result-item {
  background: #2d2d2d;
  border-color: #4c4d4f;
}

.dark .result-item:hover {
  border-color: #409eff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.dark .result-title {
  color: #e5eaf3;
}

.dark .result-content {
  color: #c0c4cc;
}

.dark .result-content::after {
  background: linear-gradient(transparent, #2d2d2d);
}

.dark .similarity-score {
  background: #3a3a3a;
  color: #a8abb2;
}

.dark .results-stats {
  color: #a8abb2;
}
</style>
