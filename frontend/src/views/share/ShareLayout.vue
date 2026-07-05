<template>
  <div class="share-layout" :class="{ 'share-layout--preview': isPreviewRoute }">
    <header v-if="!isPreviewRoute" class="share-header">
      <router-link to="/" class="logo">
        <el-icon :size="22"><Document /></el-icon>
        <span class="logo-text">DocShop</span>
      </router-link>

      <div class="header-toolbar" data-testid="share-header-toolbar">
        <el-button text size="small" class="back-button" @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>

        <button
          type="button"
          class="theme-toggle"
          :aria-label="themeToggleLabel"
          :title="themeToggleLabel"
          @click="toggleTheme"
        >
          <el-icon :size="18">
            <Sunny v-if="isDark" />
            <Moon v-else />
          </el-icon>
        </button>
      </div>
    </header>

    <main class="share-main" :class="{ 'share-main--preview': isPreviewRoute }">
      <router-view />
    </main>

    <footer v-if="!isPreviewRoute" class="share-footer">
      <p>&copy; {{ currentYear }} DocShop. All rights reserved.</p>
    </footer>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute } from 'vue-router'
import { useUiStore } from '@/stores/ui'
import { Document, Sunny, Moon, ArrowLeft } from '@element-plus/icons-vue'
import { useShareSession } from '@/composables/useShareSession'

const route = useRoute()
const uiStore = useUiStore()
const isDark = computed(() => uiStore.isDark)
const currentYear = computed(() => new Date().getFullYear())
const themeToggleLabel = computed(() => (isDark.value ? '切换到亮色模式' : '切换到暗色模式'))
const isPreviewRoute = computed(() => String(route.path || '').includes('/preview/'))
const shareToken = computed(() => String(route.params?.token || '').trim())
const activeShareSession = ref(null)
let heartbeatTimer = null

function clearHeartbeatTimer() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

function syncShareSession(token) {
  activeShareSession.value = token ? useShareSession(token) : null
}

function startHeartbeat() {
  clearHeartbeatTimer()
  if (typeof window === 'undefined') return

  const session = activeShareSession.value
  if (!session?.grantToken?.value) return

  heartbeatTimer = window.setInterval(() => {
    session.heartbeat().catch(() => {})
  }, 30000)
}

function toggleTheme() {
  uiStore.toggleTheme()
}

function releaseShareGrantOnPageHide() {
  activeShareSession.value?.releaseOnPageHide?.()
}

onMounted(() => {
  uiStore.initTheme()
  if (typeof window !== 'undefined') {
    window.addEventListener('pagehide', releaseShareGrantOnPageHide)
    window.addEventListener('beforeunload', releaseShareGrantOnPageHide)
  }
})

watch(shareToken, (token) => {
  syncShareSession(token)
}, { immediate: true })

watch(() => activeShareSession.value?.grantToken?.value, () => {
  startHeartbeat()
}, { immediate: true })

onBeforeRouteLeave(async (to) => {
  if (!shareToken.value) return
  if (String(to.path || '').startsWith('/s/')) return
  await activeShareSession.value?.release?.().catch(() => {})
})

onBeforeUnmount(() => {
  clearHeartbeatTimer()
  if (typeof window !== 'undefined') {
    window.removeEventListener('pagehide', releaseShareGrantOnPageHide)
    window.removeEventListener('beforeunload', releaseShareGrantOnPageHide)
  }
})
</script>

<style scoped>
.share-layout {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background:
    linear-gradient(90deg, rgba(47, 93, 140, 0.025) 1px, transparent 1px),
    linear-gradient(180deg, var(--bg-primary, #f7fafc) 0%, var(--bg-secondary, #edf3f8) 100%);
  background-size: 32px 32px, auto;
}

.share-header {
  background: color-mix(in srgb, var(--bg-secondary, #fff) 90%, transparent);
  border-bottom: 1px solid var(--border-color-light, #e4e9f0);
  box-shadow: none;
  backdrop-filter: blur(10px);
  padding: 0 24px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  column-gap: 12px;
  height: 56px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--workspace-blue, #2f5d8c);
  text-decoration: none;
  transition: opacity var(--transition-fast);
}

.logo-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logo:hover {
  opacity: 0.8;
}

.header-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-width: fit-content;
}

.back-button {
  min-width: 72px;
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary, #475569);
  flex-shrink: 0;
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
  flex-shrink: 0;
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

.share-main--preview {
  max-width: none;
  margin: 0;
  padding: 0;
}

.share-footer {
  background: color-mix(in srgb, var(--bg-secondary, #fff) 82%, transparent);
  border-top: 1px solid var(--border-color-light, #e4e9f0);
  padding: 16px 24px;
  text-align: center;
}

.share-footer p {
  margin: 0;
  font-size: 13px;
  color: var(--text-tertiary, #999999);
}

@media (max-width: 768px) {
  .share-header {
    min-height: calc(56px + env(safe-area-inset-top));
    height: auto;
    padding:
      env(safe-area-inset-top)
      max(14px, env(safe-area-inset-right))
      0
      max(14px, env(safe-area-inset-left));
    column-gap: 8px;
  }

  .share-main {
    margin: 12px auto 16px;
    padding: 0 max(12px, env(safe-area-inset-right)) 0 max(12px, env(safe-area-inset-left));
  }

  .logo {
    font-size: 18px;
  }

  .header-toolbar {
    gap: 6px;
  }

  .back-button {
    min-width: 64px;
    padding: 6px 8px;
  }

  .theme-toggle {
    width: 38px;
    height: 38px;
  }
}

@media (max-width: 480px) {
  .share-header {
    grid-template-columns: minmax(0, 1fr);
    grid-auto-rows: auto;
    row-gap: 8px;
    padding-bottom: 8px;
  }

  .header-toolbar {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
