/**
 * 全局错误处理工具
 */

import { ElMessage, ElNotification } from 'element-plus'

// 错误类型枚举
export const ErrorTypes = {
  NETWORK: 'NETWORK',
  API: 'API',
  VALIDATION: 'VALIDATION',
  AUTH: 'AUTH',
  PERMISSION: 'PERMISSION',
  UNKNOWN: 'UNKNOWN'
}

// 错误级别枚举
export const ErrorLevels = {
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
  CRITICAL: 'critical'
}

class ErrorHandler {
  constructor() {
    this.errorQueue = []
    this.maxQueueSize = 100
    this.isReporting = false
  }

  // 处理错误
  handle(error, context = {}) {
    const errorInfo = this.parseError(error, context)
    
    // 添加到错误队列
    this.addToQueue(errorInfo)
    
    // 显示错误消息
    this.showError(errorInfo)
    
    // 记录错误日志
    this.logError(errorInfo)
    
    // 上报错误（可选）
    this.reportError(errorInfo)
    
    return errorInfo
  }

  // 解析错误信息
  parseError(error, context = {}) {
    const errorInfo = {
      id: this.generateErrorId(),
      timestamp: new Date().toISOString(),
      type: this.getErrorType(error),
      level: this.getErrorLevel(error),
      message: this.getErrorMessage(error),
      stack: error?.stack || '',
      context,
      userAgent: navigator.userAgent,
      url: window.location.href
    }

    return errorInfo
  }

  // 获取错误类型
  getErrorType(error) {
    if (error?.code === 'NETWORK_ERROR' || error?.message?.includes('网络')) {
      return ErrorTypes.NETWORK
    }
    
    if (error?.response) {
      const status = error.response.status
      if (status === 401) return ErrorTypes.AUTH
      if (status === 403) return ErrorTypes.PERMISSION
      return ErrorTypes.API
    }
    
    if (error?.message?.includes('验证') || error?.message?.includes('格式')) {
      return ErrorTypes.VALIDATION
    }
    
    return ErrorTypes.UNKNOWN
  }

  // 获取错误级别
  getErrorLevel(error) {
    if (error?.response?.status >= 500) {
      return ErrorLevels.CRITICAL
    }
    
    if (error?.response?.status >= 400) {
      return ErrorLevels.ERROR
    }
    
    if (error?.message?.includes('警告') || error?.message?.includes('注意')) {
      return ErrorLevels.WARNING
    }
    
    return ErrorLevels.ERROR
  }

  // 获取错误消息
  getErrorMessage(error) {
    if (typeof error === 'string') {
      return error
    }
    
    if (error?.message) {
      return error.message
    }
    
    if (error?.response?.data?.message) {
      return error.response.data.message
    }
    
    if (error?.response?.statusText) {
      return error.response.statusText
    }
    
    return '未知错误'
  }

  // 生成错误ID
  generateErrorId() {
    return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  // 添加到错误队列
  addToQueue(errorInfo) {
    this.errorQueue.push(errorInfo)
    
    // 限制队列大小
    if (this.errorQueue.length > this.maxQueueSize) {
      this.errorQueue.shift()
    }
  }

  // 显示错误消息
  showError(errorInfo) {
    const { type, level, message } = errorInfo
    
    // 根据错误类型和级别选择显示方式
    if (level === ErrorLevels.CRITICAL) {
      ElNotification({
        title: '系统错误',
        message: message,
        type: 'error',
        duration: 0, // 不自动关闭
        showClose: true
      })
    } else if (level === ErrorLevels.ERROR) {
      ElMessage.error(message)
    } else if (level === ErrorLevels.WARNING) {
      ElMessage.warning(message)
    } else {
      ElMessage.info(message)
    }
  }

  // 记录错误日志
  logError(errorInfo) {
    const logMessage = `[${errorInfo.level.toUpperCase()}] ${errorInfo.type}: ${errorInfo.message}`
    
    if (errorInfo.level === ErrorLevels.CRITICAL || errorInfo.level === ErrorLevels.ERROR) {
      console.error(logMessage, errorInfo)
    } else if (errorInfo.level === ErrorLevels.WARNING) {
      console.warn(logMessage, errorInfo)
    } else {
      console.info(logMessage, errorInfo)
    }
  }

  // 上报错误（可集成第三方错误监控服务）
  async reportError(errorInfo) {
    // 只在生产环境上报
    if (import.meta.env.PROD && !this.isReporting) {
      this.isReporting = true
      
      try {
        // 这里可以集成 Sentry、LogRocket 等错误监控服务
        // await this.sendToErrorService(errorInfo)
        
        console.log('错误已上报:', errorInfo.id)
      } catch (error) {
        console.error('错误上报失败:', error)
      } finally {
        this.isReporting = false
      }
    }
  }

  // 获取错误统计
  getErrorStats() {
    const stats = {
      total: this.errorQueue.length,
      byType: {},
      byLevel: {},
      recent: this.errorQueue.slice(-10)
    }
    
    this.errorQueue.forEach(error => {
      stats.byType[error.type] = (stats.byType[error.type] || 0) + 1
      stats.byLevel[error.level] = (stats.byLevel[error.level] || 0) + 1
    })
    
    return stats
  }

  // 清空错误队列
  clearErrors() {
    this.errorQueue = []
  }

  // 导出错误日志
  exportErrors() {
    return JSON.stringify(this.errorQueue, null, 2)
  }
}

// 创建全局错误处理器实例
export const errorHandler = new ErrorHandler()

// 全局错误处理函数
export const handleError = (error, context = {}) => {
  return errorHandler.handle(error, context)
}

// Vue 错误处理器
export const setupVueErrorHandler = (app) => {
  app.config.errorHandler = (error, instance, info) => {
    handleError(error, {
      component: instance?.$options?.name || 'Unknown',
      info,
      type: 'VUE_COMPONENT_ERROR'
    })
  }
}

// 全局未捕获错误处理
export const setupGlobalErrorHandler = () => {
  // 捕获未处理的 Promise 错误
  window.addEventListener('unhandledrejection', (event) => {
    handleError(event.reason, {
      type: 'UNHANDLED_PROMISE_REJECTION',
      promise: event.promise
    })
  })

  // 捕获全局 JavaScript 错误
  window.addEventListener('error', (event) => {
    handleError(event.error, {
      type: 'GLOBAL_ERROR',
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno
    })
  })
}

export default errorHandler
