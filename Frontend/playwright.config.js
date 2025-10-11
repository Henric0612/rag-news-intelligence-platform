import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E 测试配置
 * 
 * 运行前确保：
 * 1. 后端服务运行: cd Backend && python app.py (http://localhost:5000)
 * 2. 前端服务运行: cd Frontend && npm run dev (http://localhost:5173)
 */

export default defineConfig({
  // 测试目录
  testDir: './tests/e2e',
  
  // 测试文件匹配模式
  testMatch: '**/*.spec.js',
  
  // 全局超时设置
  timeout: 60000, // 60秒
  
  // 断言超时
  expect: {
    timeout: 10000 // 10秒
  },
  
  // 失败重试次数
  retries: process.env.CI ? 2 : 0,
  
  // 并行执行配置
  workers: process.env.CI ? 1 : 1, // E2E测试建议串行执行
  
  // 报告配置
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report' }]
  ],
  
  // 全局配置
  use: {
    // 基础URL
    baseURL: 'http://localhost:3000',
    
    // 浏览器上下文选项
    trace: 'on-first-retry', // 失败时记录trace
    screenshot: 'only-on-failure', // 失败时截图
    video: 'retain-on-failure', // 失败时保留视频
    
    // 视口大小
    viewport: { width: 1280, height: 720 },
    
    // 忽略HTTPS错误
    ignoreHTTPSErrors: true,
    
    // 导航超时
    navigationTimeout: 30000,
    
    // 操作超时
    actionTimeout: 10000
  },

  // 测试项目配置
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    },
    
    // 可选：添加更多浏览器
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] }
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] }
    // }
  ],

  // Web服务器配置（可选）
  // 如果需要Playwright自动启动前端服务，取消注释以下配置
  // webServer: {
  //   command: 'npm run dev',
  //   port: 5173,
  //   timeout: 120000,
  //   reuseExistingServer: !process.env.CI
  // }
})

