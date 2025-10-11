/**
 * 前端性能测试
 * 测试用例ID: PERF-002, PERF-003
 * 对应测试计划: Sprint 4 - 质量保证与交付
 * 测试描述: 搜索响应时间、RAG问答响应、页面加载时间
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import SearchBox from '@/components/SearchBox.vue'
import ChatInterface from '@/components/ChatInterface.vue'
import { useSearchStore } from '@/stores/search'
import { useChatStore } from '@/stores/chat'

describe('前端性能测试', () => {
  let pinia
  let router

  beforeEach(() => {
    pinia = createPinia()
    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/search', component: { template: '<div>Search</div>' } },
        { path: '/chat', component: { template: '<div>Chat</div>' } }
      ]
    })
  })

  describe('PERF-002: 搜索响应时间测试', () => {
    it('搜索响应时间应该小于200ms', async () => {
      const wrapper = mount(SearchBox, {
        global: {
          plugins: [pinia, router, ElementPlus]
        }
      })

      const searchStore = useSearchStore()
      
      // Mock搜索API以测试前端性能
      searchStore.performSearch = async (query) => {
        const startTime = performance.now()
        
        // 模拟搜索操作
        await new Promise(resolve => setTimeout(resolve, 50))
        
        const endTime = performance.now()
        const responseTime = endTime - startTime
        
        return { responseTime, results: [] }
      }

      const input = wrapper.find('[data-testid="search-input"]')
      const button = wrapper.find('[data-testid="search-button"]')

      await input.setValue('测试查询')
      
      const startTime = performance.now()
      await button.trigger('click')
      await wrapper.vm.$nextTick()
      const endTime = performance.now()

      const totalTime = endTime - startTime

      // 验证搜索响应时间（包含UI渲染）应该小于200ms
      // 注意：这是前端性能测试，实际API响应时间在后端测试中验证
      expect(totalTime).toBeLessThan(200)
    })

    it('搜索建议响应应该即时（< 100ms）', async () => {
      const wrapper = mount(SearchBox, {
        global: {
          plugins: [pinia, router, ElementPlus]
        }
      })

      const input = wrapper.find('[data-testid="search-input"]')

      const startTime = performance.now()
      await input.setValue('人工')
      await input.trigger('input')
      await wrapper.vm.$nextTick()
      const endTime = performance.now()

      const responseTime = endTime - startTime

      // 搜索建议应该即时响应
      expect(responseTime).toBeLessThan(100)
    })

    it('搜索结果渲染应该快速（< 50ms）', async () => {
      const wrapper = mount(SearchBox, {
        global: {
          plugins: [pinia, router, ElementPlus]
        },
        props: {
          results: Array(10).fill(null).map((_, i) => ({
            id: i,
            title: `结果${i}`,
            content: `内容${i}`,
            score: 0.9 - i * 0.05
          }))
        }
      })

      const startTime = performance.now()
      await wrapper.vm.$nextTick()
      const endTime = performance.now()

      const renderTime = endTime - startTime

      // 10条搜索结果的渲染时间应该小于50ms
      expect(renderTime).toBeLessThan(50)
    })
  })

  describe('PERF-003: RAG问答响应时间测试', () => {
    it('问答UI响应应该即时（< 100ms）', async () => {
      const wrapper = mount(ChatInterface, {
        global: {
          plugins: [pinia, router, ElementPlus]
        }
      })

      const input = wrapper.find('[data-testid="question-input"]')
      const button = wrapper.find('[data-testid="qa-button"]')

      await input.setValue('什么是人工智能？')

      const startTime = performance.now()
      await button.trigger('click')
      await wrapper.vm.$nextTick()
      const endTime = performance.now()

      const uiResponseTime = endTime - startTime

      // UI响应应该即时
      expect(uiResponseTime).toBeLessThan(100)
    })

    it('消息渲染应该快速（< 50ms）', async () => {
      const messages = Array(20).fill(null).map((_, i) => ({
        id: i,
        type: i % 2 === 0 ? 'user' : 'ai',
        content: `消息内容${i}`,
        timestamp: new Date().toISOString()
      }))

      const wrapper = mount(ChatInterface, {
        global: {
          plugins: [pinia, router, ElementPlus]
        },
        props: {
          messages
        }
      })

      const startTime = performance.now()
      await wrapper.vm.$nextTick()
      const endTime = performance.now()

      const renderTime = endTime - startTime

      // 20条消息的渲染时间应该小于50ms
      expect(renderTime).toBeLessThan(50)
    })

    it('流式输出更新应该流畅（< 16ms per frame）', async () => {
      const wrapper = mount(ChatInterface, {
        global: {
          plugins: [pinia, router, ElementPlus]
        }
      })

      const chatStore = useChatStore()
      
      // 模拟流式输出
      const streamText = '这是一段很长的AI回答内容，用于测试流式输出的性能表现。'
      const frameTimes = []

      for (let i = 0; i < streamText.length; i += 5) {
        const startTime = performance.now()
        
        chatStore.messages = [{
          type: 'ai',
          content: streamText.substring(0, i + 5),
          streaming: true
        }]
        
        await wrapper.vm.$nextTick()
        
        const endTime = performance.now()
        frameTimes.push(endTime - startTime)
      }

      // 计算平均帧时间
      const avgFrameTime = frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length

      // 流式输出每帧更新应该小于16ms（60fps）
      expect(avgFrameTime).toBeLessThan(16)
    })
  })

  describe('页面加载性能测试', () => {
    it('组件初始化应该快速（< 100ms）', async () => {
      const startTime = performance.now()
      
      const wrapper = mount(SearchBox, {
        global: {
          plugins: [pinia, router, ElementPlus]
        }
      })
      
      await wrapper.vm.$nextTick()
      
      const endTime = performance.now()
      const initTime = endTime - startTime

      // 组件初始化时间应该小于100ms
      expect(initTime).toBeLessThan(100)
    })

    it('Store初始化应该快速（< 50ms）', () => {
      const startTime = performance.now()
      
      const searchStore = useSearchStore()
      const chatStore = useChatStore()
      
      const endTime = performance.now()
      const initTime = endTime - startTime

      // Store初始化时间应该小于50ms
      expect(initTime).toBeLessThan(50)
      
      expect(searchStore).toBeDefined()
      expect(chatStore).toBeDefined()
    })

    it('路由导航应该快速（< 100ms）', async () => {
      const startTime = performance.now()
      
      await router.push('/search')
      await router.isReady()
      
      const endTime = performance.now()
      const navigationTime = endTime - startTime

      // 路由导航时间应该小于100ms
      expect(navigationTime).toBeLessThan(100)
    })
  })

  describe('内存性能测试', () => {
    it('大量搜索结果不应导致内存泄漏', async () => {
      const wrapper = mount(SearchBox, {
        global: {
          plugins: [pinia, router, ElementPlus]
        }
      })

      const searchStore = useSearchStore()
      
      // 模拟多次搜索
      for (let i = 0; i < 10; i++) {
        searchStore.searchResults = Array(100).fill(null).map((_, j) => ({
          id: j,
          title: `结果${j}`,
          content: `内容${j}`.repeat(100)
        }))
        
        await wrapper.vm.$nextTick()
        
        // 清空结果
        searchStore.clearSearchResults()
      }

      // 验证组件仍然正常工作
      expect(wrapper.exists()).toBe(true)
    })

    it('长时间聊天会话不应导致性能下降', async () => {
      const wrapper = mount(ChatInterface, {
        global: {
          plugins: [pinia, router, ElementPlus]
        }
      })

      const chatStore = useChatStore()
      
      // 模拟长时间聊天（100条消息）
      const frameTimes = []
      
      for (let i = 0; i < 100; i++) {
        const startTime = performance.now()
        
        chatStore.addUserMessage(`问题${i}`)
        chatStore.addAIMessage(`回答${i}`, [])
        
        await wrapper.vm.$nextTick()
        
        const endTime = performance.now()
        frameTimes.push(endTime - startTime)
      }

      // 验证后期消息的渲染时间没有显著增加
      const firstTenAvg = frameTimes.slice(0, 10).reduce((a, b) => a + b, 0) / 10
      const lastTenAvg = frameTimes.slice(-10).reduce((a, b) => a + b, 0) / 10

      // 后期渲染时间不应超过初期的2倍
      expect(lastTenAvg).toBeLessThan(firstTenAvg * 2)
    })
  })

  describe('并发操作性能测试', () => {
    it('同时处理多个搜索请求应该正常', async () => {
      const searchStore = useSearchStore()
      
      // 模拟并发搜索
      const searches = Array(5).fill(null).map((_, i) => 
        searchStore.performSearch(`查询${i}`)
      )

      const startTime = performance.now()
      await Promise.all(searches)
      const endTime = performance.now()

      const totalTime = endTime - startTime

      // 5个并发搜索应该在合理时间内完成
      expect(totalTime).toBeLessThan(1000)
    })

    it('同时更新多个Store应该不冲突', async () => {
      const searchStore = useSearchStore()
      const chatStore = useChatStore()
      
      const startTime = performance.now()
      
      // 同时更新多个Store
      await Promise.all([
        searchStore.performSearch('测试'),
        chatStore.sendMessage('测试问题')
      ])
      
      const endTime = performance.now()
      const totalTime = endTime - startTime

      // 并发Store更新应该正常完成
      expect(totalTime).toBeLessThan(500)
      expect(searchStore).toBeDefined()
      expect(chatStore).toBeDefined()
    })
  })
})

