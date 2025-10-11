import request from './request'

// RAG问答 - 使用更长的超时时间因为需要LLM生成
export const askQuestion = (data) => {
  return request.post('/api/rag/ask', data, {
    timeout: 120000 // 120秒超时，LLM生成需要更长时间
  })
}

// 流式问答
export const streamAnswer = (data) => {
  return request.post('/api/rag/ask', data, {
    headers: {
      'Accept': 'text/plain'
    }
  })
}

// 构建上下文
export const buildContext = (data) => {
  return request.post('/api/rag/context', data)
}

// 向量检索
export const vectorSearch = (data) => {
  return request.post('/api/rag/vector-search', data)
}

// LLM生成
export const generateAnswer = (data) => {
  return request.post('/api/rag/generate', data)
}

// 响应验证
export const validateResponse = (data) => {
  return request.post('/api/rag/validate', data)
}

// 获取RAG统计
export const getRAGStats = () => {
  return request.get('/api/rag/stats')
}

// RAG服务健康检查
export const ragHealthCheck = (deepCheck = false) => {
  // 添加时间戳防止缓存
  const timestamp = new Date().getTime()
  return request.get('/api/rag/health', {
    params: {
      t: timestamp,
      deep_check: deepCheck
    }
  })
}

// 测试RAG流程
export const testRAGPipeline = (data) => {
  return request.post('/api/rag/test', data)
}
