<template>
  <div class="file-upload-page">
    <PageContainer title="文件上传管理">
      <!-- 文件上传区域 -->
      <el-card class="mb-4" shadow="hover">
        <template #header>
          <h3 class="text-lg font-semibold">文件上传</h3>
        </template>

        <el-upload
          ref="uploadRef"
          class="upload-demo"
          drag
          :action="uploadUrl"
          :headers="uploadHeaders"
          :data="uploadData"
          :before-upload="beforeUpload"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :on-progress="handleUploadProgress"
          :multiple="true"
          :accept="acceptedFileTypes"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            将文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持格式：{{ supportedFormatsText }}，单个文件不超过 {{ maxFileSizeMB }}MB
            </div>
          </template>
        </el-upload>

        <!-- 上传参数设置 -->
        <div class="mt-4">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="分类标签">
                <el-input
                  v-model="uploadForm.category"
                  placeholder="请输入分类标签（可选）"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="内容标签">
                <el-input
                  v-model="uploadForm.tags"
                  placeholder="请输入标签，用逗号分隔（可选）"
                />
              </el-form-item>
            </el-col>
          </el-row>
        </div>
      </el-card>

      <!-- 批量上传 -->
      <el-card class="mb-4" shadow="hover">
        <template #header>
          <h3 class="text-lg font-semibold">批量上传</h3>
        </template>

        <el-upload
          ref="batchUploadRef"
          class="batch-upload"
          :action="batchUploadUrl"
          :headers="uploadHeaders"
          :data="uploadData"
          :before-upload="beforeBatchUpload"
          :on-success="handleBatchUploadSuccess"
          :on-error="handleBatchUploadError"
          :multiple="true"
          :accept="acceptedFileTypes"
        >
          <el-button type="primary">
            <el-icon><upload /></el-icon>
            选择多个文件
          </el-button>
          <template #tip>
            <div class="el-upload__tip">
              可以同时选择多个文件进行批量上传
            </div>
          </template>
        </el-upload>
      </el-card>

      <!-- 上传进度 -->
      <el-card v-if="uploadProgress.length > 0" class="mb-4" shadow="hover">
        <template #header>
          <h3 class="text-lg font-semibold">上传进度</h3>
        </template>

        <div v-for="progress in uploadProgress" :key="progress.id" class="mb-2">
          <div class="flex justify-between items-center mb-1">
            <span class="text-sm">{{ progress.filename }}</span>
            <span class="text-sm">{{ progress.percentage }}%</span>
          </div>
          <el-progress
            :percentage="progress.percentage"
            :status="progress.status"
            :stroke-width="6"
          />
        </div>
      </el-card>

      <!-- 已上传文件列表 -->
      <el-card shadow="hover">
        <template #header>
          <div class="flex justify-between items-center">
            <h3 class="text-lg font-semibold">已上传文件</h3>
            <el-button @click="loadUploadedFiles">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </template>

        <el-table
          :data="uploadedFiles"
          v-loading="loadingFiles"
          stripe
          style="width: 100%"
        >
          <el-table-column prop="filename" label="文件名" />
          <el-table-column prop="category" label="分类" width="120" />
          <el-table-column prop="chunks_count" label="分块数" width="100" />
          <el-table-column prop="total_content_length" label="内容长度" width="120">
            <template #default="{ row }">
              {{ formatFileSize(row.total_content_length) }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="上传时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="viewFileDetails(row)">
                查看
              </el-button>
              <el-button size="small" type="danger" @click="deleteFile(row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 文件详情对话框 -->
      <el-dialog
        v-model="showFileDetailsDialog"
        title="文件详情"
        width="800px"
      >
        <div v-if="selectedFile">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="文件名">
              {{ selectedFile.filename }}
            </el-descriptions-item>
            <el-descriptions-item label="分类">
              {{ selectedFile.category || '未分类' }}
            </el-descriptions-item>
            <el-descriptions-item label="分块数量">
              {{ selectedFile.chunks_count }}
            </el-descriptions-item>
            <el-descriptions-item label="内容长度">
              {{ formatFileSize(selectedFile.total_content_length) }}
            </el-descriptions-item>
            <el-descriptions-item label="上传时间">
              {{ formatDate(selectedFile.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="标签">
              {{ selectedFile.tags ? selectedFile.tags.join(', ') : '无' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </el-dialog>

      <!-- 文本处理工具 -->
      <el-card class="mt-4" shadow="hover">
        <template #header>
          <h3 class="text-lg font-semibold">文本处理工具</h3>
        </template>

        <el-tabs v-model="activeTab">
          <!-- 文本分块 -->
          <el-tab-pane label="文本分块" name="chunk">
            <el-form :model="chunkForm" @submit.prevent="chunkText">
              <el-form-item label="文本内容">
                <el-input
                  v-model="chunkForm.text"
                  type="textarea"
                  :rows="6"
                  placeholder="请输入要分块的文本内容"
                />
              </el-form-item>
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="块大小">
                    <el-input-number
                      v-model="chunkForm.chunk_size"
                      :min="100"
                      :max="5000"
                      :step="100"
                    />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="重叠大小">
                    <el-input-number
                      v-model="chunkForm.overlap"
                      :min="0"
                      :max="500"
                      :step="50"
                    />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item>
                <el-button type="primary" @click="chunkText" :loading="chunking">
                  分块处理
                </el-button>
              </el-form-item>
            </el-form>

            <!-- 分块结果 -->
            <div v-if="chunkResults.length > 0" class="mt-4">
              <h4 class="text-md font-semibold mb-2">分块结果 ({{ chunkResults.length }} 块)</h4>
              <el-collapse>
                <el-collapse-item
                  v-for="(chunk, index) in chunkResults"
                  :key="index"
                  :title="`第 ${index + 1} 块 (${chunk.length} 字符)`"
                >
                  <div class="text-sm text-gray-600 whitespace-pre-wrap">{{ chunk }}</div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-tab-pane>

          <!-- 内容提取 -->
          <el-tab-pane label="内容提取" name="extract">
            <el-upload
              ref="extractUploadRef"
              class="extract-upload"
              :action="extractUrl"
              :headers="uploadHeaders"
              :before-upload="beforeExtract"
              :on-success="handleExtractSuccess"
              :on-error="handleExtractError"
              :accept="acceptedFileTypes"
              :show-file-list="false"
            >
              <el-button type="primary">
                <el-icon><document /></el-icon>
                选择文件提取内容
              </el-button>
            </el-upload>

            <!-- 提取结果 -->
            <div v-if="extractedContent" class="mt-4">
              <h4 class="text-md font-semibold mb-2">提取的内容 ({{ extractedContent.length }} 字符)</h4>
              <el-input
                v-model="extractedContent"
                type="textarea"
                :rows="10"
                readonly
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </PageContainer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, Upload, Refresh, Document } from '@element-plus/icons-vue'
import PageContainer from '@/components/PageContainer.vue'
import { uploadAPI } from '@/api/upload'
import { useAuthStore } from '@/stores/auth'
import { formatToBeijingTime } from '@/utils/dateFormatter'

// 响应式数据
const uploadRef = ref()
const batchUploadRef = ref()
const extractUploadRef = ref()

const loadingFiles = ref(false)
const chunking = ref(false)

const uploadedFiles = ref([])
const uploadProgress = ref([])
const selectedFile = ref(null)
const showFileDetailsDialog = ref(false)

const activeTab = ref('chunk')

// 表单数据
const uploadForm = reactive({
  category: '',
  tags: ''
})

const chunkForm = reactive({
  text: '',
  chunk_size: 1000,
  overlap: 200
})

const chunkResults = ref([])
const extractedContent = ref('')

// 计算属性
const authStore = useAuthStore()

const uploadUrl = computed(() => '/api/upload/file')
const batchUploadUrl = computed(() => '/api/upload/files')
const extractUrl = computed(() => '/api/upload/extract')

const uploadHeaders = computed(() => ({
  'Authorization': `Bearer ${authStore.token}`
}))

const uploadData = computed(() => ({
  category: uploadForm.category || undefined,
  tags: uploadForm.tags || undefined
}))

const supportedFormatsText = computed(() => 'TXT, PDF, DOC, DOCX, RTF')
const maxFileSizeMB = computed(() => 10)
const acceptedFileTypes = computed(() => '.txt,.pdf,.doc,.docx,.rtf')

// 方法
const loadUploadedFiles = async () => {
  try {
    loadingFiles.value = true
    const response = await uploadAPI.getUploadedFiles()
    
    // 响应拦截器已返回 data.data，直接使用
    if (response && response.files) {
      uploadedFiles.value = response.files
    } else if (response && response.success && response.files) {
      uploadedFiles.value = response.files
    } else {
      uploadedFiles.value = []
      console.warn('未获取到文件列表数据')
    }
  } catch (error) {
    console.error('加载文件列表失败:', error)
    ElMessage.error('加载文件列表失败')
    uploadedFiles.value = []
  } finally {
    loadingFiles.value = false
  }
}

const beforeUpload = (file) => {
  // 文件验证
  const isValidType = acceptedFileTypes.value.split(',').some(type => 
    file.name.toLowerCase().endsWith(type.replace('.', ''))
  )
  
  if (!isValidType) {
    ElMessage.error('不支持的文件类型')
    return false
  }
  
  const isLtMaxSize = file.size / 1024 / 1024 < maxFileSizeMB.value
  if (!isLtMaxSize) {
    ElMessage.error(`文件大小不能超过 ${maxFileSizeMB.value}MB`)
    return false
  }
  
  // 添加到进度跟踪
  const progressId = Date.now() + Math.random()
  uploadProgress.value.push({
    id: progressId,
    filename: file.name,
    percentage: 0,
    status: ''
  })
  
  return true
}

const beforeBatchUpload = (file) => {
  return beforeUpload(file)
}

const beforeExtract = (file) => {
  return beforeUpload(file)
}

const handleUploadSuccess = (response, file) => {
  const progress = uploadProgress.value.find(p => p.filename === file.name)
  if (progress) {
    progress.percentage = 100
    progress.status = 'success'
  }
  
  if (response.success) {
    ElMessage.success(`文件 ${file.name} 上传成功`)
    loadUploadedFiles()
  } else {
    ElMessage.error(response.message || '上传失败')
  }
  
  // 清理进度
  setTimeout(() => {
    const index = uploadProgress.value.findIndex(p => p.filename === file.name)
    if (index > -1) {
      uploadProgress.value.splice(index, 1)
    }
  }, 2000)
}

const handleUploadError = (error, file) => {
  const progress = uploadProgress.value.find(p => p.filename === file.name)
  if (progress) {
    progress.status = 'exception'
  }
  
  console.error('上传失败:', error)
  ElMessage.error(`文件 ${file.name} 上传失败`)
}

const handleUploadProgress = (event, file) => {
  const progress = uploadProgress.value.find(p => p.filename === file.name)
  if (progress) {
    progress.percentage = Math.round(event.percent)
  }
}

const handleBatchUploadSuccess = (response) => {
  if (response.success) {
    ElMessage.success(`批量上传完成，成功 ${response.data.successful_uploads} 个，失败 ${response.data.failed_uploads} 个`)
    loadUploadedFiles()
  } else {
    ElMessage.error('批量上传失败')
  }
}

const handleBatchUploadError = (error) => {
  console.error('批量上传失败:', error)
  ElMessage.error('批量上传失败')
}

const handleExtractSuccess = (response) => {
  if (response.success) {
    extractedContent.value = response.data.content
    ElMessage.success('内容提取成功')
  } else {
    ElMessage.error('内容提取失败')
  }
}

const handleExtractError = (error) => {
  console.error('内容提取失败:', error)
  ElMessage.error('内容提取失败')
}

const viewFileDetails = (file) => {
  selectedFile.value = file
  showFileDetailsDialog.value = true
}

const deleteFile = async (file) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除文件 "${file.filename}" 吗？这将删除所有相关的知识库条目。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const response = await uploadAPI.deleteFile(file.filename)
    
    if (response.success) {
      ElMessage.success('文件删除成功')
      loadUploadedFiles()
    } else {
      ElMessage.error('删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除文件失败:', error)
      ElMessage.error('删除文件失败')
    }
  }
}

const chunkText = async () => {
  if (!chunkForm.text.trim()) {
    ElMessage.warning('请输入要分块的文本内容')
    return
  }
  
  try {
    chunking.value = true
    const response = await uploadAPI.chunkText({
      text: chunkForm.text,
      chunk_size: chunkForm.chunk_size,
      overlap: chunkForm.overlap
    })
    
    if (response.success) {
      chunkResults.value = response.data.chunks
      ElMessage.success(`文本分块完成，共 ${response.data.chunks_count} 块`)
    } else {
      ElMessage.error('文本分块失败')
    }
  } catch (error) {
    console.error('文本分块失败:', error)
    ElMessage.error('文本分块失败')
  } finally {
    chunking.value = false
  }
}

// 工具方法
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return formatToBeijingTime(dateStr)
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 生命周期
onMounted(() => {
  loadUploadedFiles()
})
</script>

<style scoped>
.file-upload-page {
  padding: 20px;
}

.mb-4 {
  margin-bottom: 1rem;
}

.mt-4 {
  margin-top: 1rem;
}

.flex {
  display: flex;
}

.justify-between {
  justify-content: space-between;
}

.items-center {
  align-items: center;
}

.mb-2 {
  margin-bottom: 0.5rem;
}

.mb-1 {
  margin-bottom: 0.25rem;
}

.text-sm {
  font-size: 0.875rem;
}

.text-md {
  font-size: 1rem;
}

.text-lg {
  font-size: 1.125rem;
}

.font-semibold {
  font-weight: 600;
}

.text-gray-600 {
  color: #6b7280;
}

.whitespace-pre-wrap {
  white-space: pre-wrap;
}

.upload-demo {
  width: 100%;
}

.batch-upload {
  margin-bottom: 1rem;
}

.extract-upload {
  margin-bottom: 1rem;
}
</style>
