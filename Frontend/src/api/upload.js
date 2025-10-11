/**
 * 文件上传相关API
 */
import request from './request'

export const uploadAPI = {
  // 单文件上传
  uploadFile(data) {
    return request({
      url: '/api/upload/file',
      method: 'post',
      data,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 批量文件上传
  uploadFiles(data) {
    return request({
      url: '/api/upload/files',
      method: 'post',
      data,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 文件验证
  validateFile(data) {
    return request({
      url: '/api/upload/validate',
      method: 'post',
      data,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 获取已上传文件列表
  getUploadedFiles() {
    return request({
      url: '/api/upload/files',
      method: 'get'
    })
  },

  // 删除上传的文件
  deleteFile(filename) {
    return request({
      url: `/api/upload/files/${filename}`,
      method: 'delete'
    })
  },

  // 获取支持的文件格式
  getSupportedFormats() {
    return request({
      url: '/api/upload/supported-formats',
      method: 'get'
    })
  },

  // 文本分块
  chunkText(data) {
    return request({
      url: '/api/upload/chunk',
      method: 'post',
      data
    })
  },

  // 内容提取
  extractContent(data) {
    return request({
      url: '/api/upload/extract',
      method: 'post',
      data,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 批量处理数据
  batchProcessData(data) {
    return request({
      url: '/api/upload/batch-process',
      method: 'post',
      data
    })
  },

  // 导出数据
  exportData(params = {}) {
    return request({
      url: '/api/upload/export',
      method: 'get',
      params
    })
  }
}
