<template>
  <PageContainer title="知识库管理" subtitle="管理新闻知识库条目">
    <template #actions>
      <el-button 
        type="success" 
        :icon="Upload"
        @click="goToUpload"
        class="tech-button"
      >
        上传文件
      </el-button>
      <el-button 
        type="primary" 
        :icon="Plus"
        @click="showCreateDialog = true"
        class="tech-button"
      >
        添加知识
      </el-button>
    </template>
    
    <div class="knowledge-page">
      <!-- 统计信息 -->
      <div class="stats-section">
        <div class="stat-card tech-card">
          <div class="stat-label">知识库条目</div>
          <div class="stat-value">{{ knowledgeStore.stats.total || 0 }}</div>
        </div>
        <div class="stat-card tech-card">
          <div class="stat-label">活跃源</div>
          <div class="stat-value">{{ knowledgeStore.stats.active_sources || 0 }}</div>
        </div>
        <div class="stat-card tech-card">
          <div class="stat-label">已同步</div>
          <div class="stat-value vectorized">{{ knowledgeStore.stats.vectorized || 0 }}</div>
        </div>
        <div class="stat-card tech-card">
          <div class="stat-label">未同步</div>
          <div class="stat-value not-vectorized">{{ knowledgeStore.stats.not_vectorized || 0 }}</div>
        </div>
      </div>
      
      <!-- 搜索和筛选 -->
      <div class="search-section tech-card">
        <div class="search-form">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索知识库条目..."
            :prefix-icon="Search"
            class="search-input tech-input"
            @keyup.enter="handleSearch"
            clearable
          />
          <el-select
            v-model="filters.category"
            placeholder="选择分类"
            clearable
            class="filter-select"
          >
            <el-option label="全部" value="" />
            <el-option label="政治" value="politics" />
            <el-option label="经济" value="economy" />
            <el-option label="科技" value="technology" />
            <el-option label="社会" value="society" />
          </el-select>
          <el-select
            v-model="filters.source_type"
            placeholder="选择来源"
            clearable
            class="filter-select"
          >
            <el-option label="全部" value="" />
            <el-option label="RSS" value="rss" />
            <el-option label="网页" value="web" />
            <el-option label="上传" value="upload" />
          </el-select>
          <el-button 
            type="primary" 
            :icon="Search"
            @click="handleSearch"
            class="tech-button"
          >
            搜索
          </el-button>
        </div>
      </div>
      
      <!-- 知识库列表 -->
      <div class="knowledge-list tech-card">
        <div class="list-header">
          <div class="list-info">
            <span>共 {{ pagination.total }} 条记录</span>
            <div class="batch-actions">
              <el-tooltip 
                content="勾选后将完全清空并重建向量索引" 
                placement="top"
              >
                <el-checkbox 
                  v-model="forceRebuildVectors" 
                  class="mr-3"
                  :disabled="syncingAllVectors"
                >
                  重建向量索引
                </el-checkbox>
              </el-tooltip>
              <el-button 
                type="primary"
                :icon="Refresh"
                :loading="syncingAllVectors"
                @click="handleBatchSync"
                class="tech-button"
              >
                {{ selectedItems.length > 0 ? `批量同步向量 (${selectedItems.length})` : '同步未同步向量' }}
              </el-button>
              <el-button 
                v-if="selectedItems.length > 0"
                type="danger"
                :icon="Delete"
                @click="handleBatchDelete"
                class="tech-button"
              >
                批量删除 ({{ selectedItems.length }})
              </el-button>
            </div>
          </div>
        </div>
        
        <div v-if="knowledgeStore.loading" class="loading-container">
          <LoadingSpinner text="加载中..." />
        </div>
        
        <div v-else-if="!knowledgeStore.hasData" class="empty-container">
          <EmptyState 
            title="暂无知识库条目"
            description="点击上方'添加知识'按钮开始创建第一个条目"
            icon="Document"
          >
            <template #actions>
              <el-button 
                type="primary" 
                :icon="Plus"
                @click="showCreateDialog = true"
                class="tech-button"
              >
                添加知识
              </el-button>
            </template>
          </EmptyState>
        </div>
        
        <div v-else class="table-container">
          <el-table
            :data="knowledgeStore.knowledgeList"
            @selection-change="handleSelectionChange"
            class="tech-table"
            stripe
          >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="title" label="标题" min-width="280">
              <template #default="{ row }">
                <div class="title-cell">
                  <div class="title-wrapper">
                    <el-tooltip 
                      :content="row.vector_id != null ? '已向量化' : '未向量化'" 
                      placement="top"
                    >
                      <el-icon 
                        :class="['vector-status-icon', row.vector_id != null ? 'vectorized' : 'not-vectorized']"
                        :size="16"
                      >
                        <CircleCheck v-if="row.vector_id != null" />
                        <Warning v-else />
                      </el-icon>
                    </el-tooltip>
                    <span class="title-text" :title="row.title">{{ row.title }}</span>
                  </div>
                  <div class="title-meta">{{ row.source_name || '未知来源' }}</div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="category" label="分类" width="100">
              <template #default="{ row }">
                <el-tag :type="getCategoryType(row.category)" size="small">
                  {{ getCategoryLabel(row.category) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="source_type" label="来源类型" width="110">
              <template #default="{ row }">
                <el-tag :type="getSourceType(row.source_type)" size="small">
                  {{ getSourceTypeLabel(row.source_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="170">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="250" fixed="right">
              <template #default="{ row }">
                <div class="action-buttons">
                  <el-button 
                    type="primary" 
                    :icon="View"
                    size="small"
                    @click="handleView(row)"
                    class="action-btn"
                  >
                    查看
                  </el-button>
                  <el-button 
                    :icon="Refresh"
                    size="small"
                    @click="handleSyncVector(row)"
                    class="action-btn"
                    :type="row.vector_id != null ? 'info' : 'warning'"
                  >
                    同步
                  </el-button>
                  <el-button 
                    type="danger" 
                    :icon="Delete"
                    size="small"
                    @click="handleDelete(row)"
                    class="action-btn"
                  >
                    删除
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
          
          <!-- 分页 -->
          <div class="pagination-container">
            <el-pagination
              v-model:current-page="pagination.page"
              v-model:page-size="pagination.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="pagination.total"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="handleSizeChange"
              @current-change="handlePageChange"
              class="tech-pagination"
            />
          </div>
        </div>
      </div>
    </div>
    
    <!-- 创建对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      title="添加知识条目"
      width="600px"
      class="tech-modal"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="80px"
      >
        <el-form-item label="标题" prop="title">
          <el-input
            v-model="formData.title"
            placeholder="请输入标题"
            class="tech-input"
          />
        </el-form-item>
        
        <el-form-item label="内容" prop="content">
          <el-input
            v-model="formData.content"
            type="textarea"
            :rows="6"
            placeholder="请输入内容"
            class="tech-input"
          />
        </el-form-item>
        
        <el-form-item label="分类" prop="category">
          <el-select
            v-model="formData.category"
            placeholder="请选择分类"
            class="tech-input"
          >
            <el-option label="政治" value="politics" />
            <el-option label="经济" value="economy" />
            <el-option label="科技" value="technology" />
            <el-option label="社会" value="society" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="来源URL" prop="source_url">
          <el-input
            v-model="formData.source_url"
            placeholder="请输入来源URL"
            class="tech-input"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateDialog = false" class="tech-button">
          取消
        </el-button>
        <el-button 
          type="primary" 
          @click="handleSubmit"
          :loading="knowledgeStore.loading"
          class="tech-button"
        >
          创建
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 查看详情对话框 -->
    <el-dialog
      v-model="showViewDialog"
      title="知识条目详情"
      width="800px"
      class="tech-modal"
    >
      <div v-if="viewingItem" class="knowledge-detail">
        <div class="detail-header">
          <h3>{{ viewingItem.title }}</h3>
          <div class="detail-meta">
            <el-tag :type="getCategoryType(viewingItem.category)" size="small">
              {{ getCategoryLabel(viewingItem.category) }}
            </el-tag>
            <el-tag :type="getSourceType(viewingItem.source_type)" size="small">
              {{ getSourceTypeLabel(viewingItem.source_type) }}
            </el-tag>
            <span class="detail-time">{{ formatDate(viewingItem.created_at) }}</span>
          </div>
        </div>
        
        <div class="detail-content">
          <h4>嵌入前文本：</h4>
          <div class="content-display">
            <pre class="content-text">{{ viewingItem.content }}</pre>
          </div>
        </div>
        
        <div class="quality-metrics">
          <h4>质量评估：</h4>
          <div class="metrics-grid">
            <div class="metric-card">
              <div class="metric-label">总体评分</div>
              <div class="metric-value">
                <el-tag 
                  :type="getQualityTagType(viewingItem.quality_score)"
                  size="large"
                >
                  {{ viewingItem.quality_score || 0 }}分
                </el-tag>
              </div>
            </div>
            <div class="metric-card">
              <div class="metric-label">文本长度</div>
              <div class="metric-value">{{ viewingItem.content?.length || 0 }} 字符</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">质量等级</div>
              <div class="metric-value">
                <el-tag :type="getQualityTagType(viewingItem.quality_score)" size="small">
                  {{ getQualityLevel(viewingItem.quality_score) }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
        
        <div v-if="viewingItem.source_url" class="detail-source">
          <h4>来源：</h4>
          <a :href="viewingItem.source_url" target="_blank" class="source-link">
            {{ viewingItem.source_url }}
          </a>
        </div>
      </div>
    </el-dialog>
  </PageContainer>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useKnowledgeStore } from '@/stores/knowledge'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Plus, 
  Search, 
  Delete, 
  View, 
  Upload,
  Refresh,
  CircleCheck,
  Warning
} from '@element-plus/icons-vue'
import { formatToBeijingTime } from '@/utils/dateFormatter'
import PageContainer from '@/components/PageContainer.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import EmptyState from '@/components/EmptyState.vue'
import TextProcessor from '@/components/TextProcessor.vue'

const knowledgeStore = useKnowledgeStore()
const router = useRouter()

// 搜索和筛选
const searchKeyword = ref('')
const filters = reactive({
  category: '',
  source_type: ''
})

// 分页
const pagination = computed(() => knowledgeStore.pagination)

// 选中的项目
const selectedItems = ref([])

// 向量同步状态
const forceRebuildVectors = ref(false)
const syncingAllVectors = ref(false)

// 对话框状态
const showCreateDialog = ref(false)
const showViewDialog = ref(false)
const viewingItem = ref(null)

// 表单数据
const formData = reactive({
  title: '',
  content: '',
  category: '',
  source_url: ''
})

const formRules = {
  title: [
    { required: true, message: '请输入标题', trigger: 'blur' }
  ],
  content: [
    { required: true, message: '请输入内容', trigger: 'blur' }
  ],
  category: [
    { required: true, message: '请选择分类', trigger: 'change' }
  ]
}

const formRef = ref()

// 获取分类标签类型
const getCategoryType = (category) => {
  const types = {
    politics: 'danger',
    economy: 'warning',
    technology: 'success',
    society: 'info'
  }
  return types[category] || 'info'
}

// 获取分类标签文本
const getCategoryLabel = (category) => {
  const labels = {
    politics: '政治',
    economy: '经济',
    technology: '科技',
    society: '社会'
  }
  return labels[category] || category
}

// 获取来源类型标签
const getSourceType = (sourceType) => {
  const types = {
    rss: 'primary',
    web: 'success',
    upload: 'warning'
  }
  return types[sourceType] || 'info'
}

// 获取来源类型文本标签
const getSourceTypeLabel = (sourceType) => {
  const labels = {
    'rss': 'RSS订阅',
    'web': '网页抓取',
    'upload': '文件上传'
  }
  return labels[sourceType] || sourceType
}

// 格式化日期
const formatDate = (dateString) => {
  return formatToBeijingTime(dateString)
}

// 获取质量评分标签类型
const getQualityTagType = (score) => {
  if (score >= 80) return 'success'
  if (score >= 60) return 'primary'
  if (score >= 40) return 'warning'
  return 'danger'
}

// 获取质量等级文本
const getQualityLevel = (score) => {
  if (score >= 80) return '优秀'
  if (score >= 60) return '良好'
  if (score >= 40) return '一般'
  return '较差'
}

// 跳转到文件上传页面
const goToUpload = () => {
  router.push('/upload')
}

// 搜索
const handleSearch = () => {
  knowledgeStore.setFilters({
    category: filters.category,
    source_type: filters.source_type,
    keyword: searchKeyword.value
  })
  knowledgeStore.fetchKnowledgeList()
}

// 分页处理
const handlePageChange = (page) => {
  knowledgeStore.setPagination(page, pagination.value.pageSize)
  knowledgeStore.fetchKnowledgeList()
}

const handleSizeChange = (pageSize) => {
  knowledgeStore.setPagination(1, pageSize)
  knowledgeStore.fetchKnowledgeList()
}

// 选择处理
const handleSelectionChange = (selection) => {
  selectedItems.value = selection
}

// 查看详情
const handleView = async (item) => {
  try {
    // 获取完整的详情数据，包含markdown_content
    const fullItem = await knowledgeStore.fetchKnowledgeDetail(item.id)
    viewingItem.value = fullItem
    showViewDialog.value = true
  } catch (error) {
    console.error('获取知识条目详情失败:', error)
    ElMessage.error('获取详情失败')
  }
}

// 删除
const handleDelete = async (item) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除"${item.title}"吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await knowledgeStore.deleteKnowledgeItem(item.id)
  } catch (error) {
    // 用户取消
  }
}

// 批量删除
const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedItems.value.length} 个条目吗？`,
      '确认批量删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    const ids = selectedItems.value.map(item => item.id)
    await knowledgeStore.batchDeleteKnowledgeItems(ids)
    selectedItems.value = []
  } catch (error) {
    // 用户取消
  }
}

// 提交表单
const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    
    await knowledgeStore.createKnowledgeItem(formData)
    
    showCreateDialog.value = false
    resetForm()
  } catch (error) {
    console.error('提交失败:', error)
  }
}

// 单条目向量同步
const handleSyncVector = async (item) => {
  try {
    await ElMessageBox.confirm(
      `确定要同步"${item.title}"的向量吗？${item.vector_id != null ? '这将重新生成向量。' : ''}`,
      '确认同步',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    const forceResync = item.vector_id != null
    await knowledgeStore.syncVectorForKnowledgeItem(item.id, forceResync)
  } catch (error) {
    // 用户取消或同步失败
    if (error !== 'cancel') {
      console.error('向量同步失败:', error)
    }
  }
}

// 批量向量同步（选中条目或全量同步）
const handleBatchSync = async () => {
  try {
    // 如果勾选了"强制重建"且没有选中特定条目，执行完全重建
    if (forceRebuildVectors.value && selectedItems.value.length === 0) {
      await ElMessageBox.confirm(
        '⚠️ 警告：此操作将完全清空并重建向量索引！\n\n' +
        '• 将删除所有现有向量数据\n' +
        '• 重新为所有知识库条目生成向量\n' +
        '• 彻底解决垃圾向量问题\n' +
        '• 此过程可能需要较长时间\n\n' +
        '确定要继续吗？',
        '完全重建向量索引',
        {
          confirmButtonText: '确认重建',
          cancelButtonText: '取消',
          type: 'warning',
          dangerouslyUseHTMLString: false
        }
      )
      
      syncingAllVectors.value = true
      
      const params = {
        rebuild_index: true,  // 关键参数：触发完全重建
        only_unprocessed: false,
        force_resync: false
      }
      
      const result = await knowledgeStore.batchSyncVectorsForItems(params)
      await knowledgeStore.fetchStats()
      
      ElMessage.success({
        message: result.message || '向量索引重建完成',
        duration: 5000
      })
      
      return
    }
    
    // 如果有选中的条目，同步选中的条目
    if (selectedItems.value.length > 0) {
      const hasVectorized = selectedItems.value.some(item => item.vector_id != null)
      const allVectorized = selectedItems.value.every(item => item.vector_id != null)
      
      let confirmMessage = `确定要为选中的 ${selectedItems.value.length} 个条目同步向量吗？`
      if (forceRebuildVectors.value) {
        confirmMessage += '\n将强制重建所有选中条目的向量索引。'
      } else if (hasVectorized) {
        confirmMessage += '\n仅同步未处理的条目。'
      }
      
      await ElMessageBox.confirm(
        confirmMessage,
        '批量向量同步',
        {
          confirmButtonText: '确认同步',
          cancelButtonText: '取消',
          type: 'info'
        }
      )
      
      const ids = selectedItems.value.map(item => item.id)
      const params = {
        ids: ids,
        only_unprocessed: !forceRebuildVectors.value,
        force_resync: forceRebuildVectors.value
      }
      
      await knowledgeStore.batchSyncVectorsForItems(params)
      selectedItems.value = []
    } else {
      // 如果没有选中条目且未勾选强制重建，同步所有未同步的条目
      syncingAllVectors.value = true
      
      await ElMessageBox.confirm(
        '确定要同步所有未同步的向量吗？仅处理尚未向量化的条目。',
        '向量同步',
        {
          confirmButtonText: '确认同步',
          cancelButtonText: '取消',
          type: 'info'
        }
      )
      
      const params = {
        only_unprocessed: true,
        force_resync: false
      }
      
      const result = await knowledgeStore.batchSyncVectorsForItems(params)
      
      // 同步完成后刷新统计信息
      await knowledgeStore.fetchStats()
      
      ElMessage.success(result.message || '向量同步完成')
    }
  } catch (error) {
    // 用户取消或同步失败
    if (error !== 'cancel') {
      console.error('批量向量同步失败:', error)
    }
  } finally {
    syncingAllVectors.value = false
  }
}

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    title: '',
    content: '',
    category: '',
    source_url: ''
  })
  formRef.value?.resetFields()
}

// 初始化
onMounted(async () => {
  await knowledgeStore.fetchKnowledgeList()
  await knowledgeStore.fetchStats()
  console.log('🎯 Knowledge.vue - Stats after fetch:', knowledgeStore.stats)
  console.log('🎯 Knowledge.vue - Vectorized:', knowledgeStore.stats.vectorized)
  console.log('🎯 Knowledge.vue - Not Vectorized:', knowledgeStore.stats.not_vectorized)
})
</script>

<style scoped>
.knowledge-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

/* 统计卡片 */
.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-md);
}

.stat-card {
  padding: var(--space-lg);
  text-align: center;
}

.stat-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-bottom: var(--space-sm);
}

.stat-value {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--primary-color);
}

.stat-value.vectorized {
  color: var(--success-color);
}

.stat-value.not-vectorized {
  color: var(--warning-color);
}

/* 向量同步区域 */
.sync-section {
  padding: var(--space-lg);
}

.sync-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-md);
}

.sync-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin: 0;
}

.sync-actions {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.sync-description {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.6;
}

.search-section {
  padding: var(--space-lg);
}

.search-form {
  display: flex;
  gap: var(--space-md);
  align-items: center;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 200px;
}

.filter-select {
  width: 120px;
}

.knowledge-list {
  padding: 0;
  overflow: hidden;
}

.list-header {
  padding: var(--space-lg);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.list-info {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  width: 100%;
  justify-content: space-between;
}

.batch-actions {
  display: flex;
  gap: var(--space-md);
  align-items: center;
}

.loading-container,
.empty-container {
  padding: var(--space-3xl);
  display: flex;
  justify-content: center;
  align-items: center;
}

.table-container {
  overflow-x: auto;
}

.title-cell h4 {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.title-cell p {
  margin: var(--space-xs) 0 0 0;
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.pagination-container {
  padding: var(--space-lg);
  display: flex;
  justify-content: center;
  border-top: 1px solid var(--border-color);
}

.knowledge-detail {
  max-height: 60vh;
  overflow-y: auto;
}

.detail-header {
  margin-bottom: var(--space-lg);
  padding-bottom: var(--space-md);
  border-bottom: 1px solid var(--border-color);
}

.detail-header h3 {
  margin: 0 0 var(--space-md) 0;
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.detail-time {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.detail-content,
.detail-source {
  margin-bottom: var(--space-lg);
}

.detail-content h4,
.detail-source h4 {
  margin: 0 0 var(--space-sm) 0;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

/* 详情内容区域优化 */
.detail-content {
  margin-top: var(--space-md);
}

.detail-content h4 {
  margin: 0 0 var(--space-sm) 0;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: var(--space-xs);
}

/* 内容显示区域 */
.content-display {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  margin-top: var(--space-sm);
}

.content-text {
  margin: 0;
  padding: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: var(--text-sm);
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 400px;
  overflow-y: auto;
}

/* 质量评估区域 */
.quality-metrics {
  margin-top: var(--space-lg);
  padding-top: var(--space-md);
  border-top: 1px solid var(--border-color);
}

.quality-metrics h4 {
  margin: 0 0 var(--space-md) 0;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-md);
}

.metric-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  text-align: center;
}

.metric-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-bottom: var(--space-xs);
}

.metric-value {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

/* 详情对话框优化 */
.knowledge-detail {
  max-height: 70vh;
  overflow-y: auto;
}

.detail-header {
  margin-bottom: var(--space-lg);
  padding-bottom: var(--space-md);
  border-bottom: 1px solid var(--border-color);
}

.detail-header h3 {
  margin: 0 0 var(--space-sm) 0;
  font-size: 1.25em;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.4;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.detail-time {
  font-size: var(--text-xs);
  color: var(--text-placeholder);
}

.detail-source {
  margin-top: var(--space-lg);
  padding-top: var(--space-md);
  border-top: 1px solid var(--border-color);
}

.detail-source h4 {
  margin: 0 0 var(--space-sm) 0;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--text-primary);
}

.source-link {
  color: var(--primary-color);
  text-decoration: none;
  word-break: break-all;
  font-size: var(--text-sm);
}

.source-link:hover {
  text-decoration: underline;
}

/* 操作按钮布局优化 */
.action-buttons {
  display: flex;
  gap: 6px;
  align-items: center;
  justify-content: flex-start;
  flex-wrap: nowrap;
}

.action-btn {
  flex-shrink: 0;
  white-space: nowrap;
  min-width: 60px;
}

/* 响应式优化：在小屏幕上调整按钮布局 */
@media (max-width: 1200px) {
  .action-buttons {
    flex-direction: column;
    gap: 4px;
    align-items: stretch;
  }
  
  .action-btn {
    width: 100%;
    justify-content: center;
  }
}

/* 确保表格操作列有足够空间 */
.el-table .el-table__cell {
  padding: 6px 10px; /* 减少内边距，使表格更紧凑 */
}

/* 特别优化操作列的右边距 */
.el-table .el-table__cell:last-child {
  padding-right: 20px; /* 操作列右边距更大 */
}

.el-table .action-buttons {
  padding: 4px 0;
}

/* 标题单元格优化 */
.title-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 40px;
}

.title-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
}

.vector-status-icon {
  flex-shrink: 0;
  cursor: help;
  transition: all 0.2s ease;
}

.vector-status-icon.vectorized {
  color: #67c23a;
}

.vector-status-icon.not-vectorized {
  color: #e6a23c;
}

.vector-status-icon:hover {
  transform: scale(1.15);
}

.title-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.title-meta {
  font-size: 12px;
  color: var(--text-tertiary);
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-left: 22px; /* 对齐图标 */
}

.source-link {
  color: var(--primary-color);
  text-decoration: none;
  word-break: break-all;
}

.source-link:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .search-form {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-input,
  .filter-select {
    width: 100%;
  }
  
  .list-header {
    flex-direction: column;
    gap: var(--space-md);
    align-items: flex-start;
  }
}
</style>
