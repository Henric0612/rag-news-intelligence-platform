<template>
  <div class="crawler-page">
    <PageContainer title="数据采集管理">
      <!-- RSS源管理 -->
      <el-card class="mb-4" shadow="hover">
        <template #header>
          <div class="flex justify-between items-center">
            <h3 class="text-lg font-semibold">RSS源管理</h3>
            <el-button type="primary" @click="showAddRssDialog = true">
              <el-icon><Plus /></el-icon>
              添加RSS源
            </el-button>
          </div>
        </template>

        <!-- RSS源列表 -->
        <el-table
          :data="rssSources"
          v-loading="loadingRssSources"
          stripe
          style="width: 100%"
        >
            <el-table-column prop="name" label="源名称" width="200" />
            <el-table-column prop="url" label="URL" show-overflow-tooltip />
            <el-table-column label="分类" width="120">
              <template #default="{ row }">
                <el-tag :type="getCategoryType(row.category)" size="small">
                  {{ getCategoryLabel(row.category) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'">
                {{ row.is_active ? '活跃' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="crawl_frequency" label="更新频率" width="120">
            <template #default="{ row }">
              {{ formatFrequency(row.crawl_frequency) }}
            </template>
          </el-table-column>
          <el-table-column prop="last_crawled" label="最后更新" width="180">
            <template #default="{ row }">
              {{ formatDate(row.last_crawled) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="editRssSource(row)">编辑</el-button>
              <el-button size="small" type="success" @click="crawlRssSource(row.id)">
                更新
              </el-button>
              <el-button size="small" type="danger" @click="deleteRssSource(row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="mt-4 flex justify-center">
          <el-pagination
            v-model:current-page="rssPagination.page"
            v-model:page-size="rssPagination.per_page"
            :page-sizes="[10, 20, 50, 100]"
            :total="rssPagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="loadRssSources"
            @current-change="loadRssSources"
          />
        </div>
      </el-card>

      <!-- 网页抓取 -->
      <el-card class="mb-4" shadow="hover">
        <template #header>
          <h3 class="text-lg font-semibold">网页抓取</h3>
        </template>

        <el-form :model="webCrawlForm" @submit.prevent="crawlWebpage">
          <el-row :gutter="20">
            <el-col :span="16">
              <el-form-item label="网页URL">
                <el-input
                  v-model="webCrawlForm.url"
                  placeholder="请输入要抓取的网页URL"
                  type="url"
                />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item label="分类">
                <el-select v-model="webCrawlForm.category" placeholder="请选择分类">
                  <el-option label="政治" value="politics" />
                  <el-option label="经济" value="economy" />
                  <el-option label="科技" value="technology" />
                  <el-option label="社会" value="society" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="2">
              <el-form-item>
                <el-button
                  type="primary"
                  @click="crawlWebpage"
                  :loading="crawlingWebpage"
                >
                  抓取
                </el-button>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </el-card>

      <!-- 任务监控 -->
      <el-card class="mb-4" shadow="hover">
        <template #header>
          <div class="flex justify-between items-center">
            <h3 class="text-lg font-semibold">任务监控</h3>
            <div class="flex gap-2">
              <el-button @click="loadCrawlTasks">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
              <el-button type="danger" @click="clearAllTasks" :loading="clearingTasks">
                <el-icon><Delete /></el-icon>
                清空记录
              </el-button>
            </div>
          </div>
        </template>

        <el-table
          :data="crawlTasks"
          v-loading="loadingCrawlTasks"
          stripe
          style="width: 100%"
        >
          <el-table-column prop="id" label="任务ID" width="80" />
          <el-table-column prop="source_name" label="源名称" width="150" />
          <el-table-column prop="task_type" label="类型" width="100">
            <template #default="{ row }">
              <el-tag :type="row.task_type === 'rss' ? 'primary' : 'success'">
                {{ row.task_type === 'rss' ? 'RSS' : '网页' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="items_crawled" label="更新数量" width="100" />
          <el-table-column prop="started_at" label="开始时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.started_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="completed_at" label="完成时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.completed_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="error_message" label="错误信息" show-overflow-tooltip />
        </el-table>

        <!-- 分页 -->
        <div class="flex justify-center mt-4">
          <el-pagination
            v-model:current-page="taskPagination.page"
            v-model:page-size="taskPagination.per_page"
            :page-sizes="[5, 10, 20, 50]"
            :total="taskPagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="loadCrawlTasks"
            @current-change="loadCrawlTasks"
          />
        </div>
      </el-card>

      <!-- 调度与数据质量 -->
      <el-card class="mb-4" shadow="hover">
        <template #header>
          <h3 class="text-lg font-semibold">调度与数据质量</h3>
        </template>
        <div class="flex items-center" style="gap:12px; flex-wrap: wrap;">
          <el-button :loading="scheduling" @click="scheduleCrawling">执行定时爬取</el-button>
          <el-select v-model="qualityType" placeholder="选择数据类型" style="width:160px;">
            <el-option label="全部" value="all" />
            <el-option label="RSS" value="rss" />
            <el-option label="网页" value="web" />
            <el-option label="上传" value="upload" />
          </el-select>
          <el-button :loading="checkingQuality" @click="checkDataQualityAction">检查数据质量</el-button>
        </div>
        <div v-if="qualityResult" class="mt-4">
          <el-alert type="success" :title="`质量分数: ${qualityResult.quality_score ?? 0}`" show-icon />
        </div>
      </el-card>
    </PageContainer>

    <!-- 添加/编辑RSS源对话框 -->
    <el-dialog
      v-model="showAddRssDialog"
      :title="editingRssSource ? '编辑RSS源' : '添加RSS源'"
      width="600px"
      @close="resetRssForm"
    >
      <el-form
        :model="rssForm"
        :rules="rssFormRules"
        ref="rssFormRef"
        label-width="100px"
      >
        <el-form-item label="源名称" prop="name">
          <el-input v-model="rssForm.name" placeholder="请输入RSS源名称" />
        </el-form-item>
        <el-form-item label="RSS URL" prop="url">
          <el-input v-model="rssForm.url" placeholder="请输入RSS订阅URL" type="url" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="rssForm.category" placeholder="请选择分类">
            <el-option label="政治" value="politics" />
            <el-option label="经济" value="economy" />
            <el-option label="科技" value="technology" />
            <el-option label="社会" value="society" />
          </el-select>
        </el-form-item>
        <el-form-item label="更新频率" prop="crawl_frequency">
          <el-select v-model="rssForm.crawl_frequency" placeholder="选择更新频率">
            <el-option label="每15分钟" :value="900" />
            <el-option label="每1小时" :value="3600" />
            <el-option label="每12小时" :value="43200" />
            <el-option label="每天" :value="86400" />
            <el-option label="每周" :value="604800" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="is_active">
          <el-switch v-model="rssForm.is_active" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeRssDialog">取消</el-button>
        <el-button type="primary" @click="saveRssSource" :loading="savingRssSource">
          {{ editingRssSource ? '更新' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Delete } from '@element-plus/icons-vue'
import PageContainer from '@/components/PageContainer.vue'
import { crawlerAPI } from '@/api/crawler'
import { formatToBeijingTime } from '@/utils/dateFormatter'

// 响应式数据
const loadingRssSources = ref(false)
const loadingCrawlTasks = ref(false)
const crawlingWebpage = ref(false)
const savingRssSource = ref(false)
const scheduling = ref(false)
const checkingQuality = ref(false)
const qualityType = ref('all')
const qualityResult = ref(null)
const clearingTasks = ref(false)

const showAddRssDialog = ref(false)
const editingRssSource = ref(null)

const rssSources = ref([])
const crawlTasks = ref([])

// 分页数据
const rssPagination = reactive({
  page: 1,
  per_page: 20,
  total: 0
})

const taskPagination = reactive({
  page: 1,
  per_page: 5,  // 默认显示5条
  total: 0
})

// 表单数据
const webCrawlForm = reactive({
  url: '',
  category: ''
})

const rssForm = reactive({
  name: '',
  url: '',
  category: '',
  crawl_frequency: 3600,
  is_active: true
})

// 表单验证规则
const rssFormRules = {
  name: [
    { required: true, message: '请输入源名称', trigger: 'blur' }
  ],
  url: [
    { required: true, message: '请输入RSS URL', trigger: 'blur' },
    { type: 'url', message: '请输入有效的URL', trigger: 'blur' }
  ]
}

const rssFormRef = ref()

// 方法
const loadRssSources = async () => {
  try {
    loadingRssSources.value = true
    const response = await crawlerAPI.getRssSources({
      page: rssPagination.page,
      per_page: rssPagination.per_page
    })
    // 拦截器已返回 data.data，这里直接使用响应负载
    rssSources.value = response.sources || []
    rssPagination.total = response.pagination?.total || 0
  } catch (error) {
    console.error('加载RSS源失败:', error)
    ElMessage.error('加载RSS源失败')
  } finally {
    loadingRssSources.value = false
  }
}

const loadCrawlTasks = async () => {
  try {
    loadingCrawlTasks.value = true
    const response = await crawlerAPI.getCrawlTasks({
      page: taskPagination.page,
      per_page: taskPagination.per_page
    })
    crawlTasks.value = response.tasks || []
    taskPagination.total = response.pagination?.total || 0
  } catch (error) {
    console.error('加载爬取任务失败:', error)
    ElMessage.error('加载爬取任务失败')
  } finally {
    loadingCrawlTasks.value = false
  }
}

const scheduleCrawling = async () => {
  try {
    scheduling.value = true
    await crawlerAPI.scheduleCrawling()
    ElMessage.success('定时爬取任务已执行')
    loadCrawlTasks()
  } catch (error) {
    console.error('执行定时爬取失败:', error)
    ElMessage.error('执行定时爬取失败')
  } finally {
    scheduling.value = false
  }
}

const checkDataQualityAction = async () => {
  try {
    checkingQuality.value = true
    const res = await crawlerAPI.checkDataQuality({ data_type: qualityType.value })
    if (res && res.success !== false) {
      qualityResult.value = res
      ElMessage.success('数据质量检查完成')
    } else {
      ElMessage.error(res?.error || '数据质量检查失败')
    }
  } catch (error) {
    console.error('数据质量检查失败:', error)
    ElMessage.error('数据质量检查失败')
  } finally {
    checkingQuality.value = false
  }
}

// 清空所有任务记录
const clearAllTasks = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有任务监控记录吗？此操作不可恢复！',
      '确认清空',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    clearingTasks.value = true
    await crawlerAPI.clearAllTasks()
    ElMessage.success('所有任务记录已清空')
    loadCrawlTasks() // 刷新任务列表
  } catch (error) {
    if (error !== 'cancel') {
      console.error('清空任务记录失败:', error)
      ElMessage.error('清空任务记录失败')
    }
  } finally {
    clearingTasks.value = false
  }
}

const editRssSource = (source) => {
  editingRssSource.value = source
  rssForm.name = source.name
  rssForm.url = source.url
  rssForm.category = source.category || ''
  rssForm.crawl_frequency = source.crawl_frequency
  rssForm.is_active = source.is_active
  showAddRssDialog.value = true
}

const saveRssSource = async () => {
  try {
    await rssFormRef.value.validate()
    savingRssSource.value = true
    
    if (editingRssSource.value) {
      // 编辑模式：只更新RSS源
      await crawlerAPI.updateRssSource(editingRssSource.value.id, rssForm)
      ElMessage.success('RSS源更新成功')
    } else {
      // 新增模式：创建RSS源后自动触发第一次抓取
      const response = await crawlerAPI.createRssSource(rssForm)
      ElMessage.success('RSS源添加成功，正在开始第一次抓取...')
      
      // 自动触发第一次抓取
      if (response && response.source && response.source.id) {
        try {
          await crawlerAPI.crawlRssSource(response.source.id)
          ElMessage.success('RSS源添加成功，第一次抓取已完成')
        } catch (crawlError) {
          console.warn('自动抓取失败，但RSS源已添加:', crawlError)
          ElMessage.warning('RSS源添加成功，但自动抓取失败，请稍后手动更新')
        }
      } else {
        console.warn('创建RSS源响应中未找到ID，跳过自动抓取')
        ElMessage.success('RSS源添加成功')
      }
    }
    
    showAddRssDialog.value = false
    resetRssForm()
    loadRssSources()
    loadCrawlTasks() // 刷新任务列表
  } catch (error) {
    console.error('保存RSS源失败:', error)
    ElMessage.error('保存RSS源失败')
  } finally {
    savingRssSource.value = false
  }
}

const deleteRssSource = async (source) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除RSS源 "${source.name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await crawlerAPI.deleteRssSource(source.id)
    ElMessage.success('RSS源删除成功')
    loadRssSources()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除RSS源失败:', error)
      ElMessage.error('删除RSS源失败')
    }
  }
}

const crawlRssSource = async (sourceId) => {
  try {
    await crawlerAPI.crawlRssFeeds({
      source_ids: [sourceId]
    })
    ElMessage.success('RSS抓取任务已启动')
    loadCrawlTasks()
  } catch (error) {
    console.error('RSS抓取失败:', error)
    ElMessage.error('RSS抓取失败')
  }
}

const crawlWebpage = async () => {
  if (!webCrawlForm.url) {
    ElMessage.warning('请输入网页URL')
    return
  }
  
  try {
    crawlingWebpage.value = true
    const response = await crawlerAPI.crawlWebpage({
      url: webCrawlForm.url,
      category: webCrawlForm.category || undefined
    })
    
    if (response.success) {
      ElMessage.success('网页抓取成功')
      webCrawlForm.url = ''
      webCrawlForm.category = ''
      loadCrawlTasks()
    } else {
      ElMessage.error(response.message || '抓取失败')
    }
  } catch (error) {
    console.error('网页抓取失败:', error)
    ElMessage.error('网页抓取失败')
  } finally {
    crawlingWebpage.value = false
  }
}

const resetRssForm = () => {
  editingRssSource.value = null
  rssForm.name = ''
  rssForm.url = ''
  rssForm.category = ''
  rssForm.crawl_frequency = 3600
  rssForm.is_active = true
  // 清除表单验证状态
  rssFormRef.value?.clearValidate()
}

// 关闭对话框
const closeRssDialog = () => {
  showAddRssDialog.value = false
  // 对话框的 @close 事件会自动调用 resetRssForm
}

// 工具方法
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return formatToBeijingTime(dateStr)
}

const formatFrequency = (seconds) => {
  if (seconds < 3600) return `${seconds / 60}分钟`
  if (seconds < 86400) return `${seconds / 3600}小时`
  return `${seconds / 86400}天`
}

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

const getStatusType = (status) => {
  const statusMap = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return statusMap[status] || 'info'
}

const getStatusText = (status) => {
  const statusMap = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败'
  }
  return statusMap[status] || status
}

// 生命周期
onMounted(() => {
  loadRssSources()
  loadCrawlTasks()
})
</script>

<style scoped>
.crawler-page {
  padding: 20px;
}

.mb-4 {
  margin-bottom: 1rem;
}

.flex {
  display: flex;
}

.justify-between {
  justify-content: space-between;
}

.justify-center {
  justify-content: center;
}

.items-center {
  align-items: center;
}

.mt-4 {
  margin-top: 1rem;
}
</style>
