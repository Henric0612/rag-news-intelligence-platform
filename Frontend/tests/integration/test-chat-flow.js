/**
 * 问答流程集成测试
 * 测试用例ID: FRONT-INT-002
 * 对应测试计划: Sprint 3 - 应用功能层
 * 测试描述: 聊天Store + Mock API集成测试
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useChatStore } from '@/stores/chat'

import { controlledSSE, mockSSEAnswer, installSSEFetch, requestPayload } from '../helpers/sse'

describe('问答流程集成测试', () => {
  let pinia
  let chatStore

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    chatStore = useChatStore()
    installSSEFetch()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('完整问答流程', () => {
    it('应该完成从提问到回答的完整流程', async () => {
      const mockResponse = {
        answer: '人工智能是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。',
        sources: [
          { title: 'AI基础', content: '相关内容1', score: 0.9 },
          { title: 'AI应用', content: '相关内容2', score: 0.8 }
        ],
        response_time: 2500
      }
      mockSSEAnswer(mockResponse)

      // 发送问题
      await chatStore.sendMessage('什么是人工智能？')

      // 验证API被调用（包含配置参数）
      expect(requestPayload()).toEqual(
        expect.objectContaining({
          query: '什么是人工智能？'
        })
      )

      // 验证消息被添加到Store
      expect(chatStore.messages.length).toBe(2) // 用户消息 + AI回答
      expect(chatStore.messages[0].type).toBe('user')
      expect(chatStore.messages[0].content).toBe('什么是人工智能？')
      expect(chatStore.messages[1].type).toBe('ai')
      expect(chatStore.messages[1].content).toBe(mockResponse.answer)
      expect(chatStore.messages[1].sources).toEqual(mockResponse.sources)
    })

    it('应该处理连续对话', async () => {
      mockSSEAnswer({
        answer: '回答内容',
        sources: [],
        response_time: 1000
      })

      // 发送多个问题
      await chatStore.sendMessage('问题1')
      await chatStore.sendMessage('问题2')
      await chatStore.sendMessage('问题3')

      // 验证所有消息都被记录
      expect(chatStore.messages.length).toBe(6) // 3个用户消息 + 3个AI回答
      expect(chatStore.userMessageCount).toBe(3)
      expect(chatStore.aiMessageCount).toBe(3)
      expect(fetch).toHaveBeenCalledTimes(3)
    })

    it('应该正确保存检索来源', async () => {
      const mockSources = [
        { title: '文档1', content: '内容1', score: 0.95 },
        { title: '文档2', content: '内容2', score: 0.85 },
        { title: '文档3', content: '内容3', score: 0.75 }
      ]
      mockSSEAnswer({
        answer: 'AI回答',
        sources: mockSources,
        response_time: 2000
      })

      await chatStore.sendMessage('测试问题')

      // 验证来源被保存
      const aiMessage = chatStore.messages.find(m => m.type === 'ai')
      expect(aiMessage.sources).toEqual(mockSources)
      expect(aiMessage.sources.length).toBe(3)
    })
  })

  describe('问答错误处理', () => {
    it('应该处理API错误', async () => {
      fetch.mockRejectedValue(new Error('网络错误'))

      // 发送问题并期望抛出错误
      await expect(chatStore.sendMessage('测试问题')).rejects.toThrow()

      // 验证加载状态被重置
      expect(chatStore.loading).toBe(false)
    })

    it('应该处理空问题', async () => {
      // 发送空问题
      await expect(chatStore.sendMessage('')).rejects.toThrow('消息内容不能为空')
      await expect(chatStore.sendMessage('   ')).rejects.toThrow('消息内容不能为空')
    })

    it('应该消费 SSE error 事件并结束消息状态', async () => {
      const stream = controlledSSE()
      stream.event({ type: 'error', code: 'AI_DEPENDENCY_UNAVAILABLE', message: 'AI服务暂时不可用' })
      stream.close()
      fetch.mockResolvedValue(stream.response)

      const message = await chatStore.sendMessage('测试')
      expect(message).toMatchObject({ type: 'ai', error: true, content: 'AI服务暂时不可用', thinking: false, isStreaming: false })
      expect(chatStore.messages).toHaveLength(2)
      expect(chatStore.streaming).toBe(false)
      expect(chatStore.loading).toBe(false)
    })
  })

  describe('聊天状态管理', () => {
    it('应该正确管理加载状态', async () => {
      const stream = controlledSSE()
      fetch.mockResolvedValue(stream.response)
      const sendPromise = chatStore.sendMessage('测试问题')
      // Attach a consumer immediately, even if an intermediate assertion fails.
      const outcome = sendPromise.then(value => ({ value }), error => ({ error }))
      try {
        expect(chatStore.loading).toBe(false)
        expect(chatStore.streaming).toBe(true)
        expect(chatStore.isChatting).toBe(true)
        expect(chatStore.lastMessage.thinking).toBe(true)
        stream.event({ type: 'thinking', stage: 'generation' })
        await vi.waitFor(() => expect(chatStore.lastMessage.thinkingStage).toBe('generation'))
        stream.write('data: {"type":"content","data":"第一')
        await Promise.resolve()
        expect(chatStore.lastMessage.content).toBe('')
        stream.write('块"}\n\n')
        await vi.waitFor(() => expect(chatStore.lastMessage.content).toBe('第一块'))
        expect(chatStore.lastMessage.thinking).toBe(false)
        expect(chatStore.lastMessage.isStreaming).toBe(true)
        stream.event({ type: 'sources', data: { sources: [{ title: '来源' }], model: 'qwen3:8b' } })
        stream.event({ type: 'content', data: '第二块' })
        await vi.waitFor(() => expect(chatStore.lastMessage.sources).toEqual([{ title: '来源' }]))
        stream.event({ type: 'done', stats: { response_time: 1.25 } })
        await vi.waitFor(() => expect(chatStore.lastMessage.isStreaming).toBe(false))
        expect(chatStore.lastMessage.content).toBe('第一块第二块')
        expect(chatStore.lastMessage.responseTime).toBe(1250)
      } finally {
        stream.close()
        await outcome
      }
      expect((await outcome).error).toBeUndefined()
      expect(chatStore.loading).toBe(false)
      expect(chatStore.streaming).toBe(false)
      expect(chatStore.isChatting).toBe(false)
    })

    it('应该在错误时重置加载状态', async () => {
      fetch.mockRejectedValue(new Error('错误'))

      // 发送消息
      await expect(chatStore.sendMessage('测试')).rejects.toThrow('错误')
      expect(chatStore.streaming).toBe(false)
      expect(chatStore.lastMessage.error).toBe(true)

      // 验证加载状态被重置
      expect(chatStore.loading).toBe(false)
    })

    it('应该支持清空聊天', async () => {
      mockSSEAnswer({
        answer: '回答',
        sources: [],
        response_time: 1000
      })

      // 添加一些消息
      await chatStore.sendMessage('问题1')
      await chatStore.sendMessage('问题2')
      expect(chatStore.messages.length).toBeGreaterThan(0)

      // 清空聊天
      chatStore.clearMessages()

      // 验证消息被清空
      expect(chatStore.messages.length).toBe(0)
      expect(chatStore.hasMessages).toBe(false)
    })
  })

  describe('消息管理', () => {
    it('应该能够删除单条消息', async () => {
      mockSSEAnswer({
        answer: '回答',
        sources: [],
        response_time: 1000
      })

      await chatStore.sendMessage('测试问题')
      const messageCount = chatStore.messages.length

      // 删除第一条消息
      chatStore.removeMessage(0)

      // 验证消息被删除
      expect(chatStore.messages.length).toBe(messageCount - 1)
    })

    it('应该正确统计消息数量', async () => {
      mockSSEAnswer({
        answer: '回答',
        sources: [],
        response_time: 1000
      })

      await chatStore.sendMessage('问题1')
      await chatStore.sendMessage('问题2')

      // 验证统计
      expect(chatStore.userMessageCount).toBe(2)
      expect(chatStore.aiMessageCount).toBe(2)
      expect(chatStore.messages.length).toBe(4)
    })

    it('应该能够获取最后一条消息', async () => {
      mockSSEAnswer({
        answer: '最新回答',
        sources: [],
        response_time: 1000
      })

      await chatStore.sendMessage('最新问题')

      // 验证最后一条消息
      expect(chatStore.lastMessage.type).toBe('ai')
      expect(chatStore.lastMessage.content).toBe('最新回答')
    })
  })

  describe('聊天配置', () => {
    it('应该能够更新聊天配置', () => {
      const newConfig = {
        top_k: 5,
        enable_rerank: false,
        enable_web_fallback: true
      }

      chatStore.updateChatConfig(newConfig)

      expect(chatStore.chatConfig.top_k).toBe(5)
      expect(chatStore.chatConfig.enable_rerank).toBe(false)
      expect(chatStore.chatConfig.enable_web_fallback).toBe(true)
    })

    it('应该使用更新后的配置发送消息', async () => {
      mockSSEAnswer({
        answer: '回答',
        sources: [],
        response_time: 1000
      })

      // 更新配置
      chatStore.updateChatConfig({ top_k: 5 })

      // 发送消息
      await chatStore.sendMessage('测试')

      // 验证API调用包含新配置
      expect(requestPayload()).toEqual(
        expect.objectContaining({ top_k: 5 })
      )
    })
  })

  describe('聊天历史导出', () => {
    it('应该能够导出聊天历史', async () => {
      mockSSEAnswer({
        answer: '回答',
        sources: [],
        response_time: 1000
      })

      await chatStore.sendMessage('测试问题')

      // 导出为文本
      const textExport = chatStore.exportChatHistory('txt')
      expect(textExport).toBeDefined()
      expect(textExport).toContain('测试问题')
      expect(textExport).toContain('回答')

      // 导出为JSON
      const jsonExport = chatStore.exportChatHistory('json')
      expect(jsonExport).toBeDefined()
      const parsed = JSON.parse(jsonExport)
      expect(Array.isArray(parsed)).toBe(true)
      expect(parsed.length).toBe(2)
    })
  })
})
