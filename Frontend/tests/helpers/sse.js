import { vi } from 'vitest'

// A real byte stream with explicitly controlled SSE frames and transport boundaries.
export function controlledSSE() {
  let controller
  const encoder = new TextEncoder()
  const body = new ReadableStream({ start(value) { controller = value } })
  return {
    response: { ok: true, status: 200, body },
    write(text) { controller.enqueue(encoder.encode(text)) },
    event(event) { this.write(`data: ${JSON.stringify(event)}\n\n`) },
    close() { controller.close() }
  }
}

export function answerSSE({ answer, sources = [], response_time = 0 }) {
  const stream = controlledSSE()
  stream.event({ type: 'thinking', stage: 'retrieval' })
  stream.event({ type: 'sources', data: { sources, model: 'qwen3:8b', knowledge_used: true, web_search_used: false } })
  const middle = Math.ceil(answer.length / 2)
  stream.event({ type: 'content', data: answer.slice(0, middle) })
  stream.event({ type: 'content', data: answer.slice(middle) })
  stream.event({ type: 'done', stats: { response_time: response_time / 1000 } })
  stream.close()
  return stream.response
}

export function mockSSEAnswer(answer) {
  // Each request needs its own unread stream, including consecutive conversations.
  fetch.mockImplementation(() => Promise.resolve(answerSSE(answer)))
}

export function installSSEFetch() {
  localStorage.setItem('token', 'c1-test-token')
  vi.stubGlobal('fetch', vi.fn(() => {
    throw new Error('Unexpected fetch: configure the SSE fixture explicitly')
  }))
}

export function requestPayload(call = 0) {
  return JSON.parse(fetch.mock.calls[call][1].body)
}
