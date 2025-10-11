/**
 * 日期时间格式化工具
 * 
 * 业内最佳实践：
 * 1. 后端存储和传输使用UTC时间（ISO 8601格式）
 * 2. 前端根据用户时区显示本地时间
 * 3. 使用原生JavaScript Date API处理时区转换
 */

/**
 * 将UTC时间字符串转换为北京时间并格式化显示
 * @param {string|Date} dateInput - UTC时间字符串或Date对象
 * @param {object} options - 格式化选项
 * @returns {string} 格式化后的北京时间字符串
 */
export function formatToBeijingTime(dateInput, options = {}) {
  if (!dateInput) return 'N/A'
  
  try {
    // 将输入转换为Date对象
    const date = dateInput instanceof Date ? dateInput : new Date(dateInput)
    
    // 检查日期是否有效
    if (isNaN(date.getTime())) {
      console.warn('Invalid date input:', dateInput)
      return 'N/A'
    }
    
    // 默认格式化选项（北京时间 UTC+8）
    const defaultOptions = {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }
    
    const formatOptions = { ...defaultOptions, ...options }
    
    // 使用Intl.DateTimeFormat进行格式化（支持时区转换）
    return new Intl.DateTimeFormat('zh-CN', formatOptions).format(date)
  } catch (error) {
    console.error('Date formatting error:', error, dateInput)
    return 'N/A'
  }
}

/**
 * 格式化为简短的日期时间（不含秒）
 * @param {string|Date} dateInput - UTC时间字符串或Date对象
 * @returns {string} 格式化后的北京时间字符串
 */
export function formatToBeijingTimeShort(dateInput) {
  return formatToBeijingTime(dateInput, {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

/**
 * 格式化为仅日期（不含时间）
 * @param {string|Date} dateInput - UTC时间字符串或Date对象
 * @returns {string} 格式化后的日期字符串
 */
export function formatToBeijingDate(dateInput) {
  return formatToBeijingTime(dateInput, {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

/**
 * 格式化为相对时间（如：5分钟前、2小时前）
 * @param {string|Date} dateInput - UTC时间字符串或Date对象
 * @returns {string} 相对时间字符串
 */
export function formatRelativeTime(dateInput) {
  if (!dateInput) return 'N/A'
  
  try {
    const date = dateInput instanceof Date ? dateInput : new Date(dateInput)
    if (isNaN(date.getTime())) return 'N/A'
    
    const now = new Date()
    const diffMs = now - date
    const diffSeconds = Math.floor(diffMs / 1000)
    const diffMinutes = Math.floor(diffSeconds / 60)
    const diffHours = Math.floor(diffMinutes / 60)
    const diffDays = Math.floor(diffHours / 24)
    
    if (diffSeconds < 60) {
      return '刚刚'
    } else if (diffMinutes < 60) {
      return `${diffMinutes}分钟前`
    } else if (diffHours < 24) {
      return `${diffHours}小时前`
    } else if (diffDays < 7) {
      return `${diffDays}天前`
    } else {
      // 超过7天显示完整日期
      return formatToBeijingTime(date)
    }
  } catch (error) {
    console.error('Relative time formatting error:', error, dateInput)
    return 'N/A'
  }
}

/**
 * 获取当前北京时间
 * @returns {Date} 当前时间的Date对象
 */
export function getCurrentBeijingTime() {
  return new Date()
}

/**
 * 将北京时间转换为UTC ISO字符串（用于发送到后端）
 * @param {Date} date - 本地时间Date对象
 * @returns {string} UTC ISO格式字符串
 */
export function toUTCString(date) {
  if (!date) return null
  return date.toISOString()
}

// 导出默认格式化函数
export default formatToBeijingTime

