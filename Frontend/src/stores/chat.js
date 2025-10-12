import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { askQuestion } from '@/api/rag'
import { ElMessage } from 'element-plus'

/**
 * 聊天Store - 使用Composition API
 * 管理RAG问答对话、消息历史和统计
 */
export const useChatStore = defineStore('chat', () => {
  // ==================== State ====================
  
  // 聊天消息
  const messages = ref([])
  
  // 聊天状态
  const loading = ref(false)
  const streaming = ref(false)
  const streamingContent = ref('')
  
  // 聊天配置
  const chatConfig = ref({
    top_k: 10,
    enable_rerank: true,
    stream: false,
    temperature: 0.7,
    max_tokens: 2000
  })
  
  // 聊天统计
  const chatStats = ref({
    total_messages: 0,
    avg_response_time: 0,
    last_activity: null
  })
  
  // ==================== Computed ====================
  
  // 获取所有消息
  const getMessages = computed(() => messages.value)
  
  // 获取最后一条消息
  const lastMessage = computed(() => messages.value[messages.value.length - 1])
  
  // 获取用户消息数量
  const userMessageCount = computed(() => 
    messages.value.filter(msg => msg.type === 'user').length
  )
  
  // 获取AI消息数量
  const aiMessageCount = computed(() => 
    messages.value.filter(msg => msg.type === 'ai').length
  )
  
  // 是否正在聊天
  const isChatting = computed(() => loading.value || streaming.value)
  
  // 是否有聊天记录
  const hasMessages = computed(() => messages.value.length > 0)
  
  // 格式化的平均响应时间
  const formattedAvgResponseTime = computed(() => {
    const time = chatStats.value.avg_response_time
    return time < 1000 ? `${time.toFixed(0)}ms` : `${(time / 1000).toFixed(2)}s`
  })
  
  // ==================== Actions ====================
  
  /**
   * 发送消息
   * @param {string} message - 用户消息
   * @param {object} options - 发送选项
   * @returns {Promise<object>} AI响应消息
   */
  const sendMessage = async (message, options = {}) => {
    if (!message?.trim()) {
      throw new Error('消息内容不能为空')
    }

    // 添加用户消息
    addUserMessage(message)
    
    // 设置加载状态
    loading.value = true
    
    try {
      // 调试信息：检查认证状态
      const token = localStorage.getItem('token')
      console.log('发送消息时的认证状态:', {
        hasToken: !!token,
        tokenPreview: token ? token.substring(0, 20) + '...' : 'null',
        message: message
      })
      
      // 只发送后端期望的字段
      const requestData = {
        query: message,
        top_k: chatConfig.value.top_k,
        enable_rerank: chatConfig.value.enable_rerank,
        enable_web_fallback: true,  // ✅ 启用联网查询
        stream: chatConfig.value.stream,
        ...options
      }
      
      console.log('发送RAG请求数据:', requestData)
      
      const response = await askQuestion(requestData)
      
      console.log('收到RAG响应:', response)
      
      // 响应拦截器返回 data.data，所以response已经是实际数据
      // 后端返回格式：{ success: true, code: 200, data: { answer, sources, ... } }
      // 拦截器处理后：{ answer, sources, response_time, ... }
      
      let actualData = response
      
      // 如果response还包含data字段，说明拦截器返回的是整个data对象
      if (response && response.data && typeof response.data === 'object') {
        actualData = response.data
      }
      
      console.log('实际数据:', actualData)
      console.log('knowledge_used:', actualData.knowledge_used)
      console.log('web_search_used:', actualData.web_search_used)
      
      if (actualData && typeof actualData === 'object' && actualData.answer !== undefined) {
        const fullAnswer = actualData.answer || '抱歉，我无法回答您的问题。'
        
        // 后端返回的是下划线命名，需要正确读取
        const knowledgeUsed = actualData.knowledge_used !== undefined ? actualData.knowledge_used : false
        const webSearchUsed = actualData.web_search_used !== undefined ? actualData.web_search_used : false
        
        // 使用打字机效果逐字显示答案
        await typewriterEffect(
          fullAnswer, 
          actualData.sources || [], 
          actualData.response_time || 0, 
          actualData.quality_score || 0,
          knowledgeUsed,  // 是否使用了知识库
          webSearchUsed   // 是否使用了联网搜索
        )
        
        // 更新统计信息
        updateStats()
        
        return messages.value[messages.value.length - 1]
      } else {
        console.error('AI响应格式错误，响应内容:', response)
        console.error('实际数据:', actualData)
        throw new Error('AI响应格式错误')
      }
    } catch (error) {
      console.error('发送消息失败:', error)
      
      // 添加错误消息
      const errorMessage = {
        type: 'ai',
        content: '抱歉，我无法回答您的问题。请稍后重试。',
        error: true,
        timestamp: new Date()
      }
      
      addAIMessage(errorMessage)
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 流式发送消息
   * @param {string} message - 用户消息
   * @param {object} options - 发送选项
   */
  const sendMessageStream = async (message, options = {}) => {
    if (!message?.trim()) {
      throw new Error('消息内容不能为空')
    }

    // 添加用户消息
    addUserMessage(message)
    
    // 设置流式状态
    streaming.value = true
    streamingContent.value = ''
    
    try {
      // 只发送后端期望的字段
      const requestData = {
        query: message,
        top_k: chatConfig.value.top_k,
        enable_rerank: chatConfig.value.enable_rerank,
        enable_web_fallback: false,
        stream: true,
        ...options
      }
      
      console.log('发送流式RAG请求数据:', requestData)
      
      const response = await askQuestion(requestData)
      
      // 处理流式响应
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break
        
        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              
              if (data.type === 'content') {
                streamingContent.value += data.data
              } else if (data.type === 'sources') {
                // 处理来源信息
              } else if (data.type === 'done') {
                // 完成，添加最终消息
                const aiMessage = {
                  type: 'ai',
                  content: streamingContent.value,
                  timestamp: new Date()
                }
                
                addAIMessage(aiMessage)
                streamingContent.value = ''
              } else if (data.type === 'error') {
                throw new Error(data.message)
              }
            } catch (e) {
              console.error('解析流式数据失败:', e)
            }
          }
        }
      }
      
      // 更新统计信息
      updateStats()
      
    } catch (error) {
      console.error('流式发送消息失败:', error)
      throw error
    } finally {
      streaming.value = false
    }
  }

  /**
   * 打字机效果显示答案
   * @param {string} fullAnswer - 完整答案
   * @param {array} sources - 参考来源
   * @param {number} responseTime - 响应时间
   * @param {number} qualityScore - 质量评分
   * @param {boolean} knowledgeUsed - 是否使用了知识库
   * @param {boolean} webSearchUsed - 是否使用了联网搜索
   */
  const typewriterEffect = async (fullAnswer, sources, responseTime, qualityScore, knowledgeUsed = true, webSearchUsed = false) => {
    console.log('打字机效果参数:', { knowledgeUsed, webSearchUsed })
    
    // 创建一个临时消息对象用于逐字显示
    const tempMessage = {
      type: 'ai',
      content: '',
      sources: sources,
      responseTime: responseTime,
      qualityScore: qualityScore,
      knowledgeUsed: knowledgeUsed,
      webSearchUsed: webSearchUsed,
      timestamp: new Date(),
      isTyping: true
    }
    
    console.log('创建的消息对象:', tempMessage)
    
    messages.value.push(tempMessage)
    const messageIndex = messages.value.length - 1
    
    // 逐字添加内容（打字机效果）
    const words = fullAnswer.split('')
    const speed = 30 // 每个字符显示间隔（毫秒）
    
    for (let i = 0; i < words.length; i++) {
      messages.value[messageIndex].content += words[i]
      // 每10个字符暂停一下，让UI更新
      if (i % 10 === 0) {
        await new Promise(resolve => setTimeout(resolve, speed))
      }
    }
    
    // 完成打字效果
    messages.value[messageIndex].isTyping = false
  }

  /**
   * 添加用户消息
   * @param {string} content - 消息内容
   * @returns {object} 用户消息对象
   */
  const addUserMessage = (content) => {
    const userMessage = {
      type: 'user',
      content: content.trim(),
      timestamp: new Date()
    }
    
    messages.value.push(userMessage)
    updateStats()
    
    return userMessage
  }

  /**
   * 添加AI消息
   * @param {object} message - AI消息对象
   * @returns {object} AI消息对象
   */
  const addAIMessage = (message) => {
    messages.value.push(message)
    updateStats()
    
    return message
  }

  /**
   * 清空聊天记录
   */
  const clearMessages = () => {
    messages.value = []
    updateStats()
  }

  /**
   * 删除指定消息
   * @param {number} index - 消息索引
   */
  const removeMessage = (index) => {
    if (index >= 0 && index < messages.value.length) {
      messages.value.splice(index, 1)
      updateStats()
    }
  }

  /**
   * 更新聊天配置
   * @param {object} config - 配置对象
   */
  const updateChatConfig = (config) => {
    chatConfig.value = { ...chatConfig.value, ...config }
  }

  /**
   * 更新统计信息
   */
  const updateStats = () => {
    chatStats.value.total_messages = messages.value.length
    chatStats.value.last_activity = new Date()
    
    // 计算平均响应时间
    const aiMessages = messages.value.filter(msg => msg.type === 'ai' && msg.responseTime)
    if (aiMessages.length > 0) {
      const totalTime = aiMessages.reduce((sum, msg) => sum + msg.responseTime, 0)
      chatStats.value.avg_response_time = totalTime / aiMessages.length
    }
  }

  /**
   * 重置聊天状态
   */
  const resetChatState = () => {
    messages.value = []
    loading.value = false
    streaming.value = false
    streamingContent.value = ''
    updateStats()
  }

  /**
   * 导出聊天记录
   * @param {string} format - 导出格式 ('json' | 'txt')
   * @returns {string} 导出的内容
   */
  const exportChatHistory = (format = 'json') => {
    if (format === 'json') {
      return JSON.stringify(messages.value, null, 2)
    } else if (format === 'txt') {
      return messages.value.map(msg => 
        `${msg.type === 'user' ? '用户' : 'AI'}: ${msg.content}`
      ).join('\n\n')
    }
    return ''
  }
  
  /**
   * 导出为文本格式（便捷方法）
   * @returns {string} 文本格式的聊天记录
   */
  const exportAsText = () => exportChatHistory('txt')
  
  /**
   * 导出为JSON格式（便捷方法）
   * @returns {string} JSON格式的聊天记录
   */
  const exportAsJSON = () => exportChatHistory('json')
  
  // ==================== Return ====================
  
  return {
    // State
    messages,
    loading,
    streaming,
    streamingContent,
    chatConfig,
    chatStats,
    
    // Computed
    getMessages,
    lastMessage,
    userMessageCount,
    aiMessageCount,
    isChatting,
    hasMessages,
    formattedAvgResponseTime,
    
    // Actions
    sendMessage,
    sendMessageStream,
    addUserMessage,
    addAIMessage,
    clearMessages,
    removeMessage,
    updateChatConfig,
    updateStats,
    resetChatState,
    exportChatHistory,
    exportAsText,
    exportAsJSON
  }
}, {
  persist: {
    key: 'chat-store',
    storage: localStorage,
    paths: ['messages', 'chatConfig']
  }
})
