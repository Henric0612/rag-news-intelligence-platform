/**
 * 测试环境设置
 */
import { beforeEach, afterEach, vi } from 'vitest'

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

const activeTimers = new Map()
for (const [setName, clearName] of [['setTimeout', 'clearTimeout'], ['setInterval', 'clearInterval']]) {
  const schedule = globalThis[setName].bind(globalThis)
  const cancel = globalThis[clearName].bind(globalThis)
  globalThis[setName] = (callback, delay, ...args) => {
    const id = schedule(callback, delay, ...args)
    activeTimers.set(id, cancel)
    return id
  }
}

// Restore implementations and storage objects, including tests replacing methods directly.
const storageMethods = storage => Object.fromEntries(
  ['getItem', 'setItem', 'removeItem', 'clear'].map(key => [key, storage[key].getMockImplementation()])
)
const localMethods = storageMethods(localStorageMock)
const sessionMethods = storageMethods(sessionStorageMock)

beforeEach(() => {
  vi.resetAllMocks()
  for (const [key, fn] of Object.entries(localMethods)) localStorageMock[key] = vi.fn(fn)
  for (const [key, fn] of Object.entries(sessionMethods)) sessionStorageMock[key] = vi.fn(fn)
  localStorageMock._data = {}
  sessionStorageMock._data = {}
  global.localStorage = localStorageMock
  global.sessionStorage = sessionStorageMock
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
  // Dispose real timers created by stores; fake timers are handled by Vitest.
  for (const [id, clear] of activeTimers) clear(id)
  activeTimers.clear()
  vi.clearAllTimers()
  vi.useRealTimers()
  localStorageMock._data = {}
  sessionStorageMock._data = {}
})
