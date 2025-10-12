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
   * 发送消息（支持流式输出）
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
    
    // ✅ 启用流式请求
    const useStreaming = true
    
    if (useStreaming) {
      // 使用真正的流式处理
      return await sendMessageStream(message, options)
    } else {
      // 使用传统的非流式处理（保留作为备用）
      return await sendMessageNonStream(message, options)
    }
  }

  /**
   * 非流式发送消息（备用方法）
   */
  const sendMessageNonStream = async (message, options = {}) => {
    loading.value = true
    
    try {
      const requestData = {
        query: message,
        top_k: chatConfig.value.top_k,
        enable_rerank: chatConfig.value.enable_rerank,
        enable_web_fallback: true,
        stream: false,
        ...options
      }
      
      const response = await askQuestion(requestData)
      let actualData = response
      
      if (response && response.data && typeof response.data === 'object') {
        actualData = response.data
      }
      
      if (actualData && typeof actualData === 'object' && actualData.answer !== undefined) {
        const fullAnswer = actualData.answer || '抱歉，我无法回答您的问题。'
        const knowledgeUsed = actualData.knowledge_used !== undefined ? actualData.knowledge_used : false
        const webSearchUsed = actualData.web_search_used !== undefined ? actualData.web_search_used : false
        
        // 使用打字机效果逐字显示答案
        await typewriterEffect(
          fullAnswer, 
          actualData.sources || [], 
          actualData.response_time || 0, 
          actualData.quality_score || 0,
          knowledgeUsed,
          webSearchUsed,
          actualData.model || 'unknown'
        )
        
        updateStats()
        return messages.value[messages.value.length - 1]
      } else {
        throw new Error('AI响应格式错误')
      }
    } catch (error) {
      console.error('发送消息失败:', error)
      
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
   * 流式发送消息（真正的SSE实现）
   * @param {string} message - 用户消息
   * @param {object} options - 发送选项
   */
  const sendMessageStream = async (message, options = {}) => {
    // 设置流式状态
    streaming.value = true
    
    try {
      // 获取认证token
      const token = localStorage.getItem('token')
      if (!token) {
        throw new Error('未登录，请先登录')
      }
      
      // 构建请求数据
      const requestData = {
        query: message,
        top_k: chatConfig.value.top_k,
        enable_rerank: chatConfig.value.enable_rerank,
        enable_web_fallback: true,
        stream: true,  // ✅ 启用流式输出
        ...options
      }
      
      console.log('发送流式RAG请求:', requestData)
      
      // ✅ 创建AI消息对象（用于实时更新）
      const aiMessage = {
        type: 'ai',
        content: '',
        thinking: true,
        thinkingStage: 'retrieval',  // 初始阶段
        sources: [],
        model: '',
        knowledgeUsed: true,
        webSearchUsed: false,
        responseTime: 0,
        qualityScore: 0,
        timestamp: new Date(),
        isStreaming: true
      }
      
      // 立即添加到消息列表
      messages.value.push(aiMessage)
      const messageIndex = messages.value.length - 1
      
      // ✅ 使用Fetch API进行流式请求
      const response = await fetch('/api/rag/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestData)
      })
      
      if (!response.ok) {
        throw new Error(`请求失败: ${response.status} ${response.statusText}`)
      }
      
      // ✅ 读取流式响应
      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          console.log('流式响应完成')
          break
        }
        
        // 解码数据块
        buffer += decoder.decode(value, { stream: true })
        
        // 处理完整的SSE消息（以\n\n分隔）
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // 保留最后不完整的行
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6).trim()
              if (!jsonStr) continue
              
              const data = JSON.parse(jsonStr)
              console.log('收到流式数据:', data)
              
              // ✅ 处理不同类型的消息
              if (data.type === 'thinking') {
                // 更新思考阶段
                messages.value[messageIndex].thinkingStage = data.stage
                console.log(`思考阶段: ${data.stage} - ${data.message}`)
                
              } else if (data.type === 'sources') {
                // 接收参考来源和元信息
                const sourcesData = data.data
                messages.value[messageIndex].sources = sourcesData.sources || []
                messages.value[messageIndex].model = sourcesData.model || 'unknown'
                messages.value[messageIndex].knowledgeUsed = sourcesData.knowledge_used !== undefined ? sourcesData.knowledge_used : true
                messages.value[messageIndex].webSearchUsed = sourcesData.web_search_used !== undefined ? sourcesData.web_search_used : false
                console.log('收到参考来源:', sourcesData)
                
              } else if (data.type === 'content') {
                // 接收答案内容片段
                messages.value[messageIndex].thinking = false
                messages.value[messageIndex].content += data.data
                
              } else if (data.type === 'done') {
                // 完成
                messages.value[messageIndex].thinking = false
                messages.value[messageIndex].isStreaming = false
                
                // 设置统计信息
                if (data.stats) {
                  messages.value[messageIndex].responseTime = Math.round(data.stats.response_time * 1000) || 0
                  messages.value[messageIndex].qualityScore = 0.85 // 默认质量评分
                }
                
                console.log('流式生成完成')
                
              } else if (data.type === 'error') {
                // 错误处理
                console.error('流式错误:', data.message)
                messages.value[messageIndex].thinking = false
                messages.value[messageIndex].isStreaming = false
                messages.value[messageIndex].error = true
                messages.value[messageIndex].content = data.message || '抱歉，生成答案时发生错误。'
              }
              
            } catch (e) {
              console.error('解析流式数据失败:', e, line)
            }
          }
        }
      }
      
      // 更新统计信息
      updateStats()
      
      return messages.value[messageIndex]
      
    } catch (error) {
      console.error('流式发送消息失败:', error)
      
      // 添加错误消息
      const errorMessage = {
        type: 'ai',
        content: `抱歉，发生错误: ${error.message}`,
        error: true,
        timestamp: new Date()
      }
      
      addAIMessage(errorMessage)
      throw error
      
    } finally {
      streaming.value = false
    }
  }

  /**
   * 打字机效果显示答案（备用方法，用于非流式模式）
   * @param {string} fullAnswer - 完整答案
   * @param {array} sources - 参考来源
   * @param {number} responseTime - 响应时间
   * @param {number} qualityScore - 质量评分
   * @param {boolean} knowledgeUsed - 是否使用了知识库
   * @param {boolean} webSearchUsed - 是否使用了联网搜索
   * @param {string} model - 模型名称
   */
  const typewriterEffect = async (fullAnswer, sources, responseTime, qualityScore, knowledgeUsed = true, webSearchUsed = false, model = 'unknown') => {
    console.log('打字机效果参数:', { knowledgeUsed, webSearchUsed, model })
    
    // 创建一个临时消息对象用于逐字显示
    const tempMessage = {
      type: 'ai',
      content: '',
      sources: sources,
      responseTime: responseTime,
      qualityScore: qualityScore,
      knowledgeUsed: knowledgeUsed,
      webSearchUsed: webSearchUsed,
      model: model,
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
