import { createRouter, createWebHistory } from 'vue-router'
import { isTokenValid } from '@/composables/useTokenCheck'
import { useAuthStore } from '@/stores/auth'
import { finishRouteProgress, resetRouteProgress, startRouteProgress } from '@/utils/routeProgress'
import { setDocumentTitle } from '@/utils/pageTitle'
import { resolveRouteScrollPosition } from '@/utils/routeScroll'
import { sendPageViewTracking } from '@/utils/trackingClient'
import {
  canPassGlobalAccessGateVerified,
  clearUrlTokenQuery,
  getAccessDeniedRedirect,
  getUrlAccessToken,
  hasUrlTokenQuery,
  isShareTokenRoute,
  persistUrlAccessToken,
  validateUrlAccessToken,
  URL_ACCESS_TOKEN_STORAGE_KEY
} from './accessGate'

const routes = [
  {
    path: '/login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true, title: '登录' }
  },
  {
    path: '/access-denied',
    name: 'AccessDenied',
    component: () => import('@/views/AccessDenied.vue'),
    meta: { public: true, title: '访问未通过门禁' }
  },
  {
    path: '/exam/:id',
    name: 'PublicExam',
    component: () => import('@/views/PublicExamView.vue'),
    meta: { public: true, title: '考试详情' }
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomePage.vue'),
    meta: { public: true, title: '首页' }
  },
  {
    path: '/profile',
    component: () => import('@/layouts/ResponsiveLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        component: () => import('@/views/user/UserProfile.vue'),
        meta: { title: '个人中心', requiresAuth: true }
      }
    ]
  },
  {
    path: '/activities',
    component: () => import('@/layouts/ResponsiveLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        component: () => import('@/views/user/UserActivities.vue'),
        meta: { title: '活动记录', requiresAuth: true }
      }
    ]
  },
  {
    path: '/admin',
    component: () => import('@/layouts/ResponsiveLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      // 首页仪表盘
      { path: '', redirect: '/admin/dashboard' },
      {
        path: 'dashboard',
        component: () => import('@/views/admin/AdminDashboard.vue'),
        meta: { title: '仪表盘' }
      },
      // 设置页面
      {
        path: 'settings',
        component: () => import('@/views/admin/AdminSettings.vue'),
        meta: { title: '系统设置' }
      },
      // 卡片管理 — 已合并到项目管理
      {
        path: 'cards',
        redirect: '/admin/projects',
      },
      {
        path: 'cards/:pathMatch(.*)*',
        redirect: '/admin/projects',
      },
      // 项目管理路由
      {
        path: 'projects',
        component: () => import('@/views/admin/ProjectList.vue'),
        meta: { title: '项目管理' }
      },
      {
        path: 'projects/:id',
        component: () => import('@/views/admin/ProjectDetail.vue'),
        meta: { title: '项目详情' }
      },
      {
        path: 'projects/:id/upload',
        component: () => import('@/views/admin/FileUpload.vue'),
        meta: { title: '上传文件' }
      },
      {
        path: 'projects/:id/diff/:fileId',
        component: () => import('@/views/admin/DiffView.vue'),
        meta: { title: '版本对比' }
      },
      // 排行榜路由
      {
        path: 'rank/download',
        component: () => import('@/views/admin/RankDownload.vue'),
        meta: { title: '下载排行榜' }
      },
      {
        path: 'rank/visit',
        component: () => import('@/views/admin/RankVisit.vue'),
        meta: { title: '访问排行榜' }
      },
      // 追踪监控路由
      {
        path: 'tracking',
        component: () => import('@/views/admin/TrackingDashboard.vue'),
        meta: { title: '追踪监控' }
      },
      // 令牌管理路由
      {
        path: 'tokens',
        component: () => import('@/views/admin/TokenManager.vue'),
        meta: { title: '用户与令牌' }
      },
      // 公告管理路由
      {
        path: 'announcements',
        component: () => import('@/views/admin/AnnouncementManager.vue'),
        meta: { title: '公告管理' }
      },
      // 考试安排路由
      {
        path: 'exams',
        component: () => import('@/views/admin/ExamList.vue'),
        meta: { title: '考试安排' }
      },
      {
        path: 'exams/:id',
        component: () => import('@/views/admin/ExamDetail.vue'),
        meta: { title: '考试详情' }
      }
    ]
  },
  {
    path: '/s/:token',
    component: () => import('@/views/share/ShareLayout.vue'),
    meta: { public: true },
    children: [
      { path: '', component: () => import('@/views/share/ShareProject.vue'), meta: { title: '分享项目' } },
      { path: 'preview/:fileId', component: () => import('@/views/share/SharePreview.vue'), meta: { title: '文件预览' } },
      { path: 'files/:fileId', component: () => import('@/views/share/ShareFile.vue'), meta: { title: '文档预览' } },
      { path: 'diff/:fileId', component: () => import('@/views/share/ShareDiff.vue'), meta: { title: '分享版本对比' } }
    ]
  },

  // 404 兜底路由
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { public: true, title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    return resolveRouteScrollPosition(to, from, savedPosition)
  }
})

// ==================== 路由独占锁 ====================

/**
 * 路由导航锁
 * 防止并发导航导致的竞态条件（如快速连续点击多个菜单项）
 */
let navigationLock = false
let pendingNavigation = null

/**
 * 获取路由独占锁
 * @returns {boolean} 是否获取成功
 */
function acquireNavigationLock() {
  if (navigationLock) return false
  navigationLock = true
  return true
}

/**
 * 释放路由独占锁
 */
function releaseNavigationLock() {
  navigationLock = false
  // 如果有等待中的导航，执行它
  if (pendingNavigation) {
    const nav = pendingNavigation
    pendingNavigation = null
    nav()
  }
}

// ==================== 路由守卫 ====================

router.beforeEach(async (to, from, next) => {
  startRouteProgress()

  const urlToken = getUrlAccessToken(to)

  if (urlToken && !isShareTokenRoute(to)) {
    const valid = await validateUrlAccessToken(urlToken)
    if (valid) {
      persistUrlAccessToken(urlToken)
    } else {
      localStorage.removeItem(URL_ACCESS_TOKEN_STORAGE_KEY)
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
  }

  const canEnter = await canPassGlobalAccessGateVerified(to)
  if (!canEnter) {
    next(getAccessDeniedRedirect(to))
    return
  }

  if (hasUrlTokenQuery(to.query)) {
    next({ path: to.path, query: clearUrlTokenQuery(to.query), hash: to.hash, replace: true })
    return
  }

  next()
})

router.beforeEach((to, from, next) => {
  // 获取路由独占锁，防止并发导航
  if (!acquireNavigationLock()) {
    // 当前有导航正在进行，排队等待
    pendingNavigation = () => {
      router.replace(to.fullPath).catch(() => {})
    }
    finishRouteProgress()
    next(false)
    return
  }

  const token = localStorage.getItem('access_token')

  // 需要认证的路由
  if (to.matched.some((record) => record.meta.requiresAuth)) {
    if (!token) {
      // 无 token，跳转登录页
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }

    // 检查 token 有效性（解析 JWT exp）
    if (!isTokenValid(token)) {
      // token 已过期，清除并跳转登录页
      localStorage.removeItem('access_token')
      next({ path: '/login', query: { redirect: to.fullPath, expired: '1' } })
      return
    }

    // 检查角色权限
    const requiredRoles = to.meta.roles
    if (requiredRoles && requiredRoles.length > 0) {
      // 从 token payload 中解析用户角色
      const userRoles = parseTokenRoles(token)
      const hasPermission = requiredRoles.some((role) => userRoles.includes(role))
      if (!hasPermission) {
        // 权限不足，跳转到 404 页面
        next({ name: 'NotFound' })
        return
      }
    }
  }

  // 已登录用户访问登录页，重定向到管理页
  if (to.path === '/login' && token && isTokenValid(token)) {
    next('/admin')
    return
  }

  next()
})

router.beforeEach(async (to, from, next) => {
  if (to.path === '/login' || !to.matched.some((record) => record.meta.requiresAuth)) {
    next()
    return
  }

  const token = localStorage.getItem('access_token')
  if (!token || !isTokenValid(token)) {
    localStorage.removeItem('access_token')
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  const authStore = useAuthStore()
  if (!authStore.user) {
    try {
      await authStore.fetchUser()
    } catch {
      // 网络错误等非认证错误不清除登录状态，允许用户继续浏览
    }
  }

  if (!authStore.user) {
    const status = authStore.user === null && !localStorage.getItem('access_token')
    if (status) {
      next({ path: '/login', query: { redirect: to.fullPath, expired: '1' } })
    } else {
      // 网络错误导致无法获取用户信息，但 token 仍存在，不踢出用户
      next()
    }
    return
  }

  if (to.path.startsWith('/admin') && !authStore.isAdmin) {
    next({ name: 'NotFound' })
    return
  }

  next()
})

/**
 * 后置钩子：释放导航锁
 */
router.afterEach((to) => {
  setDocumentTitle(to)
  sendPageViewTracking()
  finishRouteProgress()
  releaseNavigationLock()
})

/**
 * 错误处理：释放导航锁
 */
router.onError(() => {
  resetRouteProgress()
  releaseNavigationLock()
})

// ==================== 数据预加载守卫 ====================

/**
 * beforeResolve 守卫：在路由确认前预加载数据
 * 路由组件可通过 meta.preload 指定需要预加载的数据
 */
router.beforeResolve(async (to) => {
  // 查找目标路由及其父路由中是否有 preload 配置
  const matched = [...to.matched].reverse()
  const preloadRoute = matched.find((record) => record.meta?.preload)

  if (preloadRoute?.meta?.preload) {
    try {
      // 执行预加载函数
      await preloadRoute.meta.preload(to)
    } catch (error) {
      // 预加载失败不阻塞导航，仅在开发环境打印警告
      if (import.meta.env.DEV) {
        console.warn('[Router] 数据预加载失败:', error)
      }
    }
  }
})

// ==================== 工具函数 ====================

/**
 * 从 JWT Token 或 Auth Store 中解析用户角色
 * JWT 优先（如后端已签发 role），否则回退到 store
 * @param {string} token - JWT Token
 * @returns {string[]} 用户角色列表
 */
function parseTokenRoles(token) {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return defaultRoles()
    const base64Url = parts[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(
      decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      )
    )
    if (Array.isArray(payload.roles)) return payload.roles
    if (typeof payload.role === 'string') return [payload.role]
    return defaultRoles()
  } catch {
    return defaultRoles()
  }
}

function defaultRoles() {
  try {
    const store = useAuthStore()
    if (store?.user?.role) return [store.user.role]
  } catch {}
  return ['user']
}

export default router
