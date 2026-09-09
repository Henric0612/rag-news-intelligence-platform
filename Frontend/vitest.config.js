import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(({ mode }) => ({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.js'],
    include: mode === 'ci'
      ? ['tests/{unit,integration}/**/test-*.js']
      : ['tests/{unit,integration,security,performance}/**/test-*.js'],
    exclude: [
      'tests/e2e/**',
      'tests/helpers/**',
      'tests/setup.js',
      'tests/**/__init__.js',
      'tests/run-all-tests.js',
      'tests/test-*.js' // 排除旧的测试脚本
    ],
    testTimeout: 30000, // 增加测试超时时间到30秒
    // 使用默认reporter，避免重复输出
    reporters: mode === 'ci' ? ['default', 'junit'] : ['default'],
    outputFile: { junit: './coverage/junit.xml' },
    dangerouslyIgnoreUnhandledErrors: false,
    coverage: {
      provider: 'v8',
      all: true,
      include: ['src/**'],
      exclude: [],
      clean: true,
      reportsDirectory: './coverage',
      reporter: ['text', 'lcov'],
      reportOnFailure: true
    },
    // 失败时显示完整的diff
    outputDiffLines: 20,
    // 静默模式配置
    silent: false,
    // 隐藏控制台输出中的重复信息
    hideSkippedTests: true,
    // 只在失败时显示详细信息
    onConsoleLog(log, type) {
      // 过滤掉重复的日志
      if (log.includes('✓ 用户登录端到端流程')) {
        return false
      }
      return true
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  }
}))
