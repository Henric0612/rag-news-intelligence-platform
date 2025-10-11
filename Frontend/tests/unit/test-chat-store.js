/**
 * 聊天Store单元测试
 * 测试用例ID: RAG-API-001 (前端Store层)
 * 对应测试计划: Sprint 2 - 数据与AI服务层
 * 测试描述: RAG问答功能、聊天历史管理、消息状态管理
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useChatStore } from '@/stores/chat'

// Mock API calls
vi.mock('@/api/rag', () => ({
  askQuestion: vi.fn()
}))

describe('聊天Store单元测试', () => {
  let chatStore

  beforeEach(() => {
    setActivePinia(createPinia())
    chatStore = useChatStore()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('问答功能', () => {
    it('应该成功发送问题并接收回答', async () => {
      const { askQuestion } = await import('@/api/rag')
      const mockResponse = {
        answer: '人工智能是计算机科学的一个分支...',
        sources: [
          { title: '人工智能概述', content: '相关内容...', relevance: 0.95 }
        ],
        response_time: 1500,
        quality_score: 0.92
      }
      
      askQuestion.mockResolvedValue(mockResponse)

      const question = '什么是人工智能？'
      await chatStore.sendMessage(question)

      // 验证API调用参数
      expect(askQuestion).toHaveBeenCalledWith(
        expect.objectContaining({
          query: question,
          top_k: 10,
          enable_rerank: true,
          enable_web_fallback: false,
          stream: false
        })
      )

      // 验证消息列表
      expect(chatStore.messages).toHaveLength(2) // 用户消息 + AI消息
      
      // 验证用户消息
      expect(chatStore.messages[0]).toMatchObject({
        type: 'user',
        content: question
      })
      
      // 验证AI消息
      expect(chatStore.messages[1]).toMatchObject({
        type: 'ai',
        content: mockResponse.answer,
        sources: mockResponse.sources
      })
    })

    it('应该处理问答失败', async () => {
      const { askQuestion } = await import('@/api/rag')
      const mockError = new Error('RAG服务不可用')
      askQuestion.mockRejectedValue(mockError)

      await expect(chatStore.sendMessage('测试问题')).rejects.toThrow('RAG服务不可用')
      
      // 验证加载状态已重置
      expect(chatStore.loading).toBe(false)
      
      // 验证添加了错误消息
      expect(chatStore.messages).toHaveLength(2) // 用户消息 + 错误消息
      expect(chatStore.messages[1]).toMatchObject({
        type: 'ai',
        error: true
      })
    })

    it('应该更新加载状态', async () => {
      const { askQuestion } = await import('@/api/rag')
      askQuestion.mockImplementation(() => 
        new Promise(resolve => 
          setTimeout(() => resolve({ answer: '测试回答', sources: [] }), 100)
        )
      )

      const sendPromise = chatStore.sendMessage('测试')
      expect(chatStore.loading).toBe(true)

      await sendPromise
      expect(chatStore.loading).toBe(false)
    })

    it('应该处理空问题', async () => {
      await expect(chatStore.sendMessage('')).rejects.toThrow('消息内容不能为空')
      await expect(chatStore.sendMessage('   ')).rejects.toThrow('消息内容不能为空')
    })
  })

  describe('聊天历史管理', () => {
    it('应该添加用户消息', () => {
      const message = '这是一条测试消息'
      chatStore.addUserMessage(message)

      expect(chatStore.messages).toHaveLength(1)
      expect(chatStore.messages[0]).toMatchObject({
        type: 'user',
        content: message
      })
      expect(chatStore.messages[0].timestamp).toBeInstanceOf(Date)
    })

    it('应该添加AI消息', () => {
      const aiMessage = {
        type: 'ai',
        content: '这是AI的回答',
        sources: [
          { title: '上下文', content: '相关内容', relevance: 0.9 }
        ],
        timestamp: new Date()
      }
      
      chatStore.addAIMessage(aiMessage)

      expect(chatStore.messages).toHaveLength(1)
      expect(chatStore.messages[0]).toMatchObject({
        type: 'ai',
        content: aiMessage.content,
        sources: aiMessage.sources
      })
    })

    it('应该清空聊天历史', () => {
      chatStore.addUserMessage('消息1')
      chatStore.addAIMessage({ type: 'ai', content: '回答1', timestamp: new Date() })
      chatStore.addUserMessage('消息2')

      expect(chatStore.messages).toHaveLength(3)

      chatStore.clearMessages()

      expect(chatStore.messages).toEqual([])
    })

    it('应该获取聊天消息列表', () => {
      chatStore.addUserMessage('问题1')
      chatStore.addAIMessage({ type: 'ai', content: '回答1', timestamp: new Date() })
      chatStore.addUserMessage('问题2')

      const messages = chatStore.messages

      expect(messages).toHaveLength(3)
      expect(messages[0].type).toBe('user')
      expect(messages[1].type).toBe('ai')
      expect(messages[2].type).toBe('user')
    })

    it('应该删除指定消息', () => {
      chatStore.addUserMessage('消息1')
      chatStore.addUserMessage('消息2')
      chatStore.addUserMessage('消息3')

      chatStore.removeMessage(1)

      expect(chatStore.messages).toHaveLength(2)
      expect(chatStore.messages[0].content).toBe('消息1')
      expect(chatStore.messages[1].content).toBe('消息3')
    })
  })

  describe('聊天统计', () => {
    it('应该更新消息统计', () => {
      expect(chatStore.chatStats.total_messages).toBe(0)

      chatStore.addUserMessage('测试消息')

      expect(chatStore.chatStats.total_messages).toBe(1)
      expect(chatStore.chatStats.last_activity).toBeInstanceOf(Date)
    })

    it('应该计算平均响应时间', () => {
      chatStore.addAIMessage({
        type: 'ai',
        content: '回答1',
        responseTime: 1000,
        timestamp: new Date()
      })
      
      chatStore.addAIMessage({
        type: 'ai',
        content: '回答2',
        responseTime: 2000,
        timestamp: new Date()
      })

      expect(chatStore.chatStats.avg_response_time).toBe(1500)
    })
  })

  describe('聊天配置', () => {
    it('应该更新聊天配置', () => {
      const newConfig = {
        top_k: 20,
        temperature: 0.9
      }

      chatStore.updateChatConfig(newConfig)

      expect(chatStore.chatConfig.top_k).toBe(20)
      expect(chatStore.chatConfig.temperature).toBe(0.9)
      // 其他配置应该保持不变
      expect(chatStore.chatConfig.enable_rerank).toBe(true)
    })

    it('应该重置聊天状态', () => {
      chatStore.addUserMessage('测试')
      chatStore.loading = true
      chatStore.streaming = true

      chatStore.resetChatState()

      expect(chatStore.messages).toEqual([])
      expect(chatStore.loading).toBe(false)
      expect(chatStore.streaming).toBe(false)
    })
  })

  describe('消息导出功能', () => {
    beforeEach(() => {
      chatStore.addUserMessage('问题1')
      chatStore.addAIMessage({
        type: 'ai',
        content: '回答1',
        timestamp: new Date()
      })
      chatStore.addUserMessage('问题2')
      chatStore.addAIMessage({
        type: 'ai',
        content: '回答2',
        timestamp: new Date()
      })
    })

    it('应该导出聊天记录为文本', () => {
      const exportedText = chatStore.exportChatHistory('txt')

      expect(exportedText).toContain('用户: 问题1')
      expect(exportedText).toContain('AI: 回答1')
      expect(exportedText).toContain('用户: 问题2')
      expect(exportedText).toContain('AI: 回答2')
    })

    it('应该导出聊天记录为JSON', () => {
      const exportedJSON = chatStore.exportChatHistory('json')
      const parsed = JSON.parse(exportedJSON)

      expect(Array.isArray(parsed)).toBe(true)
      expect(parsed).toHaveLength(4)
      expect(parsed[0].type).toBe('user')
      expect(parsed[1].type).toBe('ai')
    })
  })

  describe('Getters', () => {
    beforeEach(() => {
      chatStore.addUserMessage('问题1')
      chatStore.addAIMessage({
        type: 'ai',
        content: '回答1',
        timestamp: new Date()
      })
      chatStore.addUserMessage('问题2')
    })

    it('应该获取最后一条消息', () => {
      const lastMessage = chatStore.lastMessage

      expect(lastMessage.type).toBe('user')
      expect(lastMessage.content).toBe('问题2')
    })

    it('应该获取用户消息数量', () => {
      expect(chatStore.userMessageCount).toBe(2)
    })

    it('应该获取AI消息数量', () => {
      expect(chatStore.aiMessageCount).toBe(1)
    })

    it('应该检查是否正在聊天', () => {
      expect(chatStore.isChatting).toBe(false)

      chatStore.loading = true
      expect(chatStore.isChatting).toBe(true)

      chatStore.loading = false
      chatStore.streaming = true
      expect(chatStore.isChatting).toBe(true)
    })

    it('应该检查是否有消息', () => {
      expect(chatStore.hasMessages).toBe(true)

      chatStore.clearMessages()
      expect(chatStore.hasMessages).toBe(false)
    })
  })
})
