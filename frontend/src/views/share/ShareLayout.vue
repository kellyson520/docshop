<template>
  <div class="share-layout">
    <!-- 顶部栏 -->
    <header class="share-header">
      <router-link to="/" class="logo">
        <el-icon :size="22"><Document /></el-icon>
        <span>DocDist</span>
      </router-link>
      <div class="header-actions">
        <el-button text size="small" @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <button class="theme-toggle" @click="toggleTheme" :title="isDark ? '切换到亮色模式' : '切换到暗色模式'">
          <el-icon :size="18">
            <Sunny v-if="isDark" />
            <Moon v-else />
          </el-icon>
        </button>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="share-main">
      <router-view />
    </main>

    <!-- 页脚 -->
    <footer class="share-footer">
      <p>&copy; {{ currentYear }} DocDist. All rights reserved.</p>
    </footer>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useUiStore } from '@/stores/ui'
import { Document, Sunny, Moon, ArrowLeft } from '@element-plus/icons-vue'

const uiStore = useUiStore()
const isDark = computed(() => uiStore.isDark)
const currentYear = computed(() => new Date().getFullYear())

function toggleTheme() {
  uiStore.toggleTheme()
}
</script>

<style scoped>
.share-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    linear-gradient(90deg, rgba(47, 93, 140, 0.025) 1px, transparent 1px),
    linear-gradient(180deg, #f7fafc 0%, #edf3f8 100%);
  background-size: 32px 32px, auto;
}

.share-header {
  background: rgba(255, 255, 255, 0.9);
  border-bottom: 1px solid var(--border-color-light, #e4e9f0);
  box-shadow: none;
  backdrop-filter: blur(10px);
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 700;
  color: var(--workspace-blue, #2f5d8c);
  text-decoration: none;
  transition: opacity var(--transition-fast);
}

.logo:hover {
  opacity: 0.8;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.theme-toggle {
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
  transition: background-color 0.16s ease, color 0.16s ease;
}

.theme-toggle:hover {
  background-color: var(--bg-hover, #f0f2f5);
  color: var(--workspace-blue, #2f5d8c);
  transform: none;
}

.share-main {
  flex: 1;
  max-width: 1200px;
  width: 100%;
  margin: 28px auto;
  padding: 0 24px;
}

.share-footer {
  background: rgba(255, 255, 255, 0.82);
  border-top: 1px solid var(--border-color-light, #e4e9f0);
  padding: 16px 24px;
  text-align: center;
}

.share-footer p {
  margin: 0;
  font-size: 13px;
  color: var(--text-tertiary, #999999);
}

/* 响应式适配 */
@media (max-width: 768px) {
  .share-header {
    padding: 0 16px;
  }

  .share-main {
    margin: 16px auto;
    padding: 0 16px;
  }

  .logo {
    font-size: 18px;
  }
}
</style>
