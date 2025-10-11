<template>
  <PageContainer title="仪表板" subtitle="系统概览与快速操作">
    <div class="dashboard">
      <!-- 统计卡片 -->
      <div class="stats-grid">
        <div class="stat-card tech-card">
          <div class="stat-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="stat-content">
            <h3 class="stat-value">{{ stats.totalItems || 0 }}</h3>
            <p class="stat-label">知识库条目</p>
          </div>
        </div>
        
        <div class="stat-card tech-card">
          <div class="stat-icon">
            <el-icon><Search /></el-icon>
          </div>
          <div class="stat-content">
            <h3 class="stat-value">{{ stats.totalSearches || 0 }}</h3>
            <p class="stat-label">搜索次数</p>
          </div>
        </div>
        
        <div class="stat-card tech-card">
          <div class="stat-icon">
            <el-icon><User /></el-icon>
          </div>
          <div class="stat-content">
            <h3 class="stat-value">{{ stats.activeUsers || 1 }}</h3>
            <p class="stat-label">活跃用户</p>
          </div>
        </div>
        
        <div class="stat-card tech-card">
          <div class="stat-icon">
            <el-icon><Clock /></el-icon>
          </div>
          <div class="stat-content">
            <h3 class="stat-value">{{ stats.lastUpdate || '刚刚' }}</h3>
            <p class="stat-label">最后更新</p>
          </div>
        </div>
      </div>
      
      <!-- 快速操作 -->
      <div class="quick-actions">
        <h3>快速操作</h3>
        <div class="action-buttons">
          <el-button 
            type="primary" 
            :icon="Plus"
            @click="$router.push('/knowledge')"
            class="action-btn tech-button"
          >
            添加知识
          </el-button>
          <el-button 
            :icon="Search"
            @click="$router.push('/search')"
            class="action-btn tech-button"
          >
            智能搜索
          </el-button>
          <el-button 
            :icon="TrendCharts"
            @click="$router.push('/analytics')"
            class="action-btn tech-button"
          >
            数据分析
          </el-button>
          <el-button 
            :icon="Monitor"
            @click="$router.push('/health')"
            class="action-btn tech-button"
          >
            系统监控
          </el-button>
        </div>
      </div>
      
      <!-- 最近活动 -->
      <div class="recent-activity">
        <h3>最近活动</h3>
        <div class="activity-list tech-card">
          <div v-if="recentActivities.length === 0" class="empty-activity">
            <el-icon><Document /></el-icon>
            <p>暂无最近活动</p>
          </div>
          <div v-else class="activity-item" v-for="activity in recentActivities" :key="activity.id">
            <div class="activity-icon">
              <el-icon><component :is="activity.icon" /></el-icon>
            </div>
            <div class="activity-content">
              <p class="activity-title">{{ activity.title }}</p>
              <p class="activity-time">{{ activity.time }}</p>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 系统状态 -->
      <div class="system-status">
        <div class="status-header">
          <h3>系统状态</h3>
          <el-button 
            size="small" 
            type="primary" 
            @click="checkSystemStatus"
            :loading="statusChecking"
          >
            刷新状态
          </el-button>
        </div>
        <div class="status-grid">
          <div class="status-item tech-card">
            <div class="status-indicator" :class="systemStatus.api ? 'online' : 'offline'"></div>
            <div class="status-content">
              <h4>API 服务</h4>
              <p>{{ systemStatus.api ? '正常运行' : '服务异常' }}</p>
            </div>
          </div>
          
          <div class="status-item tech-card">
            <div class="status-indicator" :class="systemStatus.database ? 'online' : 'offline'"></div>
            <div class="status-content">
              <h4>数据库</h4>
              <p>{{ systemStatus.database ? '连接正常' : '连接异常' }}</p>
            </div>
          </div>
          
          <div class="status-item tech-card">
            <div class="status-indicator" :class="systemStatus.vector ? 'online' : 'offline'"></div>
            <div class="status-content">
              <h4>向量服务</h4>
              <p>{{ systemStatus.vector ? '服务正常' : '服务异常' }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </PageContainer>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { useKnowledgeStore } from '@/stores/knowledge'
import { getHealth, getDatabaseHealth } from '@/api/health'
import { ragHealthCheck } from '@/api/rag'
import PageContainer from '@/components/PageContainer.vue'
import { 
  Document, 
  Search, 
  User, 
  Clock, 
  Plus, 
  TrendCharts, 
  Monitor 
} from '@element-plus/icons-vue'

const knowledgeStore = useKnowledgeStore()

// 统计数据
const stats = ref({
  totalItems: 0,
  totalSearches: 0,
  activeUsers: 1,
  lastUpdate: '刚刚'
})

// 最近活动
const recentActivities = ref([
  {
    id: 1,
    title: '添加了新的知识条目',
    time: '2 分钟前',
    icon: 'Document'
  },
  {
    id: 2,
    title: '执行了智能搜索',
    time: '5 分钟前',
    icon: 'Search'
  },
  {
    id: 3,
    title: '查看了数据分析',
    time: '10 分钟前',
    icon: 'TrendCharts'
  }
])

// 系统状态 - 直接使用 reactive，避免嵌套 ref
const systemStatus = reactive({
  api: true,
  database: true,
  vector: false
})

// 状态检查加载状态
const statusChecking = ref(false)

// 获取统计数据
const fetchStats = async () => {
  try {
    await knowledgeStore.fetchStats()
    stats.value = {
      totalItems: knowledgeStore.stats.total_items || 0,
      totalSearches: knowledgeStore.stats.total_searches || 0,
      activeUsers: 1,
      lastUpdate: '刚刚'
    }
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

// 检查系统状态
const checkSystemStatus = async () => {
  console.log('开始检查系统状态...')
  statusChecking.value = true
  
  try {
    // 检查 API 健康状态
    const healthResponse = await getHealth()
    console.log('API健康检查响应:', healthResponse)
    systemStatus.api = true
    console.log('API服务状态: 正常')
  } catch (error) {
    console.error('API健康检查失败:', error)
    systemStatus.api = false
    console.log('API服务状态: 异常', error)
  }
  
  try {
    // 检查数据库健康状态（使用新的快速端点）
    const databaseResponse = await getDatabaseHealth()
    console.log('数据库健康检查响应:', databaseResponse)
    systemStatus.database = true
    console.log('数据库状态: 正常')
  } catch (error) {
    console.error('数据库健康检查失败:', error)
    systemStatus.database = false
    console.log('数据库状态: 异常', error)
  }
  
  // 重置向量服务状态，确保不会因为之前的错误状态而影响
  systemStatus.vector = false
  
  try {
    // 检查向量服务健康状态（通过RAG服务）
    console.log('开始检查向量服务健康状态...')
    const ragHealth = await ragHealthCheck()
    console.log('RAG健康检查响应:', ragHealth)
    
    // 处理不同的响应格式
    let vectorStatus = null
    if (ragHealth?.vector_service) {
      // 标准格式：直接包含vector_service
      vectorStatus = ragHealth.vector_service
    } else if (ragHealth?.data?.vector_service) {
      // 嵌套格式：data.vector_service
      vectorStatus = ragHealth.data.vector_service
    } else {
      console.warn('未找到向量服务状态数据，响应格式:', ragHealth)
    }
    
    console.log('向量服务状态数据:', vectorStatus)
    
    // 简化状态判断逻辑
    if (vectorStatus?.service_healthy !== undefined) {
      console.log('使用service_healthy字段:', vectorStatus.service_healthy)
      systemStatus.vector = vectorStatus.service_healthy
    } else if (vectorStatus?.embedding_model_loaded !== undefined) {
      console.log('使用手动判断逻辑')
      systemStatus.vector = vectorStatus.embedding_model_loaded && 
                           vectorStatus.faiss_index_loaded && 
                           vectorStatus.vectorization_test === true
    } else {
      console.warn('无法获取向量服务状态，设置为false')
      systemStatus.vector = false
    }
    
    console.log('向量服务状态已设置为:', systemStatus.vector)
    
    // 记录详细状态信息用于调试
    if (vectorStatus?.status_message) {
      console.log('向量服务状态:', vectorStatus.status_message)
      console.log('服务健康:', vectorStatus.service_healthy)
      console.log('有数据:', vectorStatus.has_data)
      console.log('向量数量:', vectorStatus.total_vectors)
    }
  } catch (error) {
    console.error('向量服务健康检查失败:', error)
    systemStatus.vector = false
  } finally {
    statusChecking.value = false
    console.log('系统状态检查完成')
  }
}

onMounted(() => {
  fetchStats()
  checkSystemStatus()
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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

.stat-content h3 {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.stat-content p {
  margin: var(--space-xs) 0 0 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.quick-actions {
  background: var(--bg-color);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  border: 1px solid var(--border-color);
}

.quick-actions h3 {
  margin: 0 0 var(--space-lg) 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.action-buttons {
  display: flex;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.action-btn {
  flex: 1;
  min-width: 120px;
  height: 48px;
  font-weight: var(--font-medium);
}

.recent-activity {
  background: var(--bg-color);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  border: 1px solid var(--border-color);
}

.recent-activity h3 {
  margin: 0 0 var(--space-lg) 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.activity-list {
  padding: var(--space-lg);
}

.empty-activity {
  text-align: center;
  padding: var(--space-xl);
  color: var(--text-tertiary);
}

.empty-activity .el-icon {
  font-size: 48px;
  margin-bottom: var(--space-md);
}

.activity-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md) 0;
  border-bottom: 1px solid var(--border-light);
}

.activity-item:last-child {
  border-bottom: none;
}

.activity-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
}

.activity-content p {
  margin: 0;
}

.activity-title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.activity-time {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-top: var(--space-xs);
}

.system-status {
  background: var(--bg-color);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  border: 1px solid var(--border-color);
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-lg);
}

.system-status h3 {
  margin: 0 0 var(--space-lg) 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-md);
}

.status-item {
  padding: var(--space-md);
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.status-indicator.online {
  background: var(--success-color);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.3);
}

.status-indicator.offline {
  background: var(--error-color);
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.3);
}

.status-content h4 {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.status-content p {
  margin: var(--space-xs) 0 0 0;
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
