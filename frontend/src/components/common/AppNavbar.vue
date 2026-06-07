<template>
  <nav
    class="app-navbar"
    :class="{
      'app-navbar--scrolled': isScrolled,
      'app-navbar--transparent': !isScrolled && transparent,
      'app-navbar--dark': isDark
    }"
  >
    <div class="navbar-container">
      <!-- Logo -->
      <router-link to="/" class="navbar-brand">
        <el-icon :size="28" class="brand-icon"><Document /></el-icon>
        <span class="brand-text">DocDist</span>
      </router-link>

      <!-- 导航链接（桌面端） -->
      <div class="navbar-nav hide-mobile">
        <router-link
          v-for="link in navLinks"
          :key="link.path"
          :to="link.path"
          class="nav-link"
          :class="{ 'nav-link--active': isActive(link.path) }"
        >
          {{ link.name }}
        </router-link>
      </div>

      <!-- 右侧操作区 -->
      <div class="navbar-actions">
        <!-- 搜索框 -->
        <div class="search-box hide-mobile" v-if="showSearch">
          <el-input
            v-model="searchQuery"
            placeholder="搜索文档..."
            :prefix-icon="Search"
            size="small"
            class="search-input"
            @keyup.enter="handleSearch"
          />
        </div>

        <!-- 主题切换按钮 -->
        <el-tooltip :content="isDark ? '切换到亮色模式' : '切换到暗色模式'" placement="bottom">
          <button class="action-btn theme-toggle" @click="toggleTheme">
            <el-icon :size="18">
              <Sunny v-if="isDark" />
              <Moon v-else />
            </el-icon>
          </button>
        </el-tooltip>

        <!-- 用户菜单（登录后显示） -->
        <template v-if="isLoggedIn">
          <el-dropdown trigger="click" class="user-dropdown">
            <div class="user-trigger">
              <el-avatar :size="32" :src="userAvatar" :icon="UserFilled" class="user-avatar" />
              <span class="user-name hide-mobile">{{ userName }}</span>
              <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="goToProfile">
                  <el-icon><User /></el-icon>
                  个人中心
                </el-dropdown-item>
                <el-dropdown-item @click="goToSettings">
                  <el-icon><Setting /></el-icon>
                  账号设置
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>

        <!-- 登录按钮（未登录时显示） -->
        <template v-else>
          <el-button
            type="primary"
            size="small"
            class="login-btn hide-mobile"
            @click="goToLogin"
          >
            登录
          </el-button>
        </template>

        <!-- 移动端菜单按钮 -->
        <button class="action-btn menu-toggle show-mobile" @click="toggleMobileMenu">
          <el-icon :size="20">
            <Close v-if="mobileMenuOpen" />
            <Menu v-else />
          </el-icon>
        </button>
      </div>
    </div>

    <!-- 移动端菜单 -->
    <transition name="slide-down">
      <div v-show="mobileMenuOpen" class="mobile-menu show-mobile">
        <!-- 移动端搜索 -->
        <div class="mobile-search" v-if="showSearch">
          <el-input
            v-model="searchQuery"
            placeholder="搜索文档..."
            :prefix-icon="Search"
            @keyup.enter="handleSearch"
          />
        </div>

        <!-- 移动端导航链接 -->
        <div class="mobile-nav">
          <router-link
            v-for="link in navLinks"
            :key="link.path"
            :to="link.path"
            class="mobile-nav-link"
            :class="{ 'mobile-nav-link--active': isActive(link.path) }"
            @click="mobileMenuOpen = false"
          >
            {{ link.name }}
          </router-link>
        </div>

        <!-- 移动端用户操作 -->
        <div class="mobile-user-actions" v-if="!isLoggedIn">
          <el-button type="primary" class="mobile-login-btn" @click="goToLogin">
            登录 / 注册
          </el-button>
        </div>
      </div>
    </transition>
  </nav>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { useScroll } from '@/composables/useScroll'
import {
  Document,
  Search,
  Sunny,
  Moon,
  User,
  UserFilled,
  ArrowDown,
  Setting,
  SwitchButton,
  Menu,
  Close
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

// Props
const props = defineProps({
  transparent: {
    type: Boolean,
    default: false
  },
  showSearch: {
    type: Boolean,
    default: true
  }
})

// 路由和状态
const route = useRoute()
const router = useRouter()
const uiStore = useUiStore()
const authStore = useAuthStore()
const { isScrolled } = useScroll()

// 响应式数据
const searchQuery = ref('')
const mobileMenuOpen = ref(false)

// 计算属性
const isDark = computed(() => uiStore.isDark)
const isLoggedIn = computed(() => authStore.isLoggedIn)
const userName = computed(() => authStore.user?.username || '用户')
const userAvatar = computed(() => authStore.user?.avatar || '')

// 导航链接
const navLinks = [
  { name: '首页', path: '/' },
  { name: '项目管理', path: '/admin/projects' },
  { name: '考试安排', path: '/admin/exams' },
  { name: '系统设置', path: '/admin/settings' }
]

// 判断当前路由是否激活
function isActive(path) {
  if (path === '/') {
    return route.path === '/'
  }
  return route.path.startsWith(path)
}

// 切换主题
function toggleTheme() {
  uiStore.toggleTheme()
}

// 切换移动端菜单
function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

// 搜索处理
function handleSearch() {
  if (searchQuery.value.trim()) {
    router.push({
      path: '/admin/projects',
      query: { q: searchQuery.value.trim() }
    })
    searchQuery.value = ''
    mobileMenuOpen.value = false
  }
}

// 跳转到登录页
function goToLogin() {
  router.push('/login')
  mobileMenuOpen.value = false
}

// 跳转到个人中心
function goToProfile() {
  router.push('/profile')
}

// 跳转到设置
function goToSettings() {
  router.push('/admin/settings')
}

// 退出登录
async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await authStore.logout()
    router.push('/login')
  } catch {
    // 用户取消
  }
}
</script>

<style scoped>
.app-navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 64px;
  background-color: var(--bg-secondary, #ffffff);
  border-bottom: 1px solid transparent;
  z-index: 100;
  transition: all var(--transition-normal);
}

.app-navbar--scrolled {
  background-color: var(--bg-secondary, #ffffff);
  border-bottom-color: var(--border-color, #e4e7ed);
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(0, 0, 0, 0.05));
}

.app-navbar--transparent {
  background-color: transparent;
  border-bottom-color: transparent;
}

.app-navbar--transparent .brand-text,
.app-navbar--transparent .nav-link {
  color: #ffffff;
}

.app-navbar--transparent .nav-link:hover {
  color: rgba(255, 255, 255, 0.8);
}

.navbar-container {
  max-width: 1200px;
  height: 100%;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* Logo 区域 */
.navbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  transition: opacity var(--transition-fast);
}

.navbar-brand:hover {
  opacity: 0.8;
}

.brand-icon {
  color: var(--color-primary, #1A5276);
}

.brand-text {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary, #333333);
}

/* 导航链接 */
.navbar-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 auto;
}

.nav-link {
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary, #666666);
  text-decoration: none;
  border-radius: var(--radius-md, 8px);
  transition: all var(--transition-fast);
}

.nav-link:hover {
  color: var(--color-primary, #1A5276);
  background-color: var(--bg-hover, #f0f2f5);
}

.nav-link--active {
  color: var(--color-primary, #1A5276);
  background-color: var(--bg-hover, #f0f2f5);
}

/* 右侧操作区 */
.navbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 搜索框 */
.search-box {
  margin-right: 8px;
}

.search-input {
  width: 200px;
}

.search-input :deep(.el-input__wrapper) {
  background-color: var(--bg-tertiary, #fafafa);
  border-radius: var(--radius-full, 9999px);
  box-shadow: none;
  transition: all var(--transition-fast);
}

.search-input :deep(.el-input__wrapper:hover),
.search-input :deep(.el-input__wrapper.is-focus) {
  background-color: var(--bg-hover, #f0f2f5);
}

/* 操作按钮 */
.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: var(--radius-md, 8px);
  background-color: transparent;
  color: var(--text-secondary, #666666);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.action-btn:hover {
  background-color: var(--bg-hover, #f0f2f5);
  color: var(--color-primary, #1A5276);
}

.theme-toggle:hover {
  transform: rotate(15deg);
}

/* 用户下拉菜单 */
.user-dropdown {
  cursor: pointer;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: var(--radius-md, 8px);
  transition: background-color var(--transition-fast);
}

.user-trigger:hover {
  background-color: var(--bg-hover, #f0f2f5);
}

.user-avatar {
  background-color: var(--color-primary, #1A5276);
  color: #ffffff;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #333333);
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown-icon {
  font-size: 12px;
  color: var(--text-tertiary, #999999);
  transition: transform var(--transition-fast);
}

.user-dropdown:hover .dropdown-icon {
  transform: rotate(180deg);
}

/* 登录按钮 */
.login-btn {
  border-radius: var(--radius-md, 8px);
}

/* 移动端菜单 */
.mobile-menu {
  position: absolute;
  top: 64px;
  left: 0;
  right: 0;
  background-color: var(--bg-secondary, #ffffff);
  border-bottom: 1px solid var(--border-color, #e4e7ed);
  box-shadow: var(--shadow-md, 0 4px 6px rgba(0, 0, 0, 0.07));
  padding: 16px 24px;
  z-index: 99;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all var(--transition-normal);
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.mobile-search {
  margin-bottom: 16px;
}

.mobile-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 16px;
}

.mobile-nav-link {
  padding: 12px 16px;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-secondary, #666666);
  text-decoration: none;
  border-radius: var(--radius-md, 8px);
  transition: all var(--transition-fast);
}

.mobile-nav-link:hover {
  background-color: var(--bg-hover, #f0f2f5);
  color: var(--color-primary, #1A5276);
}

.mobile-nav-link--active {
  color: var(--color-primary, #1A5276);
  background-color: var(--bg-hover, #f0f2f5);
}

.mobile-user-actions {
  padding-top: 16px;
  border-top: 1px solid var(--border-color, #e4e7ed);
}

.mobile-login-btn {
  width: 100%;
  border-radius: var(--radius-md, 8px);
}

/* 响应式 */
@media (max-width: 768px) {
  .navbar-container {
    padding: 0 16px;
  }

  .brand-text {
    font-size: 20px;
  }

  .hide-mobile {
    display: none !important;
  }

  .show-mobile {
    display: flex !important;
  }
}

@media (min-width: 769px) {
  .show-mobile {
    display: none !important;
  }
}
</style>
