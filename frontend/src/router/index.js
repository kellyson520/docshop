import { createRouter, createWebHistory } from 'vue-router'
import { isTokenValid } from '@/composables/useTokenCheck'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true }
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
    meta: { public: true }
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
      { path: '', component: () => import('@/views/share/ShareProject.vue') },
      { path: 'files/:fileId', component: () => import('@/views/share/ShareFile.vue') },
      { path: 'diff/:fileId', component: () => import('@/views/share/ShareDiff.vue') }
    ]
  },

  // 404 兜底路由
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { public: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
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

/**
 * 前置守卫：认证校验、Token 有效性检查、角色权限
 */
router.beforeEach((to, from, next) => {
  const urlToken = typeof to.query.token === 'string' ? to.query.token : ''
  if (urlToken && isTokenValid(urlToken)) {
    localStorage.setItem('access_token', urlToken)
    const query = { ...to.query }
    delete query.token
    next({ path: to.path, query, hash: to.hash, replace: true })
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
    next(false)
    return
  }

  const token = localStorage.getItem('access_token')

  // 需要认证的路由
  if (to.matched.some((record) => record.meta.requiresAuth)) {
    if (!token) {
      // 无 token，跳转登录页
      releaseNavigationLock()
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }

    // 检查 token 有效性（解析 JWT exp）
    if (!isTokenValid(token)) {
      // token 已过期，清除并跳转登录页
      localStorage.removeItem('access_token')
      releaseNavigationLock()
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
        releaseNavigationLock()
        // 权限不足，跳转到 404 页面
        next({ name: 'NotFound' })
        return
      }
    }
  }

  // 已登录用户访问登录页，重定向到管理页
  if (to.path === '/login' && token && isTokenValid(token)) {
    releaseNavigationLock()
    next('/admin')
    return
  }

  next()
})

router.beforeEach(async (to, from, next) => {
  if (to.path === '/login') {
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
    await authStore.fetchUser()
  }

  if (!authStore.user) {
    next({ path: '/login', query: { redirect: to.fullPath, expired: '1' } })
    return
  }

  if (to.path.startsWith('/admin') && authStore.user.role !== 'admin') {
    next({ name: 'NotFound' })
    return
  }

  next()
})

/**
 * 后置钩子：释放导航锁
 */
router.afterEach(() => {
  releaseNavigationLock()
})

/**
 * 错误处理：释放导航锁
 */
router.onError(() => {
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
      if (process.env.NODE_ENV === 'development') {
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
