/**
 * API缓存工具
 */

class APICache {
  constructor(maxSize = 100, ttl = 5 * 60 * 1000) { // 默认5分钟过期
    this.cache = new Map()
    this.maxSize = maxSize
    this.ttl = ttl
  }

  // 生成缓存键
  generateKey(url, params = {}) {
    const sortedParams = Object.keys(params)
      .sort()
      .reduce((result, key) => {
        result[key] = params[key]
        return result
      }, {})
    
    return `${url}:${JSON.stringify(sortedParams)}`
  }

  // 获取缓存
  get(key) {
    const item = this.cache.get(key)
    
    if (!item) {
      return null
    }
    
    // 检查是否过期
    if (Date.now() - item.timestamp > this.ttl) {
      this.cache.delete(key)
      return null
    }
    
    return item.data
  }

  // 设置缓存
  set(key, data) {
    // 如果缓存已满，删除最旧的条目
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value
      this.cache.delete(firstKey)
    }
    
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    })
  }

  // 删除缓存
  delete(key) {
    return this.cache.delete(key)
  }

  // 清空缓存
  clear() {
    this.cache.clear()
  }

  // 获取缓存统计
  getStats() {
    return {
      size: this.cache.size,
      maxSize: this.maxSize,
      ttl: this.ttl
    }
  }
}

// 创建全局缓存实例
export const apiCache = new APICache()

// 缓存装饰器
export const withCache = (fn, cacheKey, ttl = 5 * 60 * 1000) => {
  return async (...args) => {
    const key = typeof cacheKey === 'function' ? cacheKey(...args) : cacheKey
    
    // 尝试从缓存获取
    const cached = apiCache.get(key)
    if (cached !== null) {
      console.log(`缓存命中: ${key}`)
      return cached
    }
    
    // 执行函数并缓存结果
    const result = await fn(...args)
    apiCache.set(key, result)
    
    console.log(`缓存存储: ${key}`)
    return result
  }
}

// 搜索API缓存
export const searchCache = {
  get: (query, options = {}) => {
    return apiCache.get(apiCache.generateKey('/api/search', { query, ...options }))
  },
  
  set: (query, data, options = {}) => {
    apiCache.set(apiCache.generateKey('/api/search', { query, ...options }), data)
  },
  
  clear: () => {
    // 清除所有搜索相关的缓存
    for (const [key] of apiCache.cache) {
      if (key.startsWith('/api/search:')) {
        apiCache.delete(key)
      }
    }
  }
}

// 用户信息缓存
export const userCache = {
  get: (userId) => {
    return apiCache.get(`/api/user/${userId}`)
  },
  
  set: (userId, data) => {
    apiCache.set(`/api/user/${userId}`, data)
  },
  
  clear: (userId) => {
    if (userId) {
      apiCache.delete(`/api/user/${userId}`)
    } else {
      // 清除所有用户缓存
      for (const [key] of apiCache.cache) {
        if (key.startsWith('/api/user/')) {
          apiCache.delete(key)
        }
      }
    }
  }
}

export default apiCache
