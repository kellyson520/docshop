<template>
  <!-- 考试提醒弹窗 -->
  <transition-group name="reminder" tag="div" class="exam-reminder-container">
    <div
      v-for="reminder in visibleReminders"
      :key="`${reminder.id}-${reminder.reminderType}`"
      class="exam-reminder"
      :class="`reminder-${reminder.reminderType}`"
    >
      <div class="reminder-icon">
        <el-icon :size="32" class="bell-icon">
          <Bell />
        </el-icon>
      </div>
      <div class="reminder-content">
        <h4 class="reminder-title">{{ reminder.name }}</h4>
        <p class="reminder-text">
          <el-tag :type="getReminderTagType(reminder.reminderType)" size="small">
            {{ reminder.reminderText }}
          </el-tag>
          <span v-if="reminder.diffMinutes > 0" class="time-left">
            还有 {{ reminder.diffMinutes }} 分钟
          </span>
          <span v-else class="time-left">即将开始</span>
        </p>
        <p v-if="reminder.description" class="reminder-desc">
          {{ reminder.description }}
        </p>
      </div>
      <div class="reminder-actions">
        <el-button
          type="primary"
          size="small"
          @click="handleDismiss(reminder)"
        >
          我知道了
        </el-button>
      </div>
    </div>
  </transition-group>
</template>

<script setup>
defineOptions({ name: 'ExamReminder' })

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Bell } from '@element-plus/icons-vue'
import { useExamStore } from '@/stores/exam'
import { useMessage } from '@/composables/useMessage'

// ==================== 状态管理 ====================
const examStore = useExamStore()
const { success, error: showError } = useMessage()

// ==================== 响应式数据 ====================
const checkInterval = ref(null)
const dismissedIds = ref(new Set())
const reminderErrorShown = ref(false)

// ==================== 计算属性 ====================

/**
 * 可见的提醒列表（排除已关闭的）
 */
const visibleReminders = computed(() => {
  return examStore.upcomingReminders.filter(
    r => !dismissedIds.value.has(`${r.id}-${r.reminderType}`)
  )
})

// ==================== 生命周期 ====================
onMounted(() => {
  // 初始检查
  checkReminders()

  // 每30秒检查一次
  checkInterval.value = setInterval(() => {
    checkReminders()
  }, 30000)
})

onUnmounted(() => {
  // 清理定时器
  if (checkInterval.value) {
    clearInterval(checkInterval.value)
    checkInterval.value = null
  }
})

// ==================== 方法 ====================

/**
 * 检查即将开始的考试
 */
async function checkReminders() {
  try {
    await examStore.checkUpcomingExams()
    reminderErrorShown.value = false

    // 如果有新提醒，清理已过期的关闭记录
    if (examStore.upcomingReminders.length > 0) {
      cleanupDismissedIds()
    }
  } catch (error) {
    console.error('[ExamReminder] 检查提醒失败:', error)
    if (!reminderErrorShown.value) {
      showError(error.message || '检查考试提醒失败，请稍后重试')
      reminderErrorShown.value = true
    }
  }
}

/**
 * 关闭提醒
 * @param {Object} reminder - 提醒对象
 */
async function handleDismiss(reminder) {
  // 本地标记为已关闭
  dismissedIds.value.add(`${reminder.id}-${reminder.reminderType}`)

  // 同步到store
  await examStore.dismissReminder(reminder.id, reminder.reminderType)

  // 显示提示
  success(`已关闭「${reminder.name}」的提醒`)
}

/**
 * 清理已过期的关闭记录
 * 避免Set无限增长
 */
function cleanupDismissedIds() {
  const validKeys = new Set(
    examStore.upcomingReminders.map(r => `${r.id}-${r.reminderType}`)
  )

  // 只保留当前提醒列表中的关闭记录
  for (const key of dismissedIds.value) {
    if (!validKeys.has(key)) {
      dismissedIds.value.delete(key)
    }
  }
}

/**
 * 获取提醒标签类型
 * @param {string} reminderType - 提醒类型
 * @returns {string}
 */
function getReminderTagType(reminderType) {
  switch (reminderType) {
    case 'start':
      return 'danger'
    case '5min':
      return 'warning'
    case '15min':
      return 'info'
    default:
      return 'info'
  }
}
</script>

<style scoped>
.exam-reminder-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 400px;
}

.exam-reminder {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-left: 4px solid #409eff;
  min-width: 320px;
}

/* 不同提醒类型的边框颜色 */
.exam-reminder.reminder-15min {
  border-left-color: #909399;
}

.exam-reminder.reminder-5min {
  border-left-color: #e6a23c;
}

.exam-reminder.reminder-start {
  border-left-color: #f56c6c;
}

.reminder-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: #ecf5ff;
  border-radius: 50%;
  color: #409eff;
}

.reminder-15min .reminder-icon {
  background: #f4f4f5;
  color: #909399;
}

.reminder-5min .reminder-icon {
  background: #fdf6ec;
  color: #e6a23c;
}

.reminder-start .reminder-icon {
  background: #fef0f0;
  color: #f56c6c;
}

/* 铃铛动画 */
.bell-icon {
  animation: bellRing 2s ease-in-out infinite;
}

@keyframes bellRing {
  0%, 100% {
    transform: rotate(0deg);
  }
  10%, 30%, 50% {
    transform: rotate(15deg);
  }
  20%, 40% {
    transform: rotate(-15deg);
  }
  60% {
    transform: rotate(0deg);
  }
}

.reminder-content {
  flex: 1;
  min-width: 0;
}

.reminder-title {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.reminder-text {
  margin: 0 0 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.time-left {
  font-size: 13px;
  color: #606266;
}

.reminder-desc {
  margin: 0;
  font-size: 13px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.reminder-actions {
  flex-shrink: 0;
}

/* 过渡动画 */
.reminder-enter-active,
.reminder-leave-active {
  transition:
    transform 0.3s ease,
    box-shadow 0.3s ease,
    border-color 0.3s ease,
    background-color 0.3s ease,
    color 0.3s ease,
    opacity 0.3s ease;
}

.reminder-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.reminder-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

/* 响应式适配 */
@media (max-width: 768px) {
  .exam-reminder-container {
    left: 16px;
    right: 16px;
    top: 16px;
    max-width: none;
  }

  .exam-reminder {
    min-width: auto;
    width: 100%;
  }
}
</style>
