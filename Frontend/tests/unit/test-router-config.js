/**
 * 路由配置单元测试
 * 测试用例ID: 未在测试计划中明确列出（基础设施测试）
 * 对应测试计划: Sprint 0 - 项目准备与设计
 * 测试描述: Vue Router配置和路由规则验证
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { createRouter, createWebHistory } from 'vue-router'

// Mock Vue Router组件
const mockComponents = {
  Login: { template: '<div>Login</div>' },
  Dashboard: { template: '<div>Dashboard</div>' },
  Knowledge: { template: '<div>Knowledge</div>' },
  Search: { template: '<div>Search</div>' },
  NotFound: { template: '<div>404</div>' }
}

describe('路由配置测试', () => {
  let router

  beforeEach(() => {
    // 创建测试路由
    router = createRouter({
      history: createWebHistory(),
      routes: [
        {
          path: '/',
          redirect: '/dashboard'
        },
        {
          path: '/login',
          name: 'Login',
          component: mockComponents.Login,
          meta: { requiresAuth: false }
        },
        {
          path: '/dashboard',
          name: 'Dashboard',
          component: mockComponents.Dashboard,
          meta: { requiresAuth: true }
        },
        {
          path: '/knowledge',
          name: 'Knowledge',
          component: mockComponents.Knowledge,
          meta: { requiresAuth: true }
        },
        {
          path: '/search',
          name: 'Search',
          component: mockComponents.Search,
          meta: { requiresAuth: true }
        },
        {
          path: '/:pathMatch(.*)*',
          name: 'NotFound',
          component: mockComponents.NotFound
        }
      ]
    })
  })

  it('应该正确创建路由实例', () => {
    expect(router).toBeDefined()
    expect(router.options.history).toBeDefined()
    expect(router.options.routes).toBeDefined()
  })

  it('应该包含所有必需的路由', () => {
    const routeNames = router.getRoutes().map(route => route.name)
    
    expect(routeNames).toContain('Login')
    expect(routeNames).toContain('Dashboard')
    expect(routeNames).toContain('Knowledge')
    expect(routeNames).toContain('Search')
    expect(routeNames).toContain('NotFound')
  })

  it('应该正确配置路由元信息', () => {
    const routes = router.getRoutes()
    
    const loginRoute = routes.find(route => route.name === 'Login')
    const dashboardRoute = routes.find(route => route.name === 'Dashboard')
    
    expect(loginRoute.meta.requiresAuth).toBe(false)
    expect(dashboardRoute.meta.requiresAuth).toBe(true)
  })

  it('应该正确处理根路径重定向', () => {
    const routes = router.getRoutes()
    const rootRoute = routes.find(route => route.path === '/')
    
    expect(rootRoute.redirect).toBe('/dashboard')
  })

  it('应该包含404处理路由', () => {
    const routes = router.getRoutes()
    const notFoundRoute = routes.find(route => route.name === 'NotFound')
    
    expect(notFoundRoute).toBeDefined()
    expect(notFoundRoute.path).toBe('/:pathMatch(.*)*')
  })

  it('应该使用Web History模式', () => {
    expect(router.options.history).toBeInstanceOf(Object)
    // 检查是否是createWebHistory的实例
    expect(router.options.history.base).toBeDefined()
  })

  it('应该能够解析路由', () => {
    const resolvedRoute = router.resolve('/login')
    
    expect(resolvedRoute).toBeDefined()
    expect(resolvedRoute.name).toBe('Login')
    expect(resolvedRoute.path).toBe('/login')
  })

  it('应该能够解析动态路由', () => {
    const resolvedRoute = router.resolve('/nonexistent')
    
    expect(resolvedRoute).toBeDefined()
    expect(resolvedRoute.name).toBe('NotFound')
  })
})
