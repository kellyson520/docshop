/**
 * auth store 单元测试
 * 测试认证状态管理功能
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../auth.js'

// 模拟 API 模块
const {
  mockLogin,
  mockGetMe,
  mockPush,
  mockCurrentRoute,
  mockIsTokenValid
} = vi.hoisted(() => ({
  mockLogin: vi.fn(),
  mockGetMe: vi.fn(),
  mockPush: vi.fn(),
  mockCurrentRoute: { value: { path: '/dashboard' } },
  mockIsTokenValid: vi.fn()
}))

vi.mock('@/api/auth', () => ({
  login: (...args) => mockLogin(...args),
  getMe: () => mockGetMe()
}))

// 模拟路由
vi.mock('@/router', () => ({
  default: {
    push: (...args) => mockPush(...args),
    currentRoute: mockCurrentRoute
  }
}))

// 模拟 useTokenCheck
vi.mock('@/composables/useTokenCheck', () => ({
  isTokenValid: (token) => mockIsTokenValid(token)
}))

// 模拟其他 stores
vi.mock('@/stores/ui', () => ({
  useUiStore: vi.fn(() => ({ reset: vi.fn() }))
}))
vi.mock('@/stores/project', () => ({
  useProjectStore: vi.fn(() => ({ $reset: vi.fn() }))
}))
vi.mock('@/stores/card', () => ({
  useCardStore: vi.fn(() => ({ reset: vi.fn() }))
}))

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    mockLogin.mockClear()
    mockGetMe.mockClear()
    mockPush.mockClear()
    mockIsTokenValid.mockClear()
    mockCurrentRoute.value = { path: '/dashboard' }
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  /**
   * 初始状态测试
   */
  describe('初始状态', () => {
    it('应该具有正确的初始状态', () => {
      const store = useAuthStore()

      expect(store.token).toBe('')
      expect(store.user).toBeNull()
    })

    it('应该从 localStorage 读取 token', () => {
      localStorage.setItem('access_token', 'stored-token')

      const store = useAuthStore()

      expect(store.token).toBe('stored-token')
    })

    it('isLoggedIn getter 在初始状态下应该返回 false', () => {
      const store = useAuthStore()

      expect(store.isLoggedIn).toBe(false)
    })

    it('isAdmin getter 在初始状态下应该返回 false', () => {
      const store = useAuthStore()

      expect(store.isAdmin).toBe(false)
    })
  })

  /**
   * 登录成功测试
   */
  describe('登录成功', () => {
    it('login 应该设置 token', async () => {
      const store = useAuthStore()
      mockLogin.mockResolvedValueOnce({ access_token: 'test-token' })
      mockGetMe.mockResolvedValueOnce({ id: 1, username: 'test' })

      await store.login('testuser', 'password123')

      expect(store.token).toBe('test-token')
    })

    it('login 应该将 token 保存到 localStorage', async () => {
      const store = useAuthStore()
      mockLogin.mockResolvedValueOnce({ access_token: 'test-token' })
      mockGetMe.mockResolvedValueOnce({ id: 1, username: 'test' })

      await store.login('testuser', 'password123')

      expect(localStorage.getItem('access_token')).toBe('test-token')
    })

    it('login 成功后应该获取用户信息', async () => {
      const store = useAuthStore()
      const userData = { id: 1, username: 'testuser', is_admin: false }
      mockLogin.mockResolvedValueOnce({ access_token: 'test-token' })
      mockGetMe.mockResolvedValueOnce(userData)

      await store.login('testuser', 'password123')

      expect(store.user).toEqual(userData)
    })

    it('login 成功后 isLoggedIn 应该返回 true', async () => {
      const store = useAuthStore()
      mockLogin.mockResolvedValueOnce({ access_token: 'test-token' })
      mockGetMe.mockResolvedValueOnce({ id: 1, username: 'test' })

      await store.login('testuser', 'password123')

      expect(store.isLoggedIn).toBe(true)
    })

    it('管理员登录后 isAdmin 应该返回 true', async () => {
      const store = useAuthStore()
      mockLogin.mockResolvedValueOnce({ access_token: 'test-token' })
      mockGetMe.mockResolvedValueOnce({ id: 1, username: 'admin', is_admin: true })

      await store.login('admin', 'password123')

      expect(store.isAdmin).toBe(true)
    })

    it('普通用户登录后 isAdmin 应该返回 false', async () => {
      const store = useAuthStore()
      mockLogin.mockResolvedValueOnce({ access_token: 'test-token' })
      mockGetMe.mockResolvedValueOnce({ id: 1, username: 'user', is_admin: false })

      await store.login('user', 'password123')

      expect(store.isAdmin).toBe(false)
    })

    it('login 应该返回登录数据', async () => {
      const store = useAuthStore()
      const loginData = { access_token: 'test-token', token_type: 'bearer' }
      mockLogin.mockResolvedValueOnce(loginData)
      mockGetMe.mockResolvedValueOnce({ id: 1, username: 'test' })

      const result = await store.login('testuser', 'password123')

      expect(result).toEqual(loginData)
    })

    it('login 应该调用 API 传入正确的参数', async () => {
      const store = useAuthStore()
      mockLogin.mockResolvedValueOnce({ access_token: 'test-token' })
      mockGetMe.mockResolvedValueOnce({ id: 1, username: 'test' })

      await store.login('testuser', 'password123')

      expect(mockLogin).toHaveBeenCalledWith('testuser', 'password123')
    })
  })

  /**
   * 登录失败测试
   */
  describe('登录失败', () => {
    it('login 失败应该抛出错误', async () => {
      const store = useAuthStore()
      mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'))

      await expect(store.login('testuser', 'wrongpassword')).rejects.toThrow('Invalid credentials')
    })

    it('login 失败不应该设置 token', async () => {
      const store = useAuthStore()
      mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'))

      try {
        await store.login('testuser', 'wrongpassword')
      } catch {
        // 忽略错误
      }

      expect(store.token).toBe('')
    })

    it('login 失败不应该保存 token 到 localStorage', async () => {
      const store = useAuthStore()
      mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'))

      try {
        await store.login('testuser', 'wrongpassword')
      } catch {
        // 忽略错误
      }

      expect(localStorage.getItem('access_token')).toBeNull()
    })

    it('login 失败不应该获取用户信息', async () => {
      const store = useAuthStore()
      mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'))

      try {
        await store.login('testuser', 'wrongpassword')
      } catch {
        // 忽略错误
      }

      expect(mockGetMe).not.toHaveBeenCalled()
    })
  })

  /**
   * 登出测试
   */
  describe('登出', () => {
    it('logout 应该清除 token', async () => {
      const store = useAuthStore()
      mockLogin.mockResolvedValueOnce({ access_token: 'test-token' })
      mockGetMe.mockResolvedValueOnce({ id: 1, username: 'test' })

      await store.login('testuser', 'password123')
      store.logout()

      expect(store.token).toBe('')
    })

    it('logout 应该清除用户信息', async () => {
      const store = useAuthStore()
      mockLogin.mockResolvedValueOnce({ access_token: 'test-token' })
      mockGetMe.mockResolvedValueOnce({ id: 1, username: 'test' })

      await store.login('testuser', 'password123')
      store.logout()

      expect(store.user).toBeNull()
    })

    it('logout 应该从 localStorage 移除 token', async () => {
      const store = useAuthStore()
      mockLogin.mockResolvedValueOnce({ access_token: 'test-token' })
      mockGetMe.mockResolvedValueOnce({ id: 1, username: 'test' })

      await store.login('testuser', 'password123')
      store.logout()

      expect(localStorage.getItem('access_token')).toBeNull()
    })

    it('logout 应该跳转到登录页', async () => {
      const store = useAuthStore()
      store.logout()

      expect(mockPush).toHaveBeenCalledWith('/login')
    })

    it('logout 后 isLoggedIn 应该返回 false', async () => {
      const store = useAuthStore()
      mockLogin.mockResolvedValueOnce({ access_token: 'test-token' })
      mockGetMe.mockResolvedValueOnce({ id: 1, username: 'test' })

      await store.login('testuser', 'password123')
      store.logout()

      expect(store.isLoggedIn).toBe(false)
    })
  })

  /**
   * Token 验证测试
   */
  describe('Token 验证', () => {
    it('isTokenValid 应该返回 true 当 token 有效时', () => {
      const store = useAuthStore()
      mockIsTokenValid.mockReturnValueOnce(true)

      store.token = 'valid-token'
      const result = store.isTokenValid()

      expect(result).toBe(true)
      expect(mockIsTokenValid).toHaveBeenCalledWith('valid-token')
    })

    it('isTokenValid 应该返回 false 当 token 无效时', () => {
      const store = useAuthStore()
      mockIsTokenValid.mockReturnValueOnce(false)

      store.token = 'invalid-token'
      const result = store.isTokenValid()

      expect(result).toBe(false)
    })

    it('isTokenValid 应该返回 false 当 token 为空时', () => {
      const store = useAuthStore()
      mockIsTokenValid.mockReturnValueOnce(false)

      store.token = ''
      const result = store.isTokenValid()

      expect(result).toBe(false)
    })
  })

  /**
   * 获取用户信息测试
   */
  describe('获取用户信息', () => {
    it('fetchUser 应该获取并设置用户信息', async () => {
      const store = useAuthStore()
      const userData = { id: 1, username: 'testuser', email: 'test@example.com' }
      mockGetMe.mockResolvedValueOnce(userData)

      await store.fetchUser()

      expect(store.user).toEqual(userData)
    })

    it('fetchUser 401 错误应该清除 token 并跳转登录页', async () => {
      const store = useAuthStore()
      store.token = 'invalid-token'
      localStorage.setItem('access_token', 'invalid-token')

      const error = new Error('Unauthorized')
      error.response = { status: 401 }
      mockGetMe.mockRejectedValueOnce(error)

      await store.fetchUser()

      expect(store.token).toBe('')
      expect(store.user).toBeNull()
      expect(localStorage.getItem('access_token')).toBeNull()
      expect(mockPush).toHaveBeenCalledWith('/login?expired=1')
    })

    it('fetchUser 401 错误在登录页不应该重复跳转', async () => {
      const store = useAuthStore()
      store.token = 'invalid-token'
      mockCurrentRoute.value = { path: '/login' }

      const error = new Error('Unauthorized')
      error.response = { status: 401 }
      mockGetMe.mockRejectedValueOnce(error)

      await store.fetchUser()

      expect(mockPush).not.toHaveBeenCalled()
    })

    it('fetchUser 其他 HTTP 错误应该只清除用户信息', async () => {
      const store = useAuthStore()
      store.token = 'valid-token'
      store.user = { id: 1, username: 'test' }

      const error = new Error('Forbidden')
      error.response = { status: 403 }
      mockGetMe.mockRejectedValueOnce(error)

      await store.fetchUser()

      expect(store.token).toBe('valid-token')
      expect(store.user).toBeNull()
      expect(localStorage.getItem('access_token')).toBe('valid-token')
    })

    it('fetchUser 网络错误不应该清除登录状态', async () => {
      const store = useAuthStore()
      store.token = 'valid-token'
      store.user = { id: 1, username: 'test' }
      localStorage.setItem('access_token', 'valid-token')

      const error = new Error('Network Error')
      error.request = {}
      mockGetMe.mockRejectedValueOnce(error)

      await store.fetchUser()

      expect(store.token).toBe('valid-token')
      expect(localStorage.getItem('access_token')).toBe('valid-token')
    })

    it('fetchUser 请求配置错误不应该清除登录状态', async () => {
      const store = useAuthStore()
      store.token = 'valid-token'
      localStorage.setItem('access_token', 'valid-token')

      const error = new Error('Request config error')
      mockGetMe.mockRejectedValueOnce(error)

      await store.fetchUser()

      expect(store.token).toBe('valid-token')
      expect(localStorage.getItem('access_token')).toBe('valid-token')
    })
  })

  /**
   * 重置所有 stores 测试
   */
  describe('重置所有 stores', () => {
    it('resetAllStores 应该清除认证状态', async () => {
      const store = useAuthStore()
      mockLogin.mockResolvedValueOnce({ access_token: 'test-token' })
      mockGetMe.mockResolvedValueOnce({ id: 1, username: 'test' })

      await store.login('testuser', 'password123')
      store.resetAllStores()

      expect(store.token).toBe('')
      expect(store.user).toBeNull()
    })

    it('resetAllStores 应该从 localStorage 移除 token', async () => {
      const store = useAuthStore()
      mockLogin.mockResolvedValueOnce({ access_token: 'test-token' })
      mockGetMe.mockResolvedValueOnce({ id: 1, username: 'test' })

      await store.login('testuser', 'password123')
      store.resetAllStores()

      expect(localStorage.getItem('access_token')).toBeNull()
    })
  })
})
