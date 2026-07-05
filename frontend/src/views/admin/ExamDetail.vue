<template>
  <div class="page-container">
    <PageHeader
      title="考试详情"
      :subtitle="exam?.name"
      :icon="Calendar"
    >
      <template #actions>
        <el-button @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <el-button v-if="isAdmin" type="primary" @click="showEditDialog = true">
          <el-icon><Edit /></el-icon>
          编辑
        </el-button>
      </template>
    </PageHeader>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="10" animated />
    </div>

    <!-- 错误状态 -->
    <EmptyState
      v-else-if="error"
      icon="WarningFilled"
      :icon-size="64"
      icon-color="#F56C6C"
      title="加载失败"
      :description="errorMessage"
      action-text="重新加载"
      @action="fetchExam"
    />

    <!-- 考试详情 -->
    <div v-else-if="exam" class="exam-detail">
      <el-card shadow="hover">
        <template #header>
          <div class="card-header">
            <span class="exam-name">{{ exam.name }}</span>
            <el-tag :type="getStatusType(exam.status)" effect="dark">
              {{ getStatusText(exam.status) }}
            </el-tag>
          </div>
        </template>

        <div class="detail-content">
          <div class="detail-item">
            <span class="label">考试描述：</span>
            <span class="value">{{ exam.description || '暂无描述' }}</span>
          </div>

          <div class="detail-row">
            <div class="detail-item">
              <span class="label">开始时间：</span>
              <span class="value">{{ formatDateTime(exam.start_time) }}</span>
            </div>
            <div class="detail-item">
              <span class="label">结束时间：</span>
              <span class="value">{{ formatDateTime(exam.end_time) }}</span>
            </div>
          </div>

          <div class="detail-item">
            <span class="label">创建者：</span>
            <span class="value">{{ exam.creator_name || '未知' }}</span>
          </div>

          <div class="detail-item">
            <span class="label">提醒设置：</span>
            <div class="reminder-tags">
              <el-tag v-if="exam.reminder_15min" size="small" type="info">考前15分钟</el-tag>
              <el-tag v-if="exam.reminder_5min" size="small" type="info">考前5分钟</el-tag>
              <el-tag v-if="exam.reminder_start" size="small" type="info">开始时</el-tag>
              <span v-if="!exam.reminder_15min && !exam.reminder_5min && !exam.reminder_start" class="value">未设置</span>
            </div>
          </div>

          <div v-if="exam.project_name" class="detail-item">
            <span class="label">关联项目：</span>
            <span class="value">{{ exam.project_name }}</span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 编辑对话框 -->
    <ExamDialog
      v-model="showEditDialog"
      :exam="exam"
      @success="handleEditSuccess"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Calendar, ArrowLeft, Edit } from '@element-plus/icons-vue'
import { useExamStore } from '@/stores/exam'
import { useAuthStore } from '@/stores/auth'
import { useLoading } from '@/composables/useLoading'
import { ErrorHandler } from '@/utils/error'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ExamDialog from '@/components/exam/ExamDialog.vue'

defineOptions({ name: 'ExamDetail' })

const route = useRoute()
const router = useRouter()
const examStore = useExamStore()
const authStore = useAuthStore()

const exam = ref(null)
const showEditDialog = ref(false)
const error = ref(false)
const errorMessage = ref('')

const isAdmin = computed(() => authStore.user?.role === 'admin')

const { loading, start: startLoading, stop: stopLoading } = useLoading()

onMounted(() => {
  fetchExam()
})

async function fetchExam() {
  error.value = false
  errorMessage.value = ''
  startLoading()

  try {
    const id = route.params.id
    exam.value = await examStore.fetchExam(id)
  } catch (err) {
    error.value = true
    errorMessage.value = '无法加载考试详情'
    ErrorHandler.handle(err, { silent: true })
  } finally {
    stopLoading()
  }
}

function goBack() {
  router.push('/admin/exams')
}

function handleEditSuccess() {
  showEditDialog.value = false
  fetchExam()
}

function getStatusType(status) {
  const typeMap = {
    upcoming: 'primary',
    ongoing: 'success',
    expired: 'info'
  }
  return typeMap[status] || 'info'
}

function getStatusText(status) {
  const textMap = {
    upcoming: '即将开始',
    ongoing: '进行中',
    expired: '已结束'
  }
  return textMap[status] || status
}

function formatDateTime(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.exam-detail {
  margin-top: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.exam-name {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-row {
  display: flex;
  gap: 40px;
}

.detail-item {
  display: flex;
  align-items: flex-start;
}

.detail-item .label {
  color: #909399;
  min-width: 80px;
}

.detail-item .value {
  color: #606266;
}

.reminder-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
