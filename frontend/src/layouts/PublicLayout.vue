<template>
  <div class="public-layout">
    <!-- 导航栏 -->
    <header class="public-header" :class="{ 'scrolled': isScrolled }">
      <div class="header-container">
        <div class="header-left">
          <router-link to="/" class="logo">
            <el-icon :size="32" color="var(--workspace-blue, #2f5d8c)"><DocumentChecked /></el-icon>
            <span class="logo-text">DocShop</span>
          </router-link>
          
          <!-- PC端导航菜单 -->
          <nav v-if="isDesktop" class="header-nav">
            <router-link to="/" class="nav-link" :class="{ active: $route.path === '/' }">首页</router-link>
            <router-link to="/#features" class="nav-link">功能</router-link>
            <router-link to="/#pricing" class="nav-link">价格</router-link>
            <router-link to="/#about" class="nav-link">关于</router-link>
          </nav>
        </div>

        <div class="header-right">
          <template v-if="isLoggedIn">
            <el-dropdown trigger="click">
              <div class="user-menu">
                <el-avatar :size="32" :icon="UserFilled" />
                <span class="username">{{ username }}</span>
                <el-icon><ArrowDown /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="$router.push('/profile')">个人中心</el-dropdown-item>
                  <el-dropdown-item @click="$router.push('/admin')">管理后台</el-dropdown-item>
                  <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <el-button v-if="isDesktop" text @click="$router.push('/login')">登录</el-button>
            <el-button v-if="isDesktop" type="primary" @click="$router.push('/login')">免费注册</el-button>
          </template>
          
          <!-- 移动端菜单按钮 -->
          <el-button v-if="!isDesktop" text :icon="Menu" @click="mobileMenuVisible = true" class="menu-btn" />
        </div>
      </div>
    </header>

    <!-- 移动端菜单抽屉 -->
    <el-drawer
      v-model="mobileMenuVisible"
      direction="rtl"
      :size="280"
      :with-header="false"
      class="mobile-menu-drawer"
    >
      <div class="mobile-menu">
        <div class="mobile-menu-header">
          <div class="logo">
            <el-icon :size="32" color="var(--workspace-blue, #2f5d8c)"><DocumentChecked /></el-icon>
            <span class="logo-text">DocShop</span>
          </div>
          <el-button text :icon="Close" @click="mobileMenuVisible = false" />
        </div>
        
        <nav class="mobile-nav">
          <router-link to="/" class="mobile-nav-link" @click="mobileMenuVisible = false">首页</router-link>
          <router-link to="/#features" class="mobile-nav-link" @click="mobileMenuVisible = false">功能</router-link>
          <router-link to="/#pricing" class="mobile-nav-link" @click="mobileMenuVisible = false">价格</router-link>
          <router-link to="/#about" class="mobile-nav-link" @click="mobileMenuVisible = false">关于</router-link>
        </nav>

        <div class="mobile-menu-footer">
          <template v-if="isLoggedIn">
            <el-button type="primary" class="mobile-btn" @click="$router.push('/admin'); mobileMenuVisible = false">进入后台</el-button>
            <el-button class="mobile-btn" @click="logout">退出登录</el-button>
          </template>
          <template v-else>
            <el-button type="primary" class="mobile-btn" @click="$router.push('/login'); mobileMenuVisible = false">登录 / 注册</el-button>
          </template>
        </div>
      </div>
    </el-drawer>

    <!-- 主内容区 -->
    <main class="public-main">
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in" appear>
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- 页脚 -->
    <footer class="public-footer">
      <div class="footer-container">
        <div class="footer-grid">
          <div class="footer-brand">
            <div class="logo">
              <el-icon :size="28" color="var(--workspace-blue, #2f5d8c)"><DocumentChecked /></el-icon>
              <span class="logo-text">DocShop</span>
            </div>
            <p class="footer-desc">智能文档版本管理系统，让文档协作更高效、更安全。</p>
            <div class="footer-social">
              <el-button circle text :icon="Message" />
              <el-button circle text :icon="Platform" />
              <el-button circle text :icon="ChatDotRound" />
            </div>
          </div>
          
          <div class="footer-links">
            <h4>产品</h4>
            <router-link to="/">功能介绍</router-link>
            <router-link to="/">价格方案</router-link>
            <router-link to="/">更新日志</router-link>
            <router-link to="/">API文档</router-link>
          </div>
          
          <div class="footer-links">
            <h4>支持</h4>
            <router-link to="/">帮助中心</router-link>
            <router-link to="/">使用指南</router-link>
            <router-link to="/">常见问题</router-link>
            <router-link to="/">联系我们</router-link>
          </div>
          
          <div class="footer-links">
            <h4>关于</h4>
            <router-link to="/">关于我们</router-link>
            <router-link to="/">加入我们</router-link>
            <router-link to="/">隐私政策</router-link>
            <router-link to="/">服务条款</router-link>
          </div>
        </div>
        
        <div class="footer-bottom">
          <p>&copy; 2024 DocShop. All rights reserved.</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  DocumentChecked, UserFilled, ArrowDown, Menu, Close,
  Message, Platform, ChatDotRound
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useResponsive } from '@/composables/useResponsive'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const { isDesktop } = useResponsive()

const isScrolled = ref(false)
const mobileMenuVisible = ref(false)

const isLoggedIn = computed(() => authStore.isLoggedIn)
const username = computed(() => authStore.user?.username || '用户')

function handleScroll() {
  isScrolled.value = window.scrollY > 50
}

function logout() {
  authStore.logout()
  ElMessage.success('已退出登录')
  mobileMenuVisible.value = false
  router.push('/')
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.public-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary, #f5f7fa);
}

/* 导航栏 */
.public-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  transition: background-color 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
  background: transparent;
}

.public-header.scrolled {
  background: var(--bg-secondary, rgba(255, 255, 255, 0.95));
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.08);
}

.header-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 48px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
}

.logo-text {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary, #303133);
  letter-spacing: 0;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 32px;
}

.nav-link {
  font-size: 15px;
  color: var(--text-secondary, #606266);
  text-decoration: none;
  transition: color 0.3s ease;
  position: relative;
}

.nav-link:hover,
.nav-link.active {
  color: var(--workspace-blue, #2f5d8c);
}

.nav-link::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 0;
  width: 0;
  height: 2px;
  background: var(--workspace-accent, #0f766e);
  transition: width 0.3s ease;
}

.nav-link:hover::after,
.nav-link.active::after {
  width: 100%;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.user-menu:hover {
  background-color: var(--bg-hover, #f5f7fa);
}

.username {
  font-size: 14px;
  color: var(--text-primary, #303133);
}

.menu-btn {
  font-size: 20px;
}

/* 移动端菜单 */
.mobile-menu {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.mobile-menu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--border-color, #e4e7ed);
}

.mobile-nav {
  flex: 1;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mobile-nav-link {
  padding: 12px 16px;
  font-size: 16px;
  color: var(--text-primary, #303133);
  text-decoration: none;
  border-radius: 8px;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.mobile-nav-link:hover {
  background-color: var(--bg-hover, #f5f7fa);
  color: var(--workspace-blue, #2f5d8c);
}

.mobile-menu-footer {
  padding: 16px;
  border-top: 1px solid var(--border-color, #e4e7ed);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mobile-btn {
  width: 100%;
}

/* 主内容区 */
.public-main {
  flex: 1;
  padding-top: 64px;
}

/* 页脚 */
.public-footer {
  background: var(--bg-secondary, #ffffff);
  border-top: 1px solid var(--border-color, #e4e7ed);
  padding: 60px 24px 24px;
}

.footer-container {
  max-width: 1200px;
  margin: 0 auto;
}

.footer-grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 48px;
  margin-bottom: 48px;
}

.footer-brand .logo {
  margin-bottom: 16px;
}

.footer-desc {
  font-size: 14px;
  color: var(--text-secondary, #606266);
  line-height: 1.6;
  margin-bottom: 20px;
  max-width: 280px;
}

.footer-social {
  display: flex;
  gap: 12px;
}

.footer-links h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #303133);
  margin: 0 0 16px;
}

.footer-links {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.footer-links a {
  font-size: 14px;
  color: var(--text-secondary, #606266);
  text-decoration: none;
  transition: color 0.2s ease;
}

.footer-links a:hover {
  color: var(--workspace-blue, #2f5d8c);
}

.footer-bottom {
  text-align: center;
  padding-top: 24px;
  border-top: 1px solid var(--border-color, #e4e7ed);
}

.footer-bottom p {
  font-size: 13px;
  color: var(--text-secondary, #909399);
  margin: 0;
}

/* 响应式适配 */
@media (max-width: 992px) {
  .footer-grid {
    grid-template-columns: 1fr 1fr;
    gap: 32px;
  }
}

@media (max-width: 576px) {
  .header-container {
    padding: 12px 16px;
  }

  .logo-text {
    font-size: 18px;
  }

  .footer-grid {
    grid-template-columns: 1fr;
    gap: 32px;
  }

  .public-footer {
    padding: 40px 16px 24px;
  }
}

/* 暗色模式适配 */
[data-theme="dark"] .public-header.scrolled {
  background: var(--bg-secondary, rgba(29, 29, 29, 0.95));
}

[data-theme="dark"] .public-footer {
  background: var(--bg-secondary, #1d1d1d);
  border-color: var(--border-color, #414243);
}

[data-theme="dark"] .footer-bottom {
  border-color: var(--border-color, #414243);
}
</style>
