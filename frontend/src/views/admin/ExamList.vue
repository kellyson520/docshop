<template>
  <div class="page-container exam-admin-page">
    <PageHeader
      title="考试管理"
      :breadcrumbs="breadcrumbs"
      subtitle="管理面向用户展示的考试安排，支持新建、编辑、删除和按项目筛选"
    >
      <template #actions>
        <el-input
          v-model="searchQuery"
          placeholder="搜索考试名称"
          :prefix-icon="Search"
          clearable
          class="search-input"
          @input="handleSearchInput"
          @clear="handleSearchInput"
        />
        <el-button :icon="Refresh" :loading="loading" @click="handleRetry">
          刷新
        </el-button>
        <el-button
          v-if="canManage"
          type="primary"
          :icon="Plus"
          class="primary-action"
          @click="handleCreate"
        >
          新建考试
        </el-button>
      </template>
    </PageHeader>

    <section class="summary-grid" aria-label="考试概览">
      <button
        v-for="item in summaryCards"
        :key="item.key"
        class="summary-tile"
        :class="{ active: statusFilter === item.filter }"
        type="button"
        @click="setStatusFilter(item.filter)"
      >
        <span class="summary-label">{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.hint }}</small>
      </button>
    </section>

    <section class="toolbar-row">
      <el-radio-group v-model="statusFilter" @change="handleFilterChange">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="upcoming">未开始</el-radio-button>
        <el-radio-button value="ongoing">进行中</el-radio-button>
        <el-radio-button value="expired">已结束</el-radio-button>
      </el-radio-group>

      <el-select
        v-model="projectFilter"
        placeholder="全部项目"
        clearable
        filterable
        class="project-filter"
        @change="handleFilterChange"
      >
        <el-option
          v-for="project in projects"
          :key="project.id"
          :label="project.name"
          :value="project.id"
        />
      </el-select>
    </section>

    <section class="table-shell">
      <div v-if="error" class="error-strip">
        <el-icon><WarningFilled /></el-icon>
        <span>{{ errorMessage }}</span>
        <el-button text type="primary" @click="handleRetry">重新加载</el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="exams"
        row-key="id"
        class="exam-table"
        :row-class-name="getRowClassName"
        @sort-change="handleSortChange"
      >
        <el-table-column prop="name" label="考试" min-width="230" sortable="custom">
          <template #default="{ row }">
            <div class="exam-main">
              <span class="exam-title" :title="row.name">{{ row.name }}</span>
              <span class="exam-description" :title="row.description || ''">
                {{ row.description || '暂无描述' }}
              </span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row)" effect="light">
              {{ getStatusText(row) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="project_name" label="项目" min-width="180">
          <template #default="{ row }">
            <div class="project-cell">
              <el-icon><Folder /></el-icon>
              <span :title="row.project_name || row.project_id">
                {{ row.project_name || row.project_id || '-' }}
              </span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="start_time" label="考试时间" min-width="230" sortable="custom">
          <template #default="{ row }">
            <div class="time-window">
              <span><el-icon><Clock /></el-icon>{{ formatDateTime(row.start_time) }}</span>
              <span><el-icon><Timer /></el-icon>{{ formatDateTime(row.end_time) }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="提醒" min-width="160">
          <template #default="{ row }">
            <div class="reminder-tags">
              <el-tag
                v-for="item in getReminderTags(row)"
                :key="item"
                size="small"
                type="info"
                effect="plain"
              >
                {{ item }}
              </el-tag>
              <span v-if="getReminderTags(row).length === 0" class="muted">关闭</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="创建时间" width="170" sortable="custom">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-tooltip content="查看详情" placement="top">
                <el-button :icon="View" circle text @click="goToDetail(row.id)" />
              </el-tooltip>
              <template v-if="canManage">
                <el-tooltip content="编辑考试" placement="top">
                  <el-button :icon="Edit" circle text @click="handleEdit(row)" />
                </el-tooltip>
                <el-tooltip content="删除考试" placement="top">
                  <el-button :icon="Delete" circle text type="danger" @click="handleDelete(row)" />
                </el-tooltip>
              </template>
            </div>
          </template>
        </el-table-column>

        <template #empty>
          <EmptyState
            icon="Calendar"
            title="暂无考试"
            :description="emptyDescription"
            :action-text="canManage ? '新建考试' : ''"
            @action="handleCreate"
          />
        </template>
      </el-table>

      <div v-if="total > 0 && !error" class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </section>

    <ExamDialog
      v-model="dialogVisible"
      :exam="editingExam"
      @success="handleDialogSuccess"
    />
  </div>
</template>

<script setup>
defineOptions({ name: 'ExamList' })

import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  Plus,
  Search,
  View,
  Edit,
  Delete,
  Clock,
  Timer,
  Folder,
  Calendar,
  VideoPlay,
  CircleCheckFilled,
  WarningFilled,
  Refresh
} from '@element-plus/icons-vue'
import { getExams } from '@/api/exam'
import { useExamStore } from '@/stores/exam'
import { useProjectStore } from '@/stores/project'
import { useAuthStore } from '@/stores/auth'
import { useLoading } from '@/composables/useLoading'
import { useDebounce } from '@/composables/useDebounce'
import { useConfirm } from '@/composables/useConfirm'
import { useMessage } from '@/composables/useMessage'
import { ErrorHandler } from '@/utils/error'
import EmptyState from '@/components/common/EmptyState.vue'
import ExamDialog from '@/components/exam/ExamDialog.vue'
import PageHeader from '@/components/common/PageHeader.vue'

const router = useRouter()
const route = useRoute()
const examStore = useExamStore()
const projectStore = useProjectStore()
const authStore = useAuthStore()
const { confirmDelete } = useConfirm()
const { success } = useMessage()
const { loading, start: startLoading, stop: stopLoading } = useLoading()

const breadcrumbs = [{ title: '考试管理' }]

const searchQuery = ref('')
const statusFilter = ref('')
const projectFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const sortBy = ref('start_time')
const sortOrder = ref('asc')
const dialogVisible = ref(false)
const editingExam = ref(null)
const error = ref(false)
const errorMessage = ref('')
const projects = ref([])
const summary = ref({
  total: 0,
  upcoming: 0,
  ongoing: 0,
  expired: 0
})

const exams = computed(() => examStore.exams)
const canManage = computed(() => authStore.isAdmin)

const summaryCards = computed(() => [
  {
    key: 'total',
    label: '全部考试',
    value: summary.value.total,
    hint: '当前系统记录',
    filter: ''
  },
  {
    key: 'upcoming',
    label: '未开始',
    value: summary.value.upcoming,
    hint: '等待用户查看',
    filter: 'upcoming'
  },
  {
    key: 'ongoing',
    label: '进行中',
    value: summary.value.ongoing,
    hint: '正在考试',
    filter: 'ongoing'
  },
  {
    key: 'expired',
    label: '已结束',
    value: summary.value.expired,
    hint: '历史安排',
    filter: 'expired'
  }
])

const emptyDescription = computed(() => {
  if (searchQuery.value || statusFilter.value || projectFilter.value) {
    return '当前筛选条件下没有考试，调整搜索、状态或项目后再试'
  }
  return '还没有考试安排，管理员可以先新建一个考试并绑定项目'
})

const { debouncedFn: debouncedSearch } = useDebounce(() => {
  currentPage.value = 1
  fetchExams()
}, 300)

onMounted(async () => {
  await ensureCurrentUser()
  await Promise.all([loadProjects(), fetchExams(), fetchSummary()])
  if (route.query.action === 'create' && canManage.value) {
    handleCreate()
  }
})

async function ensureCurrentUser() {
  if (!authStore.user && authStore.token) {
    await authStore.fetchUser()
  }
}

async function loadProjects() {
  try {
    const data = await projectStore.fetchProjects({ page_size: 100 })
    projects.value = data.items || data || []
  } catch (err) {
    console.warn('[ExamList] 加载项目筛选失败:', err)
  }
}

async function fetchSummary() {
  try {
    const [all, upcoming, ongoing, expired] = await Promise.all([
      getExams({ page: 1, page_size: 1 }),
      getExams({ page: 1, page_size: 1, status: 'upcoming' }),
      getExams({ page: 1, page_size: 1, status: 'ongoing' }),
      getExams({ page: 1, page_size: 1, status: 'expired' })
    ])

    summary.value = {
      total: all.total || 0,
      upcoming: upcoming.total || 0,
      ongoing: ongoing.total || 0,
      expired: expired.total || 0
    }
  } catch (err) {
    console.warn('[ExamList] 加载考试概览失败:', err)
  }
}

async function fetchExams() {
  error.value = false
  errorMessage.value = ''
  startLoading('加载考试列表...')

  try {
    const data = await examStore.fetchExams({
      page: currentPage.value,
      page_size: pageSize.value,
      status: statusFilter.value || undefined,
      project_id: projectFilter.value || undefined,
      keyword: searchQuery.value.trim() || undefined,
      sort_by: sortBy.value,
      sort_order: sortOrder.value
    })
    total.value = data.total || 0
  } catch (err) {
    error.value = true
    errorMessage.value = '无法加载考试列表，请检查后端服务或登录状态'
    ErrorHandler.handle(err, { silent: true })
  } finally {
    stopLoading()
  }
}

function handleSearchInput() {
  debouncedSearch()
}

function setStatusFilter(value) {
  statusFilter.value = value
  handleFilterChange()
}

function handleFilterChange() {
  currentPage.value = 1
  fetchExams()
}

function handleRetry() {
  fetchExams()
  fetchSummary()
}

function goToDetail(id) {
  router.push(`/admin/exams/${id}`)
}

function handleCreate() {
  if (!canManage.value) return
  editingExam.value = null
  dialogVisible.value = true
}

function handleEdit(exam) {
  if (!canManage.value) return
  editingExam.value = exam
  dialogVisible.value = true
}

async function handleDelete(exam) {
  if (!canManage.value) return
  try {
    await confirmDelete({
      title: '删除考试',
      message: `确定删除考试“${exam.name}”吗？此操作不可恢复。`
    })

    startLoading('删除考试...')
    await examStore.deleteExam(exam.id)
    success('考试已删除')
    if (exams.value.length === 0 && currentPage.value > 1) {
      currentPage.value -= 1
    }
    await Promise.all([fetchExams(), fetchSummary()])
  } catch (err) {
    if (err !== 'cancel') {
      ErrorHandler.handle(err, {
        fallbackMessage: '删除失败，请稍后重试'
      })
    }
  } finally {
    stopLoading()
  }
}

async function handleDialogSuccess() {
  await Promise.all([fetchExams(), fetchSummary()])
}

function handleSizeChange(size) {
  pageSize.value = size
  currentPage.value = 1
  fetchExams()
}

function handlePageChange(page) {
  currentPage.value = page
  fetchExams()
}

function handleSortChange({ prop, order }) {
  sortBy.value = prop || 'start_time'
  sortOrder.value = order === 'descending' ? 'desc' : 'asc'
  fetchExams()
}

function getStatusKey(exam) {
  const now = new Date()
  const startTime = new Date(exam.start_time)
  const endTime = new Date(exam.end_time)

  if (endTime <= now) return 'expired'
  if (startTime <= now && endTime > now) return 'ongoing'
  return 'upcoming'
}

function getStatusType(exam) {
  const status = getStatusKey(exam)
  if (status === 'expired') return 'info'
  if (status === 'ongoing') return 'success'
  const minutes = (new Date(exam.start_time) - new Date()) / (1000 * 60)
  return minutes <= 15 ? 'warning' : 'primary'
}

function getStatusText(exam) {
  const status = getStatusKey(exam)
  if (status === 'expired') return '已结束'
  if (status === 'ongoing') return '进行中'
  const minutes = (new Date(exam.start_time) - new Date()) / (1000 * 60)
  return minutes <= 15 ? '即将开始' : '未开始'
}

function getReminderTags(exam) {
  const tags = []
  if (Number(exam.reminder_15min)) tags.push('15分钟前')
  if (Number(exam.reminder_5min)) tags.push('5分钟前')
  if (Number(exam.reminder_start)) tags.push('开始时')
  return tags
}

function getRowClassName({ row }) {
  return `exam-row exam-row--${getStatusKey(row)}`
}

function formatDateTime(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  if (Number.isNaN(date.getTime())) return isoString
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}
</script>

<style scoped>
.exam-admin-page {
  --panel-border: #dbe3eb;
  --panel-bg: #ffffff;
  --ink-strong: #172033;
  --ink-soft: #667085;
}

.search-input {
  width: 240px;
}

.primary-action {
  box-shadow: none;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.summary-tile {
  display: grid;
  gap: 4px;
  min-height: 104px;
  padding: 16px;
  text-align: left;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbfd 100%);
  cursor: pointer;
  transition: border-color 0.15s ease, background-color 0.15s ease;
}

.summary-tile:hover,
.summary-tile.active {
  border-color: #2f6da3;
  background: #f3f8fc;
}

.summary-label {
  color: var(--ink-soft);
  font-size: 13px;
}

.summary-tile strong {
  color: var(--ink-strong);
  font-size: 30px;
  line-height: 1;
}

.summary-tile small {
  color: #8a97a8;
  font-size: 12px;
}

.toolbar-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}

.project-filter {
  width: 260px;
}

.table-shell {
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: var(--panel-bg);
  overflow: hidden;
}

.error-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  color: #9f3412;
  background: #fff7ed;
  border-bottom: 1px solid #fed7aa;
}

.exam-table {
  width: 100%;
}

.exam-main {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.exam-title {
  color: var(--ink-strong);
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.exam-description {
  color: var(--ink-soft);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-cell,
.time-window span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.project-cell span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.time-window {
  display: grid;
  gap: 5px;
  color: #475467;
  font-size: 13px;
}

.reminder-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.muted {
  color: #98a2b3;
  font-size: 13px;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  padding: 14px 16px;
  border-top: 1px solid var(--panel-border);
}

.exam-table :deep(.exam-row) {
  transition: background-color 0.18s ease;
}

.exam-table :deep(.exam-row--ongoing td:first-child) {
  box-shadow: inset 3px 0 0 #22c55e;
}

.exam-table :deep(.exam-row--upcoming td:first-child) {
  box-shadow: inset 3px 0 0 #2f6da3;
}

.exam-table :deep(.exam-row--expired td:first-child) {
  box-shadow: inset 3px 0 0 #98a2b3;
}

@media (max-width: 960px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .toolbar-row {
    align-items: stretch;
    flex-direction: column;
  }

  .project-filter,
  .search-input {
    width: 100%;
  }
}

@media (max-width: 560px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
