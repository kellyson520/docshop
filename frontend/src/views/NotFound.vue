<template>
  <main class="not-found-page">
    <section class="not-found-card" aria-labelledby="not-found-title">
      <div class="not-found-copy">
        <p class="not-found-kicker">DOCSHOP / 404</p>
        <h1 id="not-found-title">这份文档走丢了</h1>
        <p class="not-found-desc">
          你访问的页面可能已被移动、删除，或者链接里少了一段令牌。我们已经把档案柜翻了一遍，但没找到它。
        </p>

        <div class="not-found-path">
          <span>当前路径</span>
          <code>{{ currentPath }}</code>
        </div>

        <div class="not-found-actions">
          <el-button type="primary" size="large" @click="goHome">
            <el-icon><HomeFilled /></el-icon>
            回到首页
          </el-button>
          <el-button size="large" @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            返回上一页
          </el-button>
          <el-button text size="large" @click="reloadPage">
            <el-icon><RefreshRight /></el-icon>
            重新检查
          </el-button>
        </div>
      </div>

      <div class="not-found-illustration" aria-hidden="true">
        <div class="archive-cabinet">
          <div class="cabinet-top">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <div class="cabinet-drawer drawer-one">
            <i></i>
            <b>DOC</b>
          </div>
          <div class="cabinet-drawer drawer-two">
            <i></i>
            <b>404</b>
          </div>
          <div class="cabinet-drawer drawer-three">
            <i></i>
            <b>PDF</b>
          </div>
        </div>
        <div class="lost-paper paper-a">?</div>
        <div class="lost-paper paper-b">v?</div>
        <div class="search-light"></div>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, HomeFilled, RefreshRight } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const currentPath = computed(() => route.fullPath || window.location.pathname || '/')

function goHome() {
  router.push('/')
}

function goBack() {
  if (window.history.length > 1) {
    router.back()
    return
  }
  goHome()
}

function reloadPage() {
  window.location.reload()
}
</script>

<style scoped>
.not-found-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: clamp(18px, 4vw, 48px);
  color: #172033;
  background:
    radial-gradient(circle at 14% 18%, rgba(15, 118, 110, 0.18), transparent 28%),
    radial-gradient(circle at 86% 16%, rgba(47, 93, 140, 0.18), transparent 30%),
    linear-gradient(135deg, #f8fafc 0%, #eef3f7 54%, #edf4f1 100%);
}

.not-found-card {
  width: min(1100px, 100%);
  min-height: 560px;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(320px, 0.95fr);
  gap: clamp(24px, 5vw, 64px);
  align-items: center;
  position: relative;
  overflow: hidden;
  padding: clamp(28px, 5vw, 64px);
  border: 1px solid rgba(255, 255, 255, 0.76);
  border-radius: 34px;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 28px 90px rgba(23, 32, 51, 0.14);
  backdrop-filter: blur(18px);
  animation: notFoundIn 260ms cubic-bezier(0.2, 0, 0, 1) both;
}

.not-found-card::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(23, 32, 51, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(23, 32, 51, 0.045) 1px, transparent 1px);
  background-size: 34px 34px;
  mask-image: linear-gradient(to bottom, black, transparent 74%);
}

.not-found-copy,
.not-found-illustration {
  position: relative;
  z-index: 1;
}

.not-found-kicker {
  margin: 0 0 16px;
  color: #0f766e;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.22em;
}

h1 {
  max-width: 640px;
  margin: 0;
  color: #101827;
  font-size: clamp(42px, 7vw, 78px);
  line-height: 0.98;
  letter-spacing: -0.065em;
}

.not-found-desc {
  max-width: 620px;
  margin: 22px 0 0;
  color: #536072;
  font-size: 16px;
  line-height: 1.8;
}

.not-found-path {
  width: min(620px, 100%);
  margin: 30px 0;
  padding: 14px 16px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.76);
}

.not-found-path span {
  display: block;
  margin-bottom: 7px;
  color: #7a8798;
  font-size: 12px;
  font-weight: 700;
}

.not-found-path code {
  display: block;
  overflow-wrap: anywhere;
  color: #243044;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.not-found-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.not-found-illustration {
  min-height: 380px;
  display: grid;
  place-items: center;
}

.archive-cabinet {
  width: min(360px, 80vw);
  padding: 18px;
  border: 1px solid rgba(47, 93, 140, 0.18);
  border-radius: 28px;
  background: linear-gradient(145deg, #2f5d8c, #243044);
  box-shadow: 0 30px 70px rgba(36, 48, 68, 0.28);
  transform: rotate(-2deg);
}

.cabinet-top {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.cabinet-top span {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.42);
}

.cabinet-drawer {
  height: 82px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding: 0 22px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 18px;
  color: #e5edf6;
  background: rgba(255, 255, 255, 0.1);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.16);
}

.drawer-two {
  transform: translateX(28px);
  background: rgba(15, 118, 110, 0.24);
}

.cabinet-drawer i {
  width: 70px;
  height: 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.46);
}

.cabinet-drawer b {
  font-size: 22px;
  letter-spacing: 0.08em;
}

.lost-paper {
  position: absolute;
  display: grid;
  place-items: center;
  border: 1px solid rgba(47, 93, 140, 0.16);
  border-radius: 14px;
  color: #2f5d8c;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 14px 34px rgba(23, 32, 51, 0.14);
  font-weight: 900;
}

.paper-a {
  top: 42px;
  right: 42px;
  width: 72px;
  height: 92px;
  transform: rotate(12deg);
  animation: floatPaper 4.8s ease-in-out infinite;
}

.paper-b {
  bottom: 46px;
  left: 34px;
  width: 82px;
  height: 62px;
  transform: rotate(-10deg);
  animation: floatPaper 5.6s ease-in-out 0.4s infinite;
}

.search-light {
  position: absolute;
  right: 8%;
  bottom: 8%;
  width: 180px;
  height: 180px;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(15, 118, 110, 0.14), transparent 68%);
  animation: pulseLight 3.4s ease-in-out infinite;
}

@keyframes notFoundIn {
  from {
    opacity: 0;
    transform: translate3d(0, 10px, 0);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

@keyframes floatPaper {
  0%,
  100% {
    translate: 0 0;
  }
  50% {
    translate: 0 -10px;
  }
}

@keyframes pulseLight {
  0%,
  100% {
    opacity: 0.72;
    transform: scale(0.96);
  }
  50% {
    opacity: 1;
    transform: scale(1.04);
  }
}

@media (max-width: 860px) {
  .not-found-card {
    min-height: auto;
    grid-template-columns: 1fr;
  }

  .not-found-illustration {
    min-height: 300px;
    order: -1;
  }
}

@media (max-width: 560px) {
  .not-found-page {
    padding: 14px;
  }

  .not-found-card {
    padding: 24px;
    border-radius: 24px;
  }

  .not-found-actions {
    display: grid;
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .not-found-card,
  .lost-paper,
  .search-light {
    animation: none !important;
    transform: none !important;
  }
}
</style>
