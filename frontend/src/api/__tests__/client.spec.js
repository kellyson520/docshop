/**
 * API 客户端单元测试
 * 测试请求拦截器、响应拦截器、重试、取消和缓存功能
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

// 模拟 axios
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      },
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      patch: vi.fn()
    })),
    isCancel: vi.fn(),
    CancelToken: {
      source: vi.fn(() => ({
        token: 'cancel-token',
        cancel: vi.fn()
      }))
    }
  }
}))

// 模拟路由
const mockPush = vi.fn()
vi.mock('@/router', () => ({
  default: {
    push: (...args) => mockPush(...args)
  }
}))

describe('API 客户端', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockPush.mockClear()
  })

  /**
   * 基本功能测试
   */
  describe('基本功能', () => {
    it('应该能够导入客户端', async () => {
      const client = await import('../client.js')
      expect(client).toBeDefined()
    })

    it('应该导出 HTTP 方法', async () => {
      const { get, post, put, del, patch } = await import('../client.js')
      expect(get).toBeDefined()
      expect(post).toBeDefined()
      expect(put).toBeDefined()
      expect(del).toBeDefined()
      expect(patch).toBeDefined()
    })

    it('应该导出缓存控制方法', async () => {
      const { clearCache, clearCacheByPattern } = await import('../client.js')
      expect(clearCache).toBeDefined()
      expect(clearCacheByPattern).toBeDefined()
    })

    it('应该导出请求取消方法', async () => {
      const { cancelAllRequests } = await import('../client.js')
      expect(cancelAllRequests).toBeDefined()
    })
  })

  /**
   * HTTP 方法测试
   */
  describe('HTTP 方法', () => {
    it('GET 请求应该返回 Promise', async () => {
      const { get } = await import('../client.js')
      const result = get('/test')
      expect(result).toBeInstanceOf(Promise)
    })

    it('POST 请求应该返回 Promise', async () => {
      const { post } = await import('../client.js')
      const result = post('/test', { data: 'value' })
      expect(result).toBeInstanceOf(Promise)
    })

    it('PUT 请求应该返回 Promise', async () => {
      const { put } = await import('../client.js')
      const result = put('/test/1', { data: 'value' })
      expect(result).toBeInstanceOf(Promise)
    })

    it('DELETE 请求应该返回 Promise', async () => {
      const { del } = await import('../client.js')
      const result = del('/test/1')
      expect(result).toBeInstanceOf(Promise)
    })

    it('PATCH 请求应该返回 Promise', async () => {
      const { patch } = await import('../client.js')
      const result = patch('/test/1', { data: 'value' })
      expect(result).toBeInstanceOf(Promise)
    })
  })

  /**
   * 文件上传下载测试
   */
  describe('文件上传下载', () => {
    it('upload 应该返回 Promise', async () => {
      const { upload } = await import('../client.js')
      const formData = new FormData()
      const result = upload('/upload', formData)
      expect(result).toBeInstanceOf(Promise)
    })

    it('download 应该返回 Promise', async () => {
      const { download } = await import('../client.js')
      const result = download('/download/file.pdf')
      expect(result).toBeInstanceOf(Promise)
    })
  })

  /**
   * 缓存机制测试
   */
  describe('缓存机制', () => {
    it('clearCache 不应该抛出错误', async () => {
      const { clearCache } = await import('../client.js')
      expect(() => clearCache()).not.toThrow()
    })

    it('clearCacheByPattern 不应该抛出错误', async () => {
      const { clearCacheByPattern } = await import('../client.js')
      expect(() => clearCacheByPattern('/api')).not.toThrow()
    })
  })

  /**
   * 请求取消测试
   */
  describe('请求取消', () => {
    it('cancelAllRequests 不应该抛出错误', async () => {
      const { cancelAllRequests } = await import('../client.js')
      expect(() => cancelAllRequests()).not.toThrow()
    })
  })
})
