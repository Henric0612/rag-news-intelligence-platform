<template>
  <div class="chat-interface">
    <!-- 聊天消息列表 -->
    <div class="chat-messages" ref="messagesContainer">
      <div
        v-for="(message, index) in messages"
        :key="index"
        class="message"
        :class="{ 'user-message': message.type === 'user', 'ai-message': message.type === 'ai' }"
      >
        <div class="message-content">
          <div v-if="message.type === 'user'" class="user-content">
            <div class="message-text">{{ message.content }}</div>
            <div class="message-time">{{ formatTime(message.timestamp) }}</div>
          </div>
          
          <div v-else class="ai-content">
            <div class="ai-avatar">
              <el-icon><DataAnalysis /></el-icon>
            </div>
            <div class="ai-message-body">
              <!-- ✅ 思考过程可视化 -->
              <div v-if="message.thinking" class="thinking-section">
                <div class="thinking-stage">
                  <el-icon class="rotating"><Loading /></el-icon>
                  <span v-if="message.thinkingStage === 'retrieval'" class="stage-text">正在搜索知识库...</span>
                  <span v-else-if="message.thinkingStage === 'web_search'" class="stage-text">正在联网搜索...</span>
                  <span v-else-if="message.thinkingStage === 'rerank'" class="stage-text">正在优化搜索结果...</span>
                  <span v-else-if="message.thinkingStage === 'generation'" class="stage-text">正在思考答案...</span>
                  <span v-else class="stage-text">AI正在思考中...</span>
                </div>
              </div>
              
              <!-- ✅ AI回答内容（使用Markdown渲染） -->
              <div v-if="!message.thinking || message.content" class="answer-section">
                <div class="answer-label">
                  <el-icon><ChatDotRound /></el-icon>
                  <span>AI回答</span>
                </div>
                <div 
                  class="message-text markdown-body" 
                  v-html="renderMarkdown(message.content)" 
                  data-testid="qa-answer"
                ></div>
                <span v-if="message.isStreaming" class="streaming-cursor">|</span>
              </div>
              
              <!-- 参考来源 -->
              <div v-if="message.sources && message.sources.length > 0" class="message-sources" data-testid="retrieval-context">
                <div class="sources-header">
                  <el-icon><Document /></el-icon>
                  <span>参考来源</span>
                </div>
                <div class="sources-list">
                  <div
                    v-for="(source, idx) in message.sources"
                    :key="idx"
                    class="source-item"
                    @click="handleSourceClick(source)"
                  >
                    <span class="source-title">{{ source.title }}</span>
                    <!-- ✅ 来源类型标记 -->
                    <el-tag 
                      v-if="source.source_type === 'web_search'" 
                      type="warning" 
                      size="small" 
                      effect="plain"
                      class="source-type-tag"
                    >
                      联网搜索
                    </el-tag>
                    <el-tag 
                      v-else 
                      type="success" 
                      size="small" 
                      effect="plain"
                      class="source-type-tag"
                    >
                      知识库
                    </el-tag>
                    <span class="source-relevance">
                      相关度: {{ formatRelevance(source.similarity_score || source.score || source.relevance) }}
                    </span>
                  </div>
                </div>
              </div>
              
              <!-- ✅ 元信息（添加模型显示） -->
              <div class="message-meta">
                <!-- ✅ 模型信息 -->
                <span v-if="message.model" class="model-info">
                  <el-icon><Cpu /></el-icon>
                  {{ message.model }}
                </span>
                
                <span class="message-time">{{ formatTime(message.timestamp) }}</span>
                
                <span v-if="message.responseTime" class="response-time">
                  <el-icon><Timer /></el-icon>
                  {{ message.responseTime }}ms
                </span>
                <span v-if="message.qualityScore" class="quality-score">
                  <el-icon><Star /></el-icon>
                  {{ (message.qualityScore * 100).toFixed(1) }}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 加载/思考状态 -->
      <div v-if="loading && !streaming" class="message ai-message">
        <div class="message-content">
          <div class="ai-content">
            <div class="ai-avatar">
              <el-icon class="rotating"><Loading /></el-icon>
            </div>
            <div class="ai-message-body">
              <div class="thinking-dots">
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="dot"></span>
                <span class="thinking-text">AI正在思考中</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 流式输出显示 -->
      <div v-if="streaming" class="message ai-message">
        <div class="message-content">
          <div class="ai-content">
            <div class="ai-avatar">
              <el-icon><DataAnalysis /></el-icon>
            </div>
            <div class="ai-message-body">
              <div class="message-text streaming">
                <span v-html="streamingContent"></span>
                <span class="cursor">|</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 输入区域 -->
    <div class="chat-input">
      <div class="input-container">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="3"
          placeholder="请输入您的问题..."
          :disabled="loading || streaming"
          @keydown.enter.exact.prevent="handleSend"
          @keydown.enter.shift.exact="handleNewLine"
          class="message-input"
          data-testid="question-input"
        />
        <div class="input-actions">
          <div class="input-tips">
            <span>Enter 发送，Shift+Enter 换行</span>
          </div>
          <div class="action-buttons">
            <el-button
              type="info"
              size="small"
              @click="clearMessages"
              :disabled="!hasMessages"
              data-testid="clear-chat-button"
            >
              清空
            </el-button>
            <el-button
              type="success"
              size="small"
              @click="exportChatHistory"
              :disabled="!hasMessages"
              data-testid="export-chat-button"
            >
              导出
            </el-button>
            <el-button
              type="primary"
              :loading="loading || streaming"
              @click="handleSend"
              :disabled="!inputMessage.trim()"
              class="send-btn"
              data-testid="qa-button"
            >
              {{ streaming ? '生成中...' : '发送' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { DataAnalysis, Loading, ChatDotRound, Document, Timer, Star, Connection, Folder, Cpu } from '@element-plus/icons-vue'
import { useChatStore } from '@/stores/chat'
import { renderMarkdown } from '@/utils/markdown'
import 'highlight.js/styles/github-dark.css'

const props = defineProps({
  initialMessage: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['message-sent', 'source-click'])

// 使用聊天store
const chatStore = useChatStore()

// 响应式数据
const inputMessage = ref('')
const messagesContainer = ref(null)

// 从store获取状态
const messages = computed(() => chatStore.getMessages)
const loading = computed(() => chatStore.loading)
const streaming = computed(() => chatStore.streaming)
const streamingContent = computed(() => chatStore.streamingContent)
const hasMessages = computed(() => chatStore.hasMessages)

// 发送消息
const handleSend = async () => {
  if (!inputMessage.value.trim() || loading.value || streaming.value) {
    return
  }
  
  const query = inputMessage.value.trim()
  inputMessage.value = ''
  
  // 滚动到底部
  await scrollToBottom()
  
  try {
    // 使用聊天store发送消息
    await chatStore.sendMessage(query)
    emit('message-sent', { type: 'user', content: query, timestamp: new Date() })
  } catch (error) {
    console.error('发送消息失败:', error)
    ElMessage.error('发送消息失败，请稍后重试')
  }
  
  // 滚动到底部
  await scrollToBottom()
}


// 流式发送消息
const handleSendStream = async (query) => {
  try {
    await chatStore.sendMessageStream(query)
  } catch (error) {
    console.error('流式发送消息失败:', error)
    ElMessage.error('发送消息失败，请稍后重试')
  }
  
  await scrollToBottom()
}

// 处理换行
const handleNewLine = () => {
  inputMessage.value += '\n'
}

// 处理来源点击
const handleSourceClick = (source) => {
  emit('source-click', source)
}

// ✅ AI消息使用导入的renderMarkdown函数
// formatAIMessage函数已被renderMarkdown替代

// 格式化时间
const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

// 格式化相关度
const formatRelevance = (score) => {
  if (!score && score !== 0) return 'N/A'
  // score可能是0-1之间的小数，也可能已经是百分比
  const percentage = score > 1 ? score : (score * 100)
  return `${percentage.toFixed(1)}%`
}

// 滚动到底部
const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 清空聊天记录
const clearMessages = () => {
  chatStore.clearMessages()
}

// 导出聊天记录
const exportChatHistory = () => {
  try {
    const chatHistory = chatStore.exportChatHistory('json')
    const blob = new Blob([chatHistory], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `chat-history-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('聊天记录导出成功')
  } catch (error) {
    console.error('导出聊天记录失败:', error)
    ElMessage.error('导出聊天记录失败')
  }
}

// 添加欢迎消息
const addWelcomeMessage = () => {
  chatStore.addAIMessage({
    type: 'ai',
    content: '您好！我是 RAG News Intelligence Platform 助手，可以帮您搜索和解答新闻相关问题。请告诉我您想了解什么？',
    timestamp: new Date()
  })
}

// 组件挂载
onMounted(() => {
  if (props.initialMessage) {
    inputMessage.value = props.initialMessage
  }
  
  // 添加欢迎消息
  if (!chatStore.hasMessages) {
    addWelcomeMessage()
  }
})

// 暴露方法给父组件
defineExpose({
  clearMessages,
  addWelcomeMessage,
  sendMessage: handleSend,
  sendMessageStream: handleSendStream
})
</script>

<style scoped>
.chat-interface {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 600px;
  max-height: calc(100vh - 300px);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: #f8f9fa;
  scroll-behavior: smooth;
}

/* 自定义滚动条 */
.chat-messages::-webkit-scrollbar {
  width: 8px;
}

.chat-messages::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.message {
  display: flex;
  width: 100%;
}

.message.user-message {
  justify-content: flex-end;
}

.message.ai-message {
  justify-content: flex-start;
}

.message-content {
  max-width: 80%;
}

.user-content {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: white;
  padding: 14px 18px;
  border-radius: 18px 18px 4px 18px;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.25);
  transition: all 0.3s ease;
}

.user-content:hover {
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35);
  transform: translateY(-1px);
}

.ai-content {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.ai-avatar {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: white;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.ai-message-body {
  flex: 1;
  background: white;
  padding: 16px 20px;
  border-radius: 18px 18px 18px 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid #e4e7ed;
  transition: all 0.3s ease;
}

.ai-message-body:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.message-text {
  line-height: 1.6;
  margin-bottom: 8px;
}

.message-text.streaming {
  position: relative;
}

.cursor {
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* ✅ 思考过程可视化样式 */
.thinking-section {
  margin-bottom: 12px;
}

.thinking-stage {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-left: 4px solid #409eff;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  animation: pulse 2s ease-in-out infinite;
}

.thinking-stage .el-icon {
  font-size: 18px;
  color: #409eff;
}

.stage-text {
  color: #409eff;
  flex: 1;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
}

.thinking-dots {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}

.dot {
  width: 8px;
  height: 8px;
  background: #409eff;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) {
  animation-delay: -0.32s;
}

.dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

.thinking-text {
  color: #909399;
  font-size: 14px;
  margin-left: 8px;
}

.rotating {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* AI回答区域 */
.answer-section {
  margin-bottom: 12px;
}

.answer-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #409eff;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 2px solid #e4e7ed;
}

.answer-label .el-icon {
  font-size: 16px;
}

/* 参考来源 */
.message-sources {
  margin: 12px 0;
  padding: 12px;
  background: #ecf5ff;
  border-left: 3px solid #409eff;
  border-radius: 4px;
}

.sources-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #409eff;
  margin-bottom: 10px;
  font-weight: 600;
}

.sources-header .el-icon {
  font-size: 16px;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.source-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid #e4e7ed;
  margin-bottom: 8px;
  gap: 8px;
}

.source-item:hover {
  background: #f0f9ff;
  border-color: #409eff;
  transform: translateX(4px);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.15);
}

.source-item:last-child {
  margin-bottom: 0;
}

.source-title {
  font-size: 14px;
  color: #303133;
  flex: 1;
  font-weight: 500;
}

/* ✅ 来源类型标签样式 */
.source-type-tag {
  flex-shrink: 0;
  font-size: 11px;
  padding: 0 6px;
  height: 20px;
  line-height: 20px;
}

.source-relevance {
  font-size: 12px;
  color: #67c23a;
  margin-left: 8px;
  padding: 2px 8px;
  background: #f0f9ff;
  border-radius: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.message-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #909399;
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid #e4e7ed;
  align-items: center;
}

.message-meta > span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.message-meta .el-icon {
  font-size: 14px;
}

.message-time {
  font-size: 12px;
  opacity: 0.8;
}

.response-time {
  color: #909399;
}

.quality-score {
  color: #f56c6c;
}

/* ✅ 模型信息样式 */
.model-info {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #909399;
  font-size: 12px;
  padding: 3px 10px;
  background: #f4f4f5;
  border-radius: 12px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.model-info:hover {
  background: #e9e9eb;
  color: #606266;
}

.model-info .el-icon {
  font-size: 14px;
}

/* ✅ 流式输出光标动画 */
.streaming-cursor {
  display: inline-block;
  margin-left: 2px;
  animation: blink 1s infinite;
  color: #409eff;
  font-weight: bold;
}

/* ✅ Markdown渲染样式 */
.markdown-body {
  font-size: 15px;
  line-height: 1.8;
  color: #303133;
  word-wrap: break-word;
  word-break: break-word;
}

.markdown-body p {
  margin: 0.8em 0;
  line-height: 1.8;
}

.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4,
.markdown-body h5,
.markdown-body h6 {
  margin: 1.2em 0 0.6em;
  font-weight: 600;
  line-height: 1.4;
  color: #303133;
}

.markdown-body h1 { font-size: 1.8em; border-bottom: 2px solid #e4e7ed; padding-bottom: 0.3em; }
.markdown-body h2 { font-size: 1.5em; border-bottom: 1px solid #e4e7ed; padding-bottom: 0.3em; }
.markdown-body h3 { font-size: 1.3em; }
.markdown-body h4 { font-size: 1.1em; }
.markdown-body h5 { font-size: 1em; }
.markdown-body h6 { font-size: 0.9em; color: #606266; }

.markdown-body strong {
  font-weight: 600;
  color: #303133;
}

.markdown-body em {
  font-style: italic;
  color: #606266;
}

.markdown-body code {
  background: #f4f4f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', 'Monaco', 'Consolas', monospace;
  font-size: 0.9em;
  color: #e83e8c;
  border: 1px solid #e9e9eb;
}

.markdown-body pre {
  background: #282c34;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 1em 0;
  border: 1px solid #3e4451;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.markdown-body pre code {
  background: transparent;
  padding: 0;
  border: none;
  color: #abb2bf;
  font-size: 0.95em;
  line-height: 1.6;
}

.markdown-body ul,
.markdown-body ol {
  padding-left: 28px;
  margin: 0.8em 0;
}

.markdown-body li {
  margin: 0.4em 0;
  line-height: 1.6;
}

.markdown-body ul li {
  list-style-type: disc;
}

.markdown-body ol li {
  list-style-type: decimal;
}

.markdown-body blockquote {
  border-left: 4px solid #409eff;
  padding: 12px 16px;
  margin: 1em 0;
  background: #f0f9ff;
  color: #606266;
  border-radius: 4px;
}

.markdown-body blockquote p {
  margin: 0;
}

.markdown-body a {
  color: #409eff;
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: all 0.3s ease;
}

.markdown-body a:hover {
  border-bottom-color: #409eff;
  color: #66b1ff;
}

.markdown-body table {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
  overflow: hidden;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.markdown-body table th,
.markdown-body table td {
  padding: 10px 12px;
  border: 1px solid #e4e7ed;
  text-align: left;
}

.markdown-body table th {
  background: #f5f7fa;
  font-weight: 600;
  color: #303133;
}

.markdown-body table tr:nth-child(even) {
  background: #fafafa;
}

.markdown-body table tr:hover {
  background: #f0f9ff;
}

.markdown-body hr {
  border: none;
  border-top: 2px solid #e4e7ed;
  margin: 1.5em 0;
}

.markdown-body img {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 1em 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 代码高亮样式增强 */
.markdown-body .hljs {
  display: block;
  overflow-x: auto;
  padding: 1em;
  background: #282c34;
  color: #abb2bf;
}

.chat-input {
  border-top: 2px solid #e4e7ed;
  padding: 20px 24px;
  background: white;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
}

.input-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-input {
  width: 100%;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.input-tips {
  font-size: 12px;
  color: #909399;
}

.action-buttons {
  display: flex;
  gap: 8px;
  align-items: center;
}

.send-btn {
  border-radius: 20px;
  padding: 10px 28px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
  transition: all 0.3s ease;
}

.send-btn:hover {
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
  transform: translateY(-2px);
}

.send-btn:active {
  transform: translateY(0);
}

/* ✅ 暗色主题适配（包括Markdown） */
.dark .chat-messages {
  background: #1f1f1f;
}

.dark .chat-messages::-webkit-scrollbar-track {
  background: #2d2d2d;
}

.dark .chat-messages::-webkit-scrollbar-thumb {
  background: #4c4d4f;
}

.dark .chat-messages::-webkit-scrollbar-thumb:hover {
  background: #5c5d5f;
}

.dark .ai-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.5);
}

.dark .ai-message-body {
  background: #2d2d2d;
  color: #e5eaf3;
  border-color: #4c4d4f;
}

.dark .ai-message-body:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

/* ✅ 暗色模式 - 思考过程 */
.dark .thinking-stage {
  background: linear-gradient(135deg, #1e3a5f 0%, #2d4a6f 100%);
  border-left-color: #5a9cf8;
}

.dark .thinking-stage .el-icon,
.dark .stage-text {
  color: #7db3ff;
}

.dark .message-sources {
  background: #1f1f1f;
  border-left-color: #667eea;
}

.dark .sources-header {
  color: #667eea;
}

.dark .source-item {
  background: #2d2d2d;
  color: #e5eaf3;
  border-color: #4c4d4f;
}

.dark .source-item:hover {
  background: #3a3a3a;
  border-color: #667eea;
}

.dark .source-title {
  color: #e5eaf3;
}

.dark .source-relevance {
  background: #1f1f1f;
  color: #67c23a;
}

.dark .message-meta {
  color: #a8abb2;
  border-top-color: #4c4d4f;
}

/* ✅ 暗色模式 - 模型信息 */
.dark .model-info {
  background: #3a3a3a;
  color: #a8abb2;
}

.dark .model-info:hover {
  background: #4c4d4f;
  color: #e5eaf3;
}

/* ✅ 暗色模式 - Markdown样式 */
.dark .markdown-body {
  color: #e5eaf3;
}

.dark .markdown-body h1,
.dark .markdown-body h2,
.dark .markdown-body h3,
.dark .markdown-body h4,
.dark .markdown-body h5,
.dark .markdown-body h6 {
  color: #e5eaf3;
  border-bottom-color: #4c4d4f;
}

.dark .markdown-body strong {
  color: #ffffff;
}

.dark .markdown-body em {
  color: #a8abb2;
}

.dark .markdown-body code {
  background: #3a3a3a;
  color: #ff6b9d;
  border-color: #4c4d4f;
}

.dark .markdown-body pre {
  background: #1e1e1e;
  border-color: #2d2d2d;
}

.dark .markdown-body blockquote {
  background: #1e3a5f;
  border-left-color: #5a9cf8;
  color: #a8abb2;
}

.dark .markdown-body a {
  color: #5a9cf8;
}

.dark .markdown-body a:hover {
  color: #7db3ff;
  border-bottom-color: #7db3ff;
}

.dark .markdown-body table {
  border-color: #4c4d4f;
}

.dark .markdown-body table th,
.dark .markdown-body table td {
  border-color: #4c4d4f;
}

.dark .markdown-body table th {
  background: #3a3a3a;
  color: #e5eaf3;
}

.dark .markdown-body table tr:nth-child(even) {
  background: #2d2d2d;
}

.dark .markdown-body table tr:hover {
  background: #3a3a3a;
}

.dark .markdown-body hr {
  border-top-color: #4c4d4f;
}

.dark .chat-input {
  border-top-color: #4c4d4f;
  background: #2d2d2d;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.3);
}

.dark .input-tips {
  color: #a8abb2;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .chat-interface {
    min-height: 500px;
    max-height: calc(100vh - 250px);
  }
  
  .chat-messages {
    padding: 16px;
    gap: 16px;
  }
  
  .message-content {
    max-width: 90%;
  }
  
  .ai-avatar {
    width: 32px;
    height: 32px;
  }
  
  .chat-input {
    padding: 16px;
  }
  
  .send-btn {
    padding: 8px 20px;
  }
}

@media (max-width: 480px) {
  .message-content {
    max-width: 95%;
  }
  
  .action-buttons {
    flex-wrap: wrap;
  }
  
  .input-tips {
    font-size: 11px;
  }
}
</style>
