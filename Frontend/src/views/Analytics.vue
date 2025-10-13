<template>
  <PageContainer title="数据分析" subtitle="知识库统计与用户行为分析">
    <div class="analytics-page">
      <!-- 统计概览 -->
      <div class="stats-overview">
        <div class="stat-card tech-card">
          <div class="stat-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stat-content">
            <h3 class="stat-value">{{ stats.totalItems || 0 }}</h3>
            <p class="stat-label">总条目数</p>
            <div class="stat-trend positive">
              <el-icon><TrendCharts /></el-icon>
              <span>+12.5%</span>
            </div>
          </div>
        </div>
        
        <div class="stat-card tech-card">
          <div class="stat-icon">
            <el-icon><Search /></el-icon>
          </div>
          <div class="stat-content">
            <h3 class="stat-value">{{ stats.totalSearches || 0 }}</h3>
            <p class="stat-label">搜索次数</p>
            <div class="stat-trend positive">
              <el-icon><TrendCharts /></el-icon>
              <span>+8.3%</span>
            </div>
          </div>
        </div>
        
        <div class="stat-card tech-card">
          <div class="stat-icon">
            <el-icon><User /></el-icon>
          </div>
          <div class="stat-content">
            <h3 class="stat-value">{{ stats.activeUsers || 1 }}</h3>
            <p class="stat-label">活跃用户</p>
            <div class="stat-trend positive">
              <el-icon><TrendCharts /></el-icon>
              <span>+5.2%</span>
            </div>
          </div>
        </div>
        
        <div class="stat-card tech-card">
          <div class="stat-icon">
            <el-icon><Clock /></el-icon>
          </div>
          <div class="stat-content">
            <h3 class="stat-value">{{ stats.avgResponseTime || 0 }}ms</h3>
            <p class="stat-label">平均响应时间</p>
            <div class="stat-trend negative">
              <el-icon><TrendCharts /></el-icon>
              <span>-15.2%</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 搜索热词TOP10 -->
      <div class="charts-section">
        <div class="chart-container tech-card">
          <div class="chart-header">
            <h3>搜索热词TOP10</h3>
            <p class="chart-subtitle">基于知识库内容的关键词分析</p>
            <el-button size="small" :icon="Refresh" @click="refreshHotWords">
              刷新
            </el-button>
          </div>
          <div class="hot-words-list">
            <div 
              v-if="hotWords.length === 0 || (hotWords.length === 1 && (hotWords[0].text === '暂无数据' || hotWords[0].text === '加载失败'))"
              class="empty-keywords"
            >
              <el-icon><Document /></el-icon>
              <p>{{ hotWords[0]?.text || '暂无关键词数据' }}</p>
            </div>
            <div 
              v-else
              v-for="(word, index) in hotWords" 
              :key="index"
              class="keyword-item"
              :class="{ 'top-three': index < 3 }"
            >
              <div class="keyword-rank">{{ index + 1 }}</div>
              <div class="keyword-content">
                <div class="keyword-text">{{ word.text }}</div>
                <div class="keyword-bar">
                  <div 
                    class="keyword-progress" 
                    :style="{ width: `${word.percentage}%` }"
                  ></div>
                </div>
              </div>
              <div class="keyword-stats">
                <span class="keyword-count">{{ word.count }}</span>
                <span class="keyword-percentage">{{ word.percentage }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 分类统计 -->
      <div class="category-stats tech-card">
        <h3>分类统计</h3>
        <div class="category-list">
          <div 
            v-for="category in categoryStats" 
            :key="category.name"
            class="category-item"
          >
            <div class="category-info">
              <span class="category-name">{{ category.name }}</span>
              <span class="category-count">{{ category.count }} 条</span>
            </div>
            <div class="category-bar">
              <div 
                class="category-progress" 
                :style="{ width: `${category.percentage}%` }"
              ></div>
            </div>
            <span class="category-percentage">{{ category.percentage }}%</span>
          </div>
        </div>
      </div>
      
      <!-- 用户行为分析 -->
      <div class="behavior-analysis tech-card">
        <h3>用户行为分析</h3>
        <div class="behavior-grid">
          <div class="behavior-item">
            <div class="behavior-icon">
              <el-icon><View /></el-icon>
            </div>
            <div class="behavior-content">
              <h4>页面访问</h4>
              <p>知识库页面访问量最高</p>
              <span class="behavior-value">1,234 次</span>
            </div>
          </div>
          
          <div class="behavior-item">
            <div class="behavior-icon">
              <el-icon><Search /></el-icon>
            </div>
            <div class="behavior-content">
              <h4>搜索行为</h4>
              <p>平均每次搜索查看 3.2 个结果</p>
              <span class="behavior-value">3.2 个</span>
            </div>
          </div>
          
          <div class="behavior-item">
            <div class="behavior-icon">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="behavior-content">
              <h4>停留时间</h4>
              <p>平均页面停留时间</p>
              <span class="behavior-value">2分30秒</span>
            </div>
          </div>
          
          <div class="behavior-item">
            <div class="behavior-icon">
              <el-icon><Star /></el-icon>
            </div>
            <div class="behavior-content">
              <h4>收藏行为</h4>
              <p>用户收藏的内容类型分布</p>
              <span class="behavior-value">15% 收藏率</span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 系统性能 -->
      <div class="performance-metrics tech-card">
        <h3>系统性能指标</h3>
        <div class="metrics-grid">
          <div class="metric-item">
            <div class="metric-label">API 响应时间</div>
            <div class="metric-value">245ms</div>
            <div class="metric-status good">良好</div>
          </div>
          
          <div class="metric-item">
            <div class="metric-label">数据库查询时间</div>
            <div class="metric-value">89ms</div>
            <div class="metric-status good">良好</div>
          </div>
          
          <div class="metric-item">
            <div class="metric-label">向量检索时间</div>
            <div class="metric-value">156ms</div>
            <div class="metric-status warning">一般</div>
          </div>
          
          <div class="metric-item">
            <div class="metric-label">内存使用率</div>
            <div class="metric-value">68%</div>
            <div class="metric-status good">良好</div>
          </div>
          
          <div class="metric-item">
            <div class="metric-label">CPU 使用率</div>
            <div class="metric-value">45%</div>
            <div class="metric-status good">良好</div>
          </div>
          
          <div class="metric-item">
            <div class="metric-label">磁盘使用率</div>
            <div class="metric-value">32%</div>
            <div class="metric-status good">良好</div>
          </div>
        </div>
      </div>
    </div>
  </PageContainer>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { 
  Document, 
  Search, 
  User, 
  Clock, 
  TrendCharts, 
  Refresh, 
  View, 
  Star 
} from '@element-plus/icons-vue'
import { ElMessage, ElLoading } from 'element-plus'
import PageContainer from '@/components/PageContainer.vue'
import { getClusteringAnalysis, getStatistics } from '@/api/analytics'

// 统计数据
const stats = reactive({
  totalItems: 0,
  totalSearches: 0,
  activeUsers: 1,
  avgResponseTime: 245
})

// 热词数据（Top10关键词）
const hotWords = ref([])

// 分类统计
const categoryStats = ref([])

// 加载状态
const loading = ref(false)

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

// 加载聚类分析数据
const loadClusteringData = async () => {
  try {
    loading.value = true
    
    // 友好提示：首次加载可能较慢
    const loadingMessage = ElMessage.info({
      message: '正在分析知识库数据，首次加载约需1分钟...',
      duration: 0,  // 不自动关闭
      showClose: false
    })
    
    const response = await getClusteringAnalysis()
    
    // 关闭加载提示
    loadingMessage.close()
    
    console.log('聚类分析API响应:', response)
    
    // ✅ 响应拦截器返回的是data.data，直接使用response
    // 检查是否有数据（响应拦截器已经处理了success判断）
    if (response && typeof response === 'object') {
      // 更新Top10关键词
      if (response.top_10_keywords && response.top_10_keywords.length > 0) {
        // 将关键词转换为热词显示格式，根据count排序设置字体大小
        hotWords.value = response.top_10_keywords.map((item, index) => ({
          text: item.keyword,
          count: item.count,
          percentage: item.percentage,
          size: 24 - (index * 1.5) // 从大到小递减
        }))
        
        console.log('Top10关键词:', hotWords.value)
      } else {
        // 如果没有数据，显示默认消息
        hotWords.value = [{ text: '暂无数据', size: 16 }]
      }
      
      // 更新统计数据
      stats.totalItems = response.total_items || 0
      
      // 更新分类统计
      if (response.category_distribution && response.category_distribution.length > 0) {
        categoryStats.value = response.category_distribution.map(cat => ({
          name: getCategoryLabel(cat.category) || '未分类',
          count: cat.count || 0,
          percentage: cat.percentage || 0
        }))
      }
      
      ElMessage.success('数据加载成功')
    } else {
      ElMessage.warning('获取分析数据失败：响应格式错误')
      hotWords.value = [{ text: '暂无数据', size: 16 }]
    }
  } catch (error) {
    // 额外容错：如果是超时，提示用户稍后重试
    console.error('加载聚类分析数据失败:', error)
    if (error.code === 'ECONNABORTED' || /timeout/i.test(error.message || '')) {
      ElMessage.error({
        message: '数据生成较慢已超时，请稍后点击"刷新"重试',
        duration: 5000
      })
    } else {
      ElMessage.error('加载数据失败: ' + (error.response?.data?.message || error.message))
    }
    
    // 显示默认数据
    hotWords.value = [{ text: '加载失败', size: 16 }]
  } finally {
    loading.value = false
  }
}

// 刷新热词
const refreshHotWords = async () => {
  const loadingInstance = ElLoading.service({
    lock: true,
    text: '正在生成关键词分析，请稍候...',
    background: 'rgba(0, 0, 0, 0.7)',
    customClass: 'analytics-loading'
  })
  
  try {
    await loadClusteringData()
  } finally {
    loadingInstance.close()
  }
}

// 初始化数据
onMounted(async () => {
  await loadClusteringData()
})
</script>

<style scoped>
.analytics-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
}

.stats-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-lg);
}

.stat-card {
  padding: var(--space-lg);
  display: flex;
  align-items: center;
  gap: var(--space-md);
  transition: transform var(--transition-fast);
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  background: var(--primary-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
  font-size: 24px;
}

.stat-content {
  flex: 1;
}

.stat-content h3 {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.stat-content p {
  margin: var(--space-xs) 0 var(--space-sm) 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.stat-trend.positive {
  color: var(--success-color);
}

.stat-trend.negative {
  color: var(--error-color);
}

.charts-section {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-lg);
}

.chart-container {
  padding: var(--space-lg);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-lg);
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.chart-header h3 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.chart-subtitle {
  flex: 1;
  margin: 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  padding-left: var(--space-md);
}

.hot-words-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  min-height: 200px;
}

.empty-keywords {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  color: var(--text-tertiary);
}

.empty-keywords .el-icon {
  font-size: 48px;
  margin-bottom: var(--space-md);
}

.keyword-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  border-left: 3px solid transparent;
}

.keyword-item:hover {
  background: var(--bg-tertiary);
  transform: translateX(4px);
}

.keyword-item.top-three {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(147, 51, 234, 0.1));
  border-left-color: var(--primary-color);
}

.keyword-item.top-three:nth-child(1) {
  border-left-color: #FFD700;
}

.keyword-item.top-three:nth-child(2) {
  border-left-color: #C0C0C0;
}

.keyword-item.top-three:nth-child(3) {
  border-left-color: #CD7F32;
}

.keyword-rank {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-color);
  color: var(--white);
  border-radius: var(--radius-full);
  font-weight: var(--font-bold);
  font-size: var(--text-sm);
  flex-shrink: 0;
}

.keyword-item.top-three:nth-child(1) .keyword-rank {
  background: linear-gradient(135deg, #FFD700, #FFA500);
}

.keyword-item.top-three:nth-child(2) .keyword-rank {
  background: linear-gradient(135deg, #C0C0C0, #A8A8A8);
}

.keyword-item.top-three:nth-child(3) .keyword-rank {
  background: linear-gradient(135deg, #CD7F32, #B8860B);
}

.keyword-content {
  flex: 1;
  min-width: 0;
}

.keyword-text {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-xs);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.keyword-bar {
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.keyword-progress {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--primary-light));
  border-radius: var(--radius-full);
  transition: width var(--transition-slow);
}

.keyword-item.top-three .keyword-progress {
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
}

.keyword-stats {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-xs);
  flex-shrink: 0;
}

.keyword-count {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--primary-color);
}

.keyword-percentage {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-weight: var(--font-medium);
}

.category-stats {
  padding: var(--space-lg);
}

.category-stats h3 {
  margin: 0 0 var(--space-lg) 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.category-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.category-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-width: 120px;
}

.category-name {
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.category-count {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.category-bar {
  flex: 1;
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.category-progress {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--primary-light));
  border-radius: var(--radius-full);
  transition: width var(--transition-slow);
}

.category-percentage {
  min-width: 40px;
  text-align: right;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
}

.behavior-analysis {
  padding: var(--space-lg);
}

.behavior-analysis h3 {
  margin: 0 0 var(--space-lg) 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.behavior-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-lg);
}

.behavior-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.behavior-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: var(--primary-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
  font-size: 20px;
}

.behavior-content h4 {
  margin: 0 0 var(--space-xs) 0;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.behavior-content p {
  margin: 0 0 var(--space-xs) 0;
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.behavior-value {
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  color: var(--primary-color);
}

.performance-metrics {
  padding: var(--space-lg);
}

.performance-metrics h3 {
  margin: 0 0 var(--space-lg) 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-md);
}

.metric-item {
  padding: var(--space-md);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  text-align: center;
}

.metric-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-bottom: var(--space-xs);
}

.metric-value {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin-bottom: var(--space-xs);
}

.metric-status {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
}

.metric-status.good {
  background: rgba(16, 185, 129, 0.1);
  color: var(--success-color);
}

.metric-status.warning {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning-color);
}

.metric-status.error {
  background: rgba(239, 68, 68, 0.1);
  color: var(--error-color);
}

@media (max-width: 768px) {
  .behavior-grid {
    grid-template-columns: 1fr;
  }
  
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .chart-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .chart-subtitle {
    padding-left: 0;
  }
  
  .keyword-item {
    flex-wrap: wrap;
  }
  
  .keyword-stats {
    flex-direction: row;
    gap: var(--space-sm);
  }
}
</style>
