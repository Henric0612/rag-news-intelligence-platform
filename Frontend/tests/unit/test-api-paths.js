import { describe, it, expect, vi } from 'vitest'

// Keep Axios and the auth API module real; only the transport adapter is controlled.
vi.mock('element-plus', () => ({ ElMessage: { error: vi.fn() } }))

describe('实际 Axios client 的 API URL 契约', () => {
  it.each([
    ['', '/api/auth/login'],
    ['https://api.example.test', 'https://api.example.test/api/auth/login'],
    ['https://api.example.test/base/', 'https://api.example.test/base/api/auth/login']
  ])('base=%s 保留恰好一个 /api', async (base, expectedURL) => {
    vi.stubEnv('VITE_API_BASE_URL', base)
    vi.resetModules()
    const { default: request } = await import('@/api/request')
    const { login } = await import('@/api/auth')
    let actualURL
    request.defaults.adapter = vi.fn(async config => {
      actualURL = request.getUri(config)
      expect(config.method).toBe('post')
      expect(JSON.parse(config.data)).toEqual({ username: 'test', password: 'test-password' })
      return { data: { success: true, code: 200, data: { token: 'ok' } }, status: 200, statusText: 'OK', headers: {}, config }
    })

    await expect(login({ username: 'test', password: 'test-password' })).resolves.toEqual({ token: 'ok' })
    expect(request.defaults.adapter).toHaveBeenCalledOnce()
    expect(actualURL).toBe(expectedURL)
    expect(actualURL.match(/\/api\//g)).toHaveLength(1)
    expect(actualURL).not.toContain('/api/api/')
  })
})
