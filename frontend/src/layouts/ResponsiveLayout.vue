<template>
  <div class="responsive-layout" :class="layoutClass">
    <!-- PC端侧边栏 -->
    <aside v-if="showSidebar" class="layout-sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <el-icon :size="32"><Document /></el-icon>
          <span v-if="!collapsed" class="logo-text">文档管理系统</span>
        </div>
        <el-button
          v-if="isDesktop"
          :icon="collapsed ? Expand : Fold"
          text
          @click="toggleCollapse"
          class="collapse-btn"
        />
      </div>

      <div
        class="sidebar-user-card"
        :class="{ collapsed }"
        role="button"
        tabindex="0"
        @click="goProfile"
        @keydown.enter="goProfile"
      >
        <el-avatar :size="36" :src="userAvatar" :icon="UserFilled" class="sidebar-user-avatar" />
        <div v-if="!collapsed" class="sidebar-user-meta">
          <span class="sidebar-user-name">{{ username }}</span>
          <span class="sidebar-user-role">{{ userRoleLabel }}</span>
        </div>
      </div>

      <el-scrollbar class="sidebar-content">
        <el-menu
          :default-active="activeMenu"
          :collapse="collapsed"
          router
          :unique-opened="true"
          class="sidebar-menu"
        >
          <el-menu-item index="/admin/dashboard">
            <el-icon><HomeFilled /></el-icon>
            <template #title>首页</template>
          </el-menu-item>

          <el-menu-item index="/admin/projects">
            <el-icon><Files /></el-icon>
            <template #title>
              <span>项目管理</span>
              <el-badge v-if="projectCount > 0" :value="projectCount" :max="99" class="menu-badge" />
            </template>
          </el-menu-item>

          <el-menu-item index="/admin/exams">
            <el-icon><Calendar /></el-icon>
            <template #title>
              <span>考试安排</span>
              <el-badge v-if="examCount > 0" :value="examCount" :max="99" class="menu-badge warning" />
            </template>
          </el-menu-item>

          <el-sub-menu index="rank">
            <template #title>
              <el-icon><TrendCharts /></el-icon>
              <span>排行榜</span>
            </template>
            <el-menu-item index="/admin/rank/download">
              <el-icon><Download /></el-icon>
              <template #title>下载排行</template>
            </el-menu-item>
            <el-menu-item index="/admin/rank/visit">
              <el-icon><View /></el-icon>
              <template #title>访问排行</template>
            </el-menu-item>
          </el-sub-menu>

          <el-menu-item index="/admin/tokens">
            <el-icon><Key /></el-icon>
            <template #title>用户与令牌</template>
          </el-menu-item>

          <el-menu-item index="/admin/announcements">
            <el-icon><Notification /></el-icon>
            <template #title>公告管理</template>
          </el-menu-item>

          <el-menu-item index="/admin/tracking">
            <el-icon><DataLine /></el-icon>
            <template #title>追踪监控</template>
          </el-menu-item>

          <el-menu-item index="/admin/settings">
            <el-icon><Setting /></el-icon>
            <template #title>系统设置</template>
          </el-menu-item>
        </el-menu>
      </el-scrollbar>

      <div class="sidebar-footer">
        <NotificationCenter />
        <el-button :icon="SwitchButton" text class="sidebar-logout" @click="logout">
          <span v-if="!collapsed">退出登录</span>
        </el-button>
      </div>
    </aside>

    <!-- 平板/手机端抽屉侧边栏 -->
    <el-drawer
      v-if="isMobile"
      v-model="drawerVisible"
      direction="ltr"
      :size="'min(86vw, 320px)'"
      :with-header="false"
      :show-close="false"
      class="mobile-drawer"
    >
      <aside class="layout-sidebar mobile">
        <div class="sidebar-header">
          <div class="logo">
            <el-icon :size="32"><Document /></el-icon>
            <span class="logo-text">文档管理系统</span>
          </div>
          <el-button :icon="Close" text @click="closeDrawer" />
        </div>

        <div
          class="sidebar-user-card mobile-user-card"
          role="button"
          tabindex="0"
          @click="goProfile"
          @keydown.enter="goProfile"
        >
          <el-avatar :size="36" :src="userAvatar" :icon="UserFilled" class="sidebar-user-avatar" />
          <div class="sidebar-user-meta">
            <span class="sidebar-user-name">{{ username }}</span>
            <span class="sidebar-user-role">{{ userRoleLabel }}</span>
          </div>
        </div>

        <el-scrollbar class="sidebar-content">
          <el-menu :default-active="activeMenu" router @select="closeDrawer" class="sidebar-menu">
            <el-menu-item index="/admin/dashboard">
              <el-icon><HomeFilled /></el-icon>
              <template #title>首页</template>
            </el-menu-item>

            <el-menu-item index="/admin/projects">
              <el-icon><Files /></el-icon>
              <template #title>
                <span>项目管理</span>
                <el-badge v-if="projectCount > 0" :value="projectCount" :max="99" class="menu-badge" />
              </template>
            </el-menu-item>

            <el-menu-item index="/admin/exams">
              <el-icon><Calendar /></el-icon>
              <template #title>
                <span>考试安排</span>
                <el-badge v-if="examCount > 0" :value="examCount" :max="99" class="menu-badge warning" />
              </template>
            </el-menu-item>

            <el-sub-menu index="rank">
              <template #title>
                <el-icon><TrendCharts /></el-icon>
                <span>排行榜</span>
              </template>
              <el-menu-item index="/admin/rank/download">
                <el-icon><Download /></el-icon>
                <template #title>下载排行</template>
              </el-menu-item>
              <el-menu-item index="/admin/rank/visit">
                <el-icon><View /></el-icon>
                <template #title>访问排行</template>
              </el-menu-item>
            </el-sub-menu>

            <el-menu-item index="/admin/tokens">
              <el-icon><Key /></el-icon>
              <template #title>用户与令牌</template>
            </el-menu-item>

            <el-menu-item index="/admin/announcements">
              <el-icon><Notification /></el-icon>
              <template #title>公告管理</template>
            </el-menu-item>

            <el-menu-item index="/admin/tracking">
              <el-icon><DataLine /></el-icon>
              <template #title>追踪监控</template>
            </el-menu-item>

            <el-menu-item index="/admin/settings">
              <el-icon><Setting /></el-icon>
              <template #title>系统设置</template>
            </el-menu-item>
          </el-menu>
        </el-scrollbar>
      </aside>
    </el-drawer>

    <!-- 主内容区 -->
    <main class="layout-main">
      <!-- 移动端顶部栏 -->
      <header v-if="isMobile" class="mobile-header">
        <div class="mobile-header-shell">
          <el-button :icon="Menu" text aria-label="打开导航" @click="openDrawer" class="menu-btn" />
          <div class="mobile-title-block">
            <span class="mobile-kicker">DocShop Workspace</span>
            <h1 class="page-title">{{ pageTitle }}</h1>
          </div>
          <div class="mobile-header-actions">
            <NotificationCenter />
          </div>
        </div>
      </header>

      <!-- 内容 -->
      <div class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in" appear>
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>

    <!-- 公告栏 -->
    <!-- 考试提醒组件 -->
    <ExamReminder />

    <!-- 移动端底部导航 -->
    <nav v-if="isMobile" class="bottom-nav">
      <button
        v-for="item in bottomNavItems"
        :key="item.path"
        type="button"
        class="nav-item"
        :class="{ active: isActiveRoute(item.path) }"
        :aria-current="isActiveRoute(item.path) ? 'page' : undefined"
        @click="navigateTo(item.path)"
      >
        <span class="nav-icon-shell">
          <el-badge v-if="item.badge" :value="item.badge" :max="99" class="nav-badge">
            <el-icon :size="22">
              <component :is="item.icon" />
            </el-icon>
          </el-badge>
          <el-icon v-else :size="22">
            <component :is="item.icon" />
          </el-icon>
        </span>
        <span class="nav-label">{{ item.label }}</span>
      </button>
      <button type="button" class="nav-item" @click="uiStore.toggleTheme()">
        <span class="nav-icon-shell">
          <el-icon :size="22" class="theme-icon">
            <Moon v-if="!uiStore.isDark" />
            <Sunny v-else />
          </el-icon>
        </span>
        <span class="nav-label">{{ uiStore.isDark ? '浅色' : '深色' }}</span>
      </button>
    </nav>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Document, HomeFilled, Files, TrendCharts, Setting,
  Download, View, UserFilled, Menu, Expand, Fold, Sunny, Moon,
  Calendar, DataLine, Close, Notification, Key, SwitchButton
} from '@element-plus/icons-vue'
import { useResponsive } from '@/composables/useResponsive'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useProjectStore } from '@/stores/project'
import { useExamStore } from '@/stores/exam'
import NotificationCenter from '@/components/common/NotificationCenter.vue'
import ExamReminder from '@/components/exam/ExamReminder.vue'
import { resolveAvatarUrl } from '@/utils/assetUrl'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()
const projectStore = useProjectStore()
const examStore = useExamStore()

const {
  isMobile,
  isTablet,
  isDesktop,
  isLandscape
} = useResponsive()

// 侧边栏状态
const collapsed = ref(false)
const drawerVisible = ref(false)

// 用户信息
const username = computed(() => {
  return authStore.user?.username || '管理员'
})

const userAvatar = computed(() => {
  return resolveAvatarUrl(authStore.user?.avatar || '')
})

const userRoleLabel = computed(() => {
  return { admin: '管理员', user: '上传者', viewer: '访客' }[authStore.user?.role] || '管理员'
})

// 数据统计
const projectCount = computed(() => projectStore.projects?.length || 0)
const examCount = computed(() => {
  const now = new Date()
  return examStore.exams?.filter(exam => {
    const startTime = new Date(exam.start_time)
    return startTime > now
  }).length || 0
})

// 当前激活菜单
const activeMenu = computed(() => {
  if (route.path.startsWith('/admin/projects')) return '/admin/projects'
  if (route.path.startsWith('/admin/exams')) return '/admin/exams'
  if (route.path.startsWith('/admin/rank/download')) return '/admin/rank/download'
  if (route.path.startsWith('/admin/rank/visit')) return '/admin/rank/visit'
  if (route.path.startsWith('/admin/tokens')) return '/admin/tokens'
  if (route.path.startsWith('/admin/announcements')) return '/admin/announcements'
  if (route.path.startsWith('/admin/tracking')) return '/admin/tracking'
  if (route.path.startsWith('/admin/settings')) return '/admin/settings'
  if (route.path === '/admin' || route.path === '/admin/dashboard') return '/admin/dashboard'
  return '/admin'
})

// 页面标题
const pageTitle = computed(() => {
  const titleMap = {
    '/admin/dashboard': '首页',
    '/admin/projects': '项目管理',
    '/admin/exams': '考试安排',
    '/admin/settings': '系统设置',
    '/admin/tracking': '追踪监控',
    '/admin/tokens': '用户与令牌',
    '/admin/announcements': '公告管理',
    '/admin/rank/download': '下载排行',
    '/admin/rank/visit': '访问排行'
  }
  // 尝试精确匹配
  if (titleMap[route.path]) {
    return titleMap[route.path]
  }
  // 尝试前缀匹配
  for (const [path, title] of Object.entries(titleMap).sort((a, b) => b[0].length - a[0].length)) {
    if (route.path.startsWith(path + '/')) {
      return title
    }
  }
  return '文档管理系统'
})

// 布局类名
const layoutClass = computed(() => {
  return {
    'layout-desktop': isDesktop.value,
    'layout-tablet': isTablet.value,
    'layout-mobile': isMobile.value,
    'sidebar-collapsed': collapsed.value,
    'theme-dark': uiStore.isDark
  }
})

// 是否显示侧边栏
const showSidebar = computed(() => {
  return isDesktop.value || isTablet.value
})

// 底部导航项 (文档管理已合并到项目管理)
const bottomNavItems = computed(() => [
  { path: '/admin/dashboard', label: '首页', icon: HomeFilled },
  { path: '/admin/projects', label: '项目', icon: Files, badge: projectCount.value },
  { path: '/admin/exams', label: '考试', icon: Calendar, badge: examCount.value },
  { path: '/admin/settings', label: '设置', icon: Setting }
])

function toggleCollapse() {
  collapsed.value = !collapsed.value
}

function openDrawer() {
  drawerVisible.value = true
}

function closeDrawer() {
  drawerVisible.value = false
}

function navigateTo(path) {
  router.push(path)
}

function goProfile() {
  drawerVisible.value = false
  router.push('/profile')
}

function logout() {
  authStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}

function isActiveRoute(path) {
  if (path === '/admin/dashboard') {
    return route.path === '/admin' || route.path === '/admin/dashboard'
  }
  return route.path === path || route.path.startsWith(path + '/')
}

// 监听路由变化关闭抽屉
watch(() => route.path, () => {
  drawerVisible.value = false
})

watch(isTablet, (tablet) => {
  if (tablet) {
    collapsed.value = true
  }
}, { immediate: true })
</script>

<style scoped>
.responsive-layout {
  display: flex;
  height: 100vh;
  height: 100dvh;
  min-height: 0;
  overflow: hidden;
  background: transparent;
  transition: background-color 0.3s ease;
}

/* 侧边栏 */
.layout-sidebar {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  width: 260px;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: var(--workspace-rail, #243044);
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 8px 0 22px rgba(15, 23, 42, 0.08);
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.3s ease;
  z-index: 100;
  position: relative;
}

.layout-sidebar.mobile {
  width: 100%;
  border-right: none;
}

.sidebar-collapsed .layout-sidebar {
  width: 64px;
}

.layout-tablet .layout-sidebar {
  width: 72px;
}

.layout-tablet .layout-sidebar .sidebar-header {
  justify-content: center;
  padding-inline: 10px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  min-height: 64px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #e5edf6;
}

.logo :deep(.el-icon) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: rgba(15, 118, 110, 0.16);
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: #f8fafc;
  white-space: nowrap;
  overflow: hidden;
}

.collapse-btn {
  transition: transform 0.3s ease;
}

.collapse-btn:hover {
  transform: scale(1.1);
}

.sidebar-user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 10px 10px 8px;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  cursor: pointer;
  transition: background-color 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
}

.sidebar-user-card:hover {
  transform: translateY(-1px);
  border-color: rgba(91, 184, 170, 0.28);
  background: rgba(255, 255, 255, 0.08);
}

.sidebar-user-card.collapsed {
  justify-content: center;
  margin: 10px 8px 8px;
  padding: 8px 0;
}

.sidebar-user-avatar {
  flex: 0 0 auto;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.12);
  color: #e5edf6;
}

.sidebar-user-meta {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.sidebar-user-name {
  overflow: hidden;
  color: #f8fafc;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.15;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-user-role {
  color: #aebdcb;
  font-size: 12px;
  line-height: 1.15;
}

.mobile-user-card {
  margin: 10px 12px;
}

.sidebar-content {
  flex: 1;
  overflow: hidden;
}

/* 菜单样式 */
.sidebar-menu {
  border-right: none;
  padding: 8px 0;
  background: transparent;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 100%;
}

.sidebar-menu :deep(.el-menu-item) {
  height: 48px;
  line-height: 48px;
  margin: 4px 8px;
  border-radius: 8px;
  color: #d6deea;
  transition: color 0.18s ease, background-color 0.18s ease;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  color: #ffffff;
  background-color: rgba(255, 255, 255, 0.06);
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: rgba(47, 93, 140, 0.24);
  color: #ffffff;
  font-weight: 600;
}

.sidebar-menu :deep(.el-menu-item.is-active::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 22px;
  background: #5bb8aa;
  border-radius: 0 2px 2px 0;
}

.sidebar-menu :deep(.el-sub-menu__title) {
  height: 48px;
  line-height: 48px;
  margin: 4px 8px;
  border-radius: 8px;
  color: #d6deea;
  transition: color 0.18s ease, background-color 0.18s ease;
}

.sidebar-menu :deep(.el-sub-menu__title:hover) {
  color: #ffffff;
  background-color: rgba(255, 255, 255, 0.06);
}

.menu-badge {
  margin-left: auto;
}

.menu-badge.warning :deep(.el-badge__content) {
  background-color: var(--color-warning, #F39C12);
}

.sidebar-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  min-height: 56px;
}

.sidebar-logout {
  color: #d6deea;
  border-radius: 8px;
}

.sidebar-logout:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.08);
}

/* 主内容区 */
.layout-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

.mobile-header {
  position: sticky;
  top: 0;
  z-index: 50;
  padding: calc(8px + env(safe-area-inset-top, 0px)) 12px 8px;
  background: linear-gradient(180deg, rgba(238, 243, 247, 0.94), rgba(238, 243, 247, 0));
  backdrop-filter: blur(8px);
  pointer-events: none;
}

.mobile-header-shell {
  pointer-events: auto;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 42px;
  align-items: center;
  gap: 8px;
  min-height: 52px;
  padding: 6px;
  border: 1px solid rgba(216, 224, 234, 0.78);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(16px);
}

.menu-btn {
  width: 40px;
  min-height: 40px;
  border-radius: 12px;
  color: var(--workspace-blue, #2f5d8c);
  transition: background-color 0.18s ease;
}

.menu-btn:hover {
  background: rgba(47, 93, 140, 0.08);
}

.mobile-title-block {
  min-width: 0;
  display: grid;
  gap: 2px;
  text-align: center;
}

.mobile-kicker {
  overflow: hidden;
  color: var(--text-tertiary, #7a8798);
  font-size: 10px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-title {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: var(--text-primary, #303133);
  line-height: 1.15;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mobile-header-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
}

.main-content {
  flex: 1;
  min-height: 0;
  padding: 24px;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  transition: padding 0.3s ease;
}

/* 底部导航 */
.bottom-nav {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 3px;
  padding: 6px;
  background: rgba(255, 255, 255, 0.93);
  border: 1px solid rgba(216, 224, 234, 0.84);
  border-radius: 18px;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.13);
  backdrop-filter: blur(16px);
  position: fixed;
  bottom: calc(8px + env(safe-area-inset-bottom, 0px));
  left: 10px;
  right: 10px;
  z-index: 100;
  transition: background-color 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
  animation: slideUp 0.24s ease;
}

@keyframes slideUp {
  from {
    transform: translateY(100%);
  }
  to {
    transform: translateY(0);
  }
}

.nav-item {
  appearance: none;
  border: 0;
  background: transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  min-width: 0;
  min-height: 54px;
  padding: 5px 4px;
  cursor: pointer;
  font: inherit;
  color: var(--text-secondary, #909399);
  border-radius: 14px;
  transition: color 0.18s ease, background-color 0.18s ease, transform 0.18s ease;
  -webkit-tap-highlight-color: transparent;
}

.nav-icon-shell {
  display: grid;
  place-items: center;
  width: 36px;
  height: 28px;
  border-radius: 999px;
  transition: color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.nav-item:active {
  transform: scale(0.95);
}

.nav-item.active {
  color: var(--workspace-blue, #2f5d8c);
  background: rgba(47, 93, 140, 0.06);
}

.nav-item.active .nav-icon-shell {
  color: #ffffff;
  background: linear-gradient(135deg, var(--workspace-blue, #2f5d8c), var(--workspace-accent, #0f766e));
  box-shadow: 0 8px 18px rgba(47, 93, 140, 0.24);
}

.nav-label {
  font-size: 11px;
  font-weight: 700;
  line-height: 1.2;
  overflow: hidden;
  max-width: 100%;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-badge :deep(.el-badge__content) {
  top: -2px;
  right: -2px;
}

.theme-icon {
  transition: transform 0.3s ease;
}

.nav-item:hover .theme-icon {
  transform: rotate(15deg);
}

/* 移动端抽屉 */
.mobile-drawer :deep(.el-drawer__body) {
  padding: 0;
  height: 100%;
  background: var(--workspace-rail, #243044);
}

.mobile-drawer :deep(.el-drawer) {
  overflow: hidden;
  border-radius: 0 18px 18px 0;
  background: var(--workspace-rail, #243044);
}

/* 过渡动画 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition:
    opacity var(--motion-ui-base, 220ms) var(--motion-ui-ease, cubic-bezier(0.2, 0, 0, 1)),
    transform var(--motion-ui-base, 220ms) var(--motion-ui-ease, cubic-bezier(0.2, 0, 0, 1));
  will-change: transform, opacity;
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translate3d(0, 8px, 0);
}

.fade-slide-enter-to,
.fade-slide-leave-from {
  opacity: 1;
  transform: translate3d(0, 0, 0);
}

/* 响应式 */
@media (max-width: 767px) {
  .layout-sidebar {
    display: none;
  }

  .main-content {
    padding: 16px;
  }
}

@media (max-width: 768px) {
  .main-content {
    padding: 10px 12px;
    padding-bottom: calc(92px + env(safe-area-inset-bottom, 0px));
  }

  .nav-item {
    min-height: 52px;
    padding: 4px 2px;
  }

  .nav-label {
    font-size: 10px;
  }
}

@media (max-width: 380px) {
  .bottom-nav {
    left: 6px;
    right: 6px;
    gap: 2px;
    padding: 5px;
  }

  .nav-icon-shell {
    width: 32px;
  }
}

/* 暗色模式适配 */
[data-theme="dark"] .layout-sidebar {
  background: var(--bg-secondary, #1d1d1d);
  border-color: var(--border-color, #414243);
}

[data-theme="dark"] .sidebar-header,
[data-theme="dark"] .sidebar-footer {
  border-color: var(--border-color, #414243);
}

[data-theme="dark"] .sidebar-menu :deep(.el-menu-item.is-active) {
  background-color: rgba(74, 155, 217, 0.15);
}

[data-theme="dark"] .bottom-nav {
  background: rgba(23, 32, 51, 0.92);
  border-color: var(--border-color, #414243);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.32);
}

[data-theme="dark"] .mobile-header {
  background: linear-gradient(180deg, rgba(17, 24, 39, 0.94), rgba(17, 24, 39, 0));
}

[data-theme="dark"] .mobile-header-shell {
  background: rgba(23, 32, 51, 0.92);
  border-color: var(--border-color, #414243);
  box-shadow: 0 10px 26px rgba(0, 0, 0, 0.28);
}
</style>
