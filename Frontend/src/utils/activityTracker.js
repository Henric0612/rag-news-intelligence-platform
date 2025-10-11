/**
 * 用户活动追踪工具
 * 用于记录用户活动时间，支持静默认证判断
 */

import { useAuthStore } from '@/stores/auth'

// 活动追踪配置
const ACTIVITY_CONFIG = {
  // 长时间未使用阈值（12小时）
  LONG_INACTIVE_THRESHOLD: 12 * 60 * 60 * 1000,
  // 超长时间未使用阈值（24小时）
  VERY_LONG_INACTIVE_THRESHOLD: 24 * 60 * 60 * 1000,
  // 活动追踪间隔（5分钟）
  TRACKING_INTERVAL: 5 * 60 * 1000
}

class ActivityTracker {
  constructor() {
    this.authStore = null
    this.trackingTimer = null
    this.isTracking = false
  }

  /**
   * 初始化活动追踪
   */
  init() {
    this.authStore = useAuthStore()
    this.startTracking()
    this.bindEvents()
  }

  /**
   * 开始活动追踪
   */
  startTracking() {
    if (this.isTracking) return
    
    this.isTracking = true
    
    // 立即更新一次活动时间
    this.updateActivity()
    
    // 定期更新活动时间（每5分钟）
    this.trackingTimer = setInterval(() => {
      this.updateActivity()
    }, ACTIVITY_CONFIG.TRACKING_INTERVAL)
    
    console.log('用户活动追踪已启动')
  }

  /**
   * 停止活动追踪
   */
  stopTracking() {
    if (this.trackingTimer) {
      clearInterval(this.trackingTimer)
      this.trackingTimer = null
    }
    this.isTracking = false
    console.log('用户活动追踪已停止')
  }

  /**
   * 更新活动时间
   */
  updateActivity() {
    if (this.authStore && this.authStore.isLoggedIn) {
      this.authStore.updateLastActivity()
    }
  }

  /**
   * 绑定用户活动事件
   */
  bindEvents() {
    // 鼠标移动事件
    document.addEventListener('mousemove', this.throttleActivity.bind(this))
    
    // 键盘事件
    document.addEventListener('keydown', this.throttleActivity.bind(this))
    
    // 点击事件
    document.addEventListener('click', this.throttleActivity.bind(this))
    
    // 滚动事件
    document.addEventListener('scroll', this.throttleActivity.bind(this))
    
    // 页面可见性变化
    document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this))
    
    // 页面卸载前保存活动时间
    window.addEventListener('beforeunload', this.updateActivity.bind(this))
  }

  /**
   * 节流处理活动事件
   */
  throttleActivity() {
    if (this.throttleTimer) return
    
    this.throttleTimer = setTimeout(() => {
      this.updateActivity()
      this.throttleTimer = null
    }, 1000) // 1秒内只更新一次
  }

  /**
   * 处理页面可见性变化
   */
  handleVisibilityChange() {
    if (document.visibilityState === 'visible') {
      // 页面重新可见时更新活动时间
      this.updateActivity()
    }
  }

  /**
   * 检查是否长时间未使用
   */
  isLongInactive() {
    if (!this.authStore || !this.authStore.lastActivity) return false
    
    const now = Date.now()
    const timeSinceLastActivity = now - this.authStore.lastActivity
    return timeSinceLastActivity > ACTIVITY_CONFIG.LONG_INACTIVE_THRESHOLD
  }

  /**
   * 检查是否超长时间未使用
   */
  isVeryLongInactive() {
    if (!this.authStore || !this.authStore.lastActivity) return false
    
    const now = Date.now()
    const timeSinceLastActivity = now - this.authStore.lastActivity
    return timeSinceLastActivity > ACTIVITY_CONFIG.VERY_LONG_INACTIVE_THRESHOLD
  }

  /**
   * 获取最后活动时间
   */
  getLastActivityTime() {
    return this.authStore?.lastActivity || null
  }

  /**
   * 获取距离最后活动的时间
   */
  getTimeSinceLastActivity() {
    if (!this.authStore || !this.authStore.lastActivity) return null
    
    return Date.now() - this.authStore.lastActivity
  }

  /**
   * 格式化时间间隔
   */
  formatTimeInterval(interval) {
    const seconds = Math.floor(interval / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)
    
    if (days > 0) return `${days}天前`
    if (hours > 0) return `${hours}小时前`
    if (minutes > 0) return `${minutes}分钟前`
    return `${seconds}秒前`
  }
}

// 创建全局实例
const activityTracker = new ActivityTracker()

export default activityTracker
export { ACTIVITY_CONFIG }
