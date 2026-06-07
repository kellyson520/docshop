<template>
  <div class="not-found-page">
    <div class="not-found-content">
      <el-icon class="not-found-icon" :size="120">
        <WarningFilled />
      </el-icon>
      <h1 class="not-found-title">404</h1>
      <p class="not-found-desc">页面不存在</p>
      <p class="not-found-hint">您访问的页面可能已被移除、名称已更改，或暂时不可用。</p>
      <el-button type="primary" size="large" @click="goHome">
        <el-icon><HomeFilled /></el-icon>
        返回首页
      </el-button>
      <p class="not-found-countdown">{{ countdown }} 秒后自动跳转首页</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { WarningFilled, HomeFilled } from '@element-plus/icons-vue'

const router = useRouter()
const countdown = ref(3)
let timer = null

function goHome() {
  router.push('/admin')
}

onMounted(() => {
  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(timer)
      timer = null
      goHome()
    }
  }, 1000)
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})
</script>

<style scoped>
.not-found-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #f5f7fa;
}

.not-found-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 40px 20px;
}

.not-found-icon {
  color: #909399;
  margin-bottom: 24px;
}

.not-found-title {
  margin: 0 0 12px;
  font-size: 72px;
  font-weight: 700;
  color: #303133;
  line-height: 1;
}

.not-found-desc {
  margin: 0 0 12px;
  font-size: 20px;
  font-weight: 500;
  color: #606266;
}

.not-found-hint {
  margin: 0 0 32px;
  font-size: 14px;
  color: #909399;
  max-width: 400px;
  line-height: 1.6;
}

.not-found-countdown {
  margin-top: 16px;
  font-size: 13px;
  color: #c0c4cc;
}
</style>
