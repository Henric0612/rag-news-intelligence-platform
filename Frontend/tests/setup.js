/**
 * 测试环境设置
 */
import { vi } from 'vitest'

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn((key) => {
    return localStorageMock._data[key] || null
  }),
  setItem: vi.fn((key, value) => {
    localStorageMock._data[key] = String(value)
  }),
  removeItem: vi.fn((key) => {
    delete localStorageMock._data[key]
  }),
  clear: vi.fn(() => {
    localStorageMock._data = {}
  }),
  _data: {}
}
global.localStorage = localStorageMock

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn((key) => {
    return sessionStorageMock._data[key] || null
  }),
  setItem: vi.fn((key, value) => {
    sessionStorageMock._data[key] = String(value)
  }),
  removeItem: vi.fn((key) => {
    delete sessionStorageMock._data[key]
  }),
  clear: vi.fn(() => {
    sessionStorageMock._data = {}
  }),
  _data: {}
}
global.sessionStorage = sessionStorageMock

// 保留原始console方法，但过滤掉噪音
const originalConsole = { ...console }

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  log: vi.fn((...args) => {
    // 只在需要时输出到真实console
    if (process.env.DEBUG_TESTS) {
      originalConsole.log(...args)
    }
  }),
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn((...args) => {
    // 过滤掉特定的警告
    const message = args.join(' ')
    if (message.includes('AggregateError') || message.includes('jsdom')) {
      return
    }
    if (process.env.DEBUG_TESTS) {
      originalConsole.warn(...args)
    }
  }),
  error: vi.fn((...args) => {
    // 过滤掉网络错误
    const message = args.join(' ')
    if (message.includes('AggregateError') || 
        message.includes('ECONNREFUSED') ||
        message.includes('xhr-utils')) {
      return
    }
    if (process.env.DEBUG_TESTS) {
      originalConsole.error(...args)
    }
  })
}

// 抑制未处理的Promise rejection警告（在测试环境中）
process.on('unhandledRejection', (reason) => {
  // 忽略网络相关的rejection
  if (reason && (
    reason.message?.includes('AggregateError') ||
    reason.message?.includes('ECONNREFUSED') ||
    reason.code === 'ECONNREFUSED'
  )) {
    return
  }
  // 其他rejection仍然抛出
  if (process.env.DEBUG_TESTS) {
    originalConsole.error('Unhandled Rejection:', reason)
  }
})
