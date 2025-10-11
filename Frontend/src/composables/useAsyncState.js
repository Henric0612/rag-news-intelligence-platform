import { ref } from 'vue'

/**
 * 异步状态管理 Composable
 * 统一处理加载状态、错误状态和异步操作
 */
export function useAsyncState() {
  const loading = ref(false)
  const error = ref(null)
  
  /**
   * 执行异步操作
   * @param {Function} asyncFn - 异步函数
   * @returns {Promise} 异步操作结果
   */
  const execute = async (asyncFn) => {
    loading.value = true
    error.value = null
    
    try {
      const result = await asyncFn()
      return result
    } catch (e) {
      error.value = e
      throw e
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 重置状态
   */
  const reset = () => {
    loading.value = false
    error.value = null
  }
  
  return {
    loading,
    error,
    execute,
    reset
  }
}

