<template>
  <div class="error-boundary">
    <div v-if="error" class="error-boundary__container">
      <div class="error-boundary__mascot" aria-hidden="true">
        <div class="error-boundary__paper">
          <span>!</span>
        </div>
        <div class="error-boundary__shadow"></div>
      </div>
      <h3 class="error-boundary__title">这个页面刚刚卡壳了</h3>
      <p class="error-boundary__message">
        {{ error.message || '发生了未知错误' }}。可以先重试，不行再回到首页继续操作。
      </p>
      <!-- 开发环境显示详细错误信息 -->
      <details v-if="isDev" class="error-boundary__details">
        <summary>查看详细信息</summary>
        <pre class="error-boundary__stack">{{ error.stack }}</pre>
      </details>
      <div class="error-boundary__actions">
        <el-button type="primary" @click="handleRetry">
          重新加载
        </el-button>
        <el-button @click="handleGoHome">
          返回首页
        </el-button>
      </div>
    </div>
    <slot v-else />
  </div>
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  /** 捕获到错误时的回调 */
  onError: {
    type: Function,
    default: null
  }
})

const router = useRouter()
const error = ref(null)
const isDev = import.meta.env.DEV

/**
 * 捕获子组件生命周期中的错误
 */
onErrorCaptured((err, instance, info) => {
  error.value = err

  // 开发环境打印错误
  if (isDev) {
    console.error('[ErrorBoundary] 捕获到错误:', err)
    console.error('[ErrorBoundary] 错误来源:', info)
  }

  // 调用外部错误回调
  if (typeof props.onError === 'function') {
    props.onError(err, instance, info)
  }

  // 阻止错误继续向上传播
  return false
})

/**
 * 重试：清除错误状态，重新渲染子组件
 */
function handleRetry() {
  error.value = null
}

/**
 * 返回首页
 */
function handleGoHome() {
  error.value = null
  router.push('/')
}
</script>

<style scoped>
.error-boundary {
  width: 100%;
  height: 100%;
}

.error-boundary__container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 40px 20px;
  text-align: center;
  animation: boundaryIn 220ms cubic-bezier(0.2, 0, 0, 1) both;
}

.error-boundary__mascot {
  position: relative;
  width: 92px;
  height: 112px;
  margin-bottom: 24px;
}

.error-boundary__paper {
  position: absolute;
  inset: 0 8px 12px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(180, 35, 24, 0.2);
  border-radius: 18px;
  color: var(--color-danger, #b42318);
  background:
    linear-gradient(135deg, transparent 0 78%, rgba(180, 35, 24, 0.1) 78% 100%),
    #fff7f5;
  box-shadow: 0 16px 34px rgba(180, 35, 24, 0.14);
  transform: rotate(-4deg);
  animation: paperWiggle 3.2s ease-in-out infinite;
}

.error-boundary__paper span {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  color: #ffffff;
  background: var(--color-danger, #b42318);
  font-size: 22px;
  font-weight: 900;
}

.error-boundary__shadow {
  position: absolute;
  right: 12px;
  bottom: 0;
  left: 12px;
  height: 14px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.12);
  filter: blur(2px);
}

.error-boundary__title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary, #333);
  margin-bottom: 8px;
}

.error-boundary__message {
  font-size: 14px;
  color: var(--text-secondary, #666);
  margin-bottom: 24px;
  max-width: 400px;
}

.error-boundary__details {
  margin-bottom: 24px;
  max-width: 600px;
  width: 100%;
  text-align: left;
}

.error-boundary__details summary {
  cursor: pointer;
  color: var(--color-primary, #1A5276);
  font-size: 13px;
  margin-bottom: 8px;
}

.error-boundary__stack {
  background: var(--bg-secondary, #f5f7fa);
  border: 1px solid var(--border-color, #e4e7ed);
  border-radius: 4px;
  padding: 12px;
  font-size: 12px;
  font-family: monospace;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
  color: var(--text-secondary, #666);
}

.error-boundary__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
}

@keyframes boundaryIn {
  from {
    opacity: 0;
    transform: translate3d(0, 8px, 0);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

@keyframes paperWiggle {
  0%,
  100% {
    transform: rotate(-4deg) translate3d(0, 0, 0);
  }
  50% {
    transform: rotate(2deg) translate3d(0, -4px, 0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .error-boundary__container,
  .error-boundary__paper {
    animation: none !important;
    transform: none !important;
  }
}
</style>
