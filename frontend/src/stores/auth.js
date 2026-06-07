import { defineStore } from 'pinia'
import { login as apiLogin, getMe } from '@/api/auth'
import router from '@/router'
import { isTokenValid } from '@/composables/useTokenCheck'
import { useUiStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import { useCardStore } from '@/stores/card'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    user: null
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    // 后端历史上同时出现过 role: 'admin' 和 is_admin: true 两种字段，
    // 这里做兼容，避免管理员账号在部分接口返回下被误判为普通用户。
    isAdmin: (state) => state.user?.role === 'admin' || state.user?.is_admin === true
  },

  actions: {
    async login(username, password) {
      const data = await apiLogin(username, password)
      this.token = data.access_token
      localStorage.setItem('access_token', data.access_token)
      await this.fetchUser()
      return data
    },

    logout() {
      this.resetAllStores()
      router.push('/login')
    },

    /**
     * 获取当前用户信息
     * 区分 401 认证错误和网络错误，采取不同处理策略
     */
    async fetchUser() {
      // 保持内存 token 与持久化 token 一致；测试、刷新恢复和路由守卫都依赖
      // localStorage 中的 access_token。
      if (this.token) {
        localStorage.setItem('access_token', this.token)
      }

      try {
        const data = await getMe()
        this.user = data
      } catch (error) {
        // 区分错误类型
        if (error.response) {
          const status = error.response.status
          if (status === 401) {
            // 认证失败：token 无效或已过期，清除登录状态
            console.warn('[Auth] Token 无效或已过期，执行登出')
            this.token = ''
            this.user = null
            localStorage.removeItem('access_token')
            // 避免在登录页重复跳转
            if (router.currentRoute.value.path !== '/login') {
              router.push('/login?expired=1')
            }
          } else {
            // 其他 HTTP 错误（如 403、500 等），仅清除用户信息
            console.warn('[Auth] 获取用户信息失败:', status)
            this.user = null
          }
        } else if (error.request) {
          // 网络错误：请求已发出但未收到响应，不清除登录状态
          console.warn('[Auth] 网络错误，无法获取用户信息')
        } else {
          // 请求配置错误或其他未知错误
          console.warn('[Auth] 获取用户信息异常:', error.message)
        }
      }
    },

    /**
     * 检查当前 token 是否有效
     * @returns {boolean} token 是否有效
     */
    isTokenValid() {
      return isTokenValid(this.token)
    },

    /**
     * 重置所有 store 的状态
     * 在登出时调用，确保清理所有持久化数据
     */
    resetAllStores() {
      // 清除认证状态
      this.token = ''
      this.user = null
      localStorage.removeItem('access_token')

      // 重置其他 store
      try {
        const uiStore = useUiStore()
        if (uiStore?.reset) uiStore.reset()
      } catch {
        // store 可能尚未初始化，忽略错误
      }

      try {
        const projectStore = useProjectStore()
        if (projectStore?.$reset) projectStore.$reset()
      } catch {
        // store 可能尚未初始化，忽略错误
      }

      try {
        const cardStore = useCardStore()
        if (cardStore?.reset) cardStore.reset()
      } catch {
        // store 可能尚未初始化，忽略错误
      }
    }
  }
})
