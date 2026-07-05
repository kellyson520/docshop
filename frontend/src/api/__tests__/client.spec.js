import { describe, it, expect, vi, beforeEach } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))

const {
  mockAxiosClient,
  mockAxiosCreate,
  mockAxiosIsCancel,
  mockRequestUse,
  mockResponseUse,
  mockPush,
  mockCurrentRoute,
  mockParseError
} = vi.hoisted(() => {
  const requestUse = vi.fn()
  const responseUse = vi.fn()
  const client = {
    interceptors: {
      request: { use: requestUse },
      response: { use: responseUse }
    },
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn()
  }

  return {
    mockAxiosClient: client,
    mockAxiosCreate: vi.fn(() => client),
    mockAxiosIsCancel: vi.fn(() => false),
    mockRequestUse: requestUse,
    mockResponseUse: responseUse,
    mockPush: vi.fn(),
    mockCurrentRoute: {
      value: {
        path: '/dashboard',
        fullPath: '/dashboard',
        params: {},
        query: {}
      }
    },
    mockParseError: vi.fn((error) => {
      const status = error?.response?.status
      if (status === 401) {
        return {
          type: 'auth',
          action: 'logout',
          message: 'Unauthorized'
        }
      }

      return {
        type: 'unknown',
        action: 'none',
        message: error?.message || 'Unknown error'
      }
    })
  }
})

vi.mock('axios', () => ({
  default: {
    create: (...args) => mockAxiosCreate(...args),
    isCancel: (...args) => mockAxiosIsCancel(...args),
    CancelToken: {
      source: vi.fn(() => ({
        token: 'cancel-token',
        cancel: vi.fn()
      }))
    }
  }
}))

vi.mock('@/router', () => ({
  default: {
    push: (...args) => mockPush(...args),
    currentRoute: mockCurrentRoute
  }
}))

vi.mock('@/utils/error', () => ({
  ErrorHandler: {
    parseError: (...args) => mockParseError(...args)
  }
}))

describe('API client', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
    mockAxiosCreate.mockImplementation(() => mockAxiosClient)
    mockAxiosIsCancel.mockReturnValue(false)
    mockParseError.mockImplementation((error) => {
      const status = error?.response?.status
      if (status === 401) {
        return {
          type: 'auth',
          action: 'logout',
          message: 'Unauthorized'
        }
      }

      return {
        type: 'unknown',
        action: 'none',
        message: error?.message || 'Unknown error'
      }
    })
    mockCurrentRoute.value = {
      path: '/dashboard',
      fullPath: '/dashboard',
      params: {},
      query: {}
    }
    localStorage.clear()
  })

  async function importClientModule() {
    return import('../client.js')
  }

  async function getResponseErrorInterceptor() {
    await importClientModule()
    return mockResponseUse.mock.calls[0]?.[1]
  }

  describe('release hygiene', () => {
    it('does not leave direct console.log API data output in production code', () => {
      const source = readFileSync(resolve(__dirname, '../client.js'), 'utf-8')
      const directConsoleLogLines = source
        .split('\n')
        .filter((line) => line.includes('console.log('))
        .filter((line) => !line.includes('debugLog('))

      expect(directConsoleLogLines).toEqual([])
    })
  })

  describe('basic exports', () => {
    it('can import the client module', async () => {
      const client = await importClientModule()
      expect(client).toBeDefined()
    })

    it('exports the main HTTP methods', async () => {
      const { get, post, put, del, patch } = await importClientModule()
      expect(get).toBeDefined()
      expect(post).toBeDefined()
      expect(put).toBeDefined()
      expect(del).toBeDefined()
      expect(patch).toBeDefined()
    })

    it('exports cache helpers', async () => {
      const { clearCache, clearCacheByPattern } = await importClientModule()
      expect(clearCache).toBeDefined()
      expect(clearCacheByPattern).toBeDefined()
    })

    it('exports request cancellation helper', async () => {
      const { cancelAllRequests } = await importClientModule()
      expect(cancelAllRequests).toBeDefined()
    })
  })

  describe('HTTP methods', () => {
    it('GET returns a Promise', async () => {
      const { get } = await importClientModule()
      expect(get('/test')).toBeInstanceOf(Promise)
    })

    it('POST returns a Promise', async () => {
      const { post } = await importClientModule()
      expect(post('/test', { data: 'value' })).toBeInstanceOf(Promise)
    })

    it('PUT returns a Promise', async () => {
      const { put } = await importClientModule()
      expect(put('/test/1', { data: 'value' })).toBeInstanceOf(Promise)
    })

    it('DELETE returns a Promise', async () => {
      const { del } = await importClientModule()
      expect(del('/test/1')).toBeInstanceOf(Promise)
    })

    it('PATCH returns a Promise', async () => {
      const { patch } = await importClientModule()
      expect(patch('/test/1', { data: 'value' })).toBeInstanceOf(Promise)
    })
  })

  describe('upload and download', () => {
    it('upload returns a Promise', async () => {
      const { upload } = await importClientModule()
      const formData = new FormData()
      expect(upload('/upload', formData)).toBeInstanceOf(Promise)
    })

    it('download returns a Promise', async () => {
      const { download } = await importClientModule()
      expect(download('/download/file.pdf')).toBeInstanceOf(Promise)
    })
  })

  describe('helpers', () => {
    it('clearCache does not throw', async () => {
      const { clearCache } = await importClientModule()
      expect(() => clearCache()).not.toThrow()
    })

    it('clearCacheByPattern does not throw', async () => {
      const { clearCacheByPattern } = await importClientModule()
      expect(() => clearCacheByPattern('/api')).not.toThrow()
    })

    it('cancelAllRequests does not throw', async () => {
      const { cancelAllRequests } = await importClientModule()
      expect(() => cancelAllRequests()).not.toThrow()
    })
  })

  describe('401 redirect handling', () => {
    it('reuses access-denied page for share route 401 and keeps the original target', async () => {
      localStorage.setItem('access_token', 'stale-token')
      mockCurrentRoute.value = {
        path: '/s/share-token/preview/file-1',
        fullPath: '/s/share-token/preview/file-1?from=mobile',
        params: { token: 'share-token', fileId: 'file-1' },
        query: { from: 'mobile' }
      }

      const onError = await getResponseErrorInterceptor()
      const error = new Error('Unauthorized')
      error.response = { status: 401, data: { detail: 'Could not validate credentials' } }

      await expect(onError(error)).rejects.toBe(error)

      expect(localStorage.getItem('access_token')).toBeNull()
      expect(mockPush).toHaveBeenCalledWith({
        path: '/access-denied',
        query: {
          redirect: '/s/share-token/preview/file-1?from=mobile',
          reason: 'invalid_token'
        }
      })
    })

    it('keeps existing login redirect for non-share route 401', async () => {
      localStorage.setItem('access_token', 'stale-token')
      mockCurrentRoute.value = {
        path: '/admin/projects',
        fullPath: '/admin/projects',
        params: {},
        query: {}
      }

      const onError = await getResponseErrorInterceptor()
      const error = new Error('Unauthorized')
      error.response = { status: 401, data: { detail: 'Could not validate credentials' } }

      await expect(onError(error)).rejects.toBe(error)

      expect(localStorage.getItem('access_token')).toBeNull()
      expect(mockPush).toHaveBeenCalledWith('/login?expired=1')
    })
  })
})
