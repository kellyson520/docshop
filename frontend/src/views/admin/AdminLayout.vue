<template>
  <el-container class="admin-layout">
    <!-- 侧边栏 -->
    <el-aside width="220px" class="admin-aside">
      <div class="aside-logo">
        <el-icon :size="24"><Document /></el-icon>
        <span class="logo-text">DocDist</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#1A5276"
        text-color="#ffffffb3"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/admin/dashboard">
          <el-icon><DataBoard /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/admin/projects">
          <el-icon><Folder /></el-icon>
          <span>项目管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <!-- 顶部栏 -->
      <el-header class="admin-header">
        <div class="header-left">
          <span class="header-title">DocDist 管理后台</span>
        </div>
        <div class="header-right">
          <span class="username">{{ authStore.user?.username || '用户' }}</span>
          <el-button type="danger" text @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
            退出
          </el-button>
        </div>
      </el-header>

      <!-- 主内容区 -->
      <el-main class="admin-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/admin/projects')) return '/admin/projects'
  if (path.startsWith('/admin/settings')) return '/admin/settings'
  if (path.startsWith('/admin/dashboard')) return '/admin/dashboard'
  return path
})

function handleLogout() {
  authStore.logout()
}

onMounted(async () => {
  if (authStore.isLoggedIn && !authStore.user) {
    await authStore.fetchUser()
  }
})
</script>

<style scoped>
.admin-layout {
  height: 100vh;
}

.admin-aside {
  background-color: #1A5276;
  overflow: hidden;
}

.aside-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 56px;
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  border-bottom: 1px solid #ffffff1a;
}

.logo-text {
  letter-spacing: 1px;
}

.admin-aside .el-menu {
  border-right: none;
}

.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  padding: 0 20px;
  height: 56px;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.username {
  color: #666;
  font-size: 14px;
}

.admin-main {
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>
