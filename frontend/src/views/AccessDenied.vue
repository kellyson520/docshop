<template>
  <main class="gate-page">
    <section class="gate-shell">
      <div class="gate-card">
        <div class="status-orbit" aria-hidden="true">
          <span class="status-dot"></span>
          <span class="status-ring"></span>
        </div>

        <p class="eyebrow">GLOBAL ACCESS GATE</p>
        <h1>当前访问未通过门禁</h1>
        <p class="lead">
          系统没有检测到有效登录状态，也没有在访问链接中发现管理员分发的访问 token。
        </p>

        <div class="reason-panel">
          <div>
            <span class="label">拦截原因</span>
            <strong>{{ reasonText }}</strong>
          </div>
          <div>
            <span class="label">原始地址</span>
            <code>{{ redirectTarget }}</code>
          </div>
        </div>

        <div class="guide-grid">
          <article>
            <span>01</span>
            <h2>登录账号</h2>
            <p>已有账号的用户请登录后继续访问后台、项目和文件详情。</p>
          </article>
          <article>
            <span>02</span>
            <h2>使用访问 token</h2>
            <p>未登录访问需要链接携带 token、access_token 或有效分享令牌。</p>
          </article>
        </div>

        <div class="actions">
          <button class="primary" type="button" @click="goLogin">去登录</button>
          <button type="button" @click="retry">刷新验证</button>
          <button type="button" @click="goHome">返回首页</button>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

function safeRedirectTarget(value) {
  return typeof value === 'string' && /^\/[^\/]/.test(value) ? value : '/'
}

const redirectTarget = computed(() => safeRedirectTarget(route.query.redirect))

const reasonText = computed(() => {
  const reason = route.query.reason
  if (reason === 'missing_credentials') return '未登录，且未携带访问 token'
  if (reason === 'invalid_token') return '访问 token 无效或已失效'
  return '访问凭据不符合当前门禁策略'
})

function goLogin() {
  router.push({ path: '/login', query: { redirect: redirectTarget.value } })
}

function retry() {
  router.replace(safeRedirectTarget(route.query.redirect))
}

function goHome() {
  router.push('/')
}
</script>

<style scoped>
.gate-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 28px;
  color: #182033;
  background:
    radial-gradient(circle at 18% 12%, rgba(255, 196, 87, 0.28), transparent 28%),
    radial-gradient(circle at 82% 18%, rgba(70, 112, 255, 0.2), transparent 30%),
    linear-gradient(135deg, #f8fafc 0%, #eef3f8 46%, #f7efe5 100%);
}

.gate-shell {
  width: min(960px, 100%);
  position: relative;
}

.gate-card {
  position: relative;
  overflow: hidden;
  padding: clamp(28px, 5vw, 56px);
  border: 1px solid rgba(255, 255, 255, 0.74);
  border-radius: 34px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 28px 90px rgba(34, 43, 69, 0.16);
  backdrop-filter: blur(22px);
}

.gate-card::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(24, 32, 51, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(24, 32, 51, 0.045) 1px, transparent 1px);
  background-size: 34px 34px;
  mask-image: linear-gradient(to bottom, black, transparent 72%);
}

.status-orbit {
  position: absolute;
  right: clamp(24px, 5vw, 54px);
  top: clamp(24px, 5vw, 54px);
  width: 88px;
  height: 88px;
}

.status-ring,
.status-dot {
  position: absolute;
  inset: 0;
  border-radius: 50%;
}

.status-ring {
  border: 1px dashed rgba(239, 68, 68, 0.48);
  animation: rotate 14s linear infinite;
}

.status-dot {
  inset: 28px;
  background: linear-gradient(135deg, #ef4444, #f97316);
  box-shadow: 0 0 34px rgba(239, 68, 68, 0.34);
}

.eyebrow {
  margin: 0 0 14px;
  color: #dc2626;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.22em;
}

h1 {
  max-width: 680px;
  margin: 0;
  font-size: clamp(34px, 7vw, 72px);
  line-height: 0.98;
  letter-spacing: -0.06em;
}

.lead {
  max-width: 660px;
  margin: 22px 0 0;
  color: #536072;
  font-size: 17px;
  line-height: 1.75;
}

.reason-panel {
  display: grid;
  grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr);
  gap: 14px;
  margin: 32px 0;
}

.reason-panel > div,
.guide-grid article {
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.62);
}

.reason-panel > div {
  padding: 18px;
}

.label {
  display: block;
  margin-bottom: 8px;
  color: #8b97a8;
  font-size: 12px;
}

strong {
  color: #111827;
}

code {
  display: block;
  overflow-wrap: anywhere;
  color: #334155;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.guide-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.guide-grid article {
  padding: 20px;
}

.guide-grid span {
  color: #f97316;
  font-weight: 900;
}

.guide-grid h2 {
  margin: 10px 0 6px;
  font-size: 18px;
}

.guide-grid p {
  margin: 0;
  color: #64748b;
  line-height: 1.65;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 32px;
}

button {
  min-height: 44px;
  padding: 0 20px;
  border: 1px solid rgba(100, 116, 139, 0.22);
  border-radius: 999px;
  color: #263246;
  background: rgba(255, 255, 255, 0.76);
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}

button:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
}

button.primary {
  border-color: transparent;
  color: white;
  background: linear-gradient(135deg, #1d4ed8, #0f172a);
}

@keyframes rotate {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 720px) {
  .gate-page {
    padding: 16px;
    place-items: stretch;
  }

  .gate-shell {
    display: grid;
    align-items: center;
    min-height: calc(100vh - 32px);
  }

  .status-orbit {
    opacity: 0.32;
  }

  .reason-panel,
  .guide-grid {
    grid-template-columns: 1fr;
  }

  .actions button {
    flex: 1 1 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .status-ring,
  button {
    animation: none !important;
    transition-duration: 1ms !important;
    transform: none !important;
  }
}
</style>
