import request from './request'

// 获取知识库列表
export const getKnowledgeList = (params = {}) => {
  // 转换分页参数名称
  const queryParams = { ...params }
  if (queryParams.page_size) {
    queryParams.size = queryParams.page_size
    delete queryParams.page_size
  }
  return request.get('/api/knowledge', { params: queryParams })
}

// 获取知识库详情
export const getKnowledgeDetail = (id) => {
  return request.get(`/api/knowledge/${id}`)
}

// 创建知识库条目
export const createKnowledge = (data) => {
  return request.post('/api/knowledge', data)
}

// 更新知识库条目
export const updateKnowledge = (id, data) => {
  return request.put(`/api/knowledge/${id}`, data)
}

// 删除知识库条目
export const deleteKnowledge = (id) => {
  return request.delete(`/api/knowledge/${id}`)
}

// 批量删除知识库条目
export const batchDeleteKnowledge = (ids) => {
  return request.delete('/api/knowledge/batch', { data: { ids } })
}

// 获取知识库统计
export const getKnowledgeStats = () => {
  return request.get('/api/knowledge/stats')
}

// 上传文件
export const uploadFile = (file, onProgress) => {
  const formData = new FormData()
  formData.append('file', file)
  
  return request.post('/api/knowledge/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        )
        onProgress(percentCompleted)
      }
    }
  })
}

// 单条目向量同步
export const syncVectorForItem = (id, forceResync = false) => {
  return request.post(`/api/knowledge/${id}/sync-vector`, { force_resync: forceResync })
}

// 批量向量同步
export const batchSyncVectors = (data) => {
  return request.post('/api/knowledge/batch-sync', data)
}