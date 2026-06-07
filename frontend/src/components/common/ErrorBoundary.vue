<template>
  <div class="error-boundary">
    <div v-if="error" class="error-boundary__container">
      <div class="error-boundary__icon">
        <svg viewBox="0 0 64 64" width="64" height="64" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="32" cy="32" r="30" stroke="var(--color-danger, #E74C3C)" stroke-width="2" />
          <path d="M32 18v16" stroke="var(--color-danger, #E74C3C)" stroke-width="3" stroke-linecap="round" />
          <circle cx="32" cy="44" r="2" fill="var(--color-danger, #E74C3C)" />
        </svg>
      </div>
      <h3 class="error-boundary__title">页面出现了问题</h3>
      <p class="error-boundary__message">{{ error.message || '发生了未知错误' }}</p>
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
const isDev = process.env.NODE_ENV === 'development'

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
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 40px 20px;
  text-align: center;
}

.error-boundary__icon {
  margin-bottom: 24px;
  opacity: 0.8;
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
  gap: 12px;
}
</style>
