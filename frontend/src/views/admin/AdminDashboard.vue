<!--
  管理员仪表盘页面
  显示系统概览、统计信息和快捷操作
-->
<template>
  <div ref="dashboardRoot" class="dashboard-container">
    <!-- 页面头部 -->
    <PageHeader
      title="仪表盘"
      subtitle="欢迎使用 DocShop 文档比对系统"
      :icon="DataBoard"
      :show-breadcrumb="false"
    />

    <!-- 加载状态 -->
    <div v-if="loading" class="skeleton-wrapper">
      <el-row :gutter="20">
        <el-col v-for="i in 4" :key="i" :xs="12" :sm="12" :md="6">
          <el-card shadow="hover" class="stat-card">
            <el-skeleton :rows="2" animated />
          </el-card>
        </el-col>
      </el-row>
    </div>

    <template v-else>
      <!-- 顶部统计卡片 -->
      <el-row :gutter="20" class="stats-row">
        <el-col :xs="12" :sm="12" :md="6">
          <el-card shadow="hover" class="stat-card stat-card--projects">
            <div class="stat-content">
              <div class="stat-icon">
                <el-icon><FolderOpened /></el-icon>
              </div>
              <div class="stat-info">
                <span class="stat-value" :data-count-to="stats.projectCount">{{ stats.projectCount }}</span>
                <span class="stat-label">项目总数</span>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="12" :sm="12" :md="6">
          <el-card shadow="hover" class="stat-card stat-card--files">
            <div class="stat-content">
              <div class="stat-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div class="stat-info">
                <span class="stat-value" :data-count-to="stats.fileCount">{{ stats.fileCount }}</span>
                <span class="stat-label">文件总数</span>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="12" :sm="12" :md="6">
          <el-card shadow="hover" class="stat-card stat-card--visits">
            <div class="stat-content">
              <div class="stat-icon">
                <el-icon><View /></el-icon>
              </div>
              <div class="stat-info">
                <span class="stat-value" :data-count-to="stats.visitCount">{{ stats.visitCount }}</span>
                <span class="stat-label">用户访问次数</span>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="12" :sm="12" :md="6">
          <el-card shadow="hover" class="stat-card stat-card--exams">
            <div class="stat-content">
              <div class="stat-icon">
                <el-icon><Calendar /></el-icon>
              </div>
              <div class="stat-info">
                <span class="stat-value" :data-count-to="stats.pendingExamCount">{{ stats.pendingExamCount }}</span>
                <span class="stat-label">待处理考试</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 快捷操作区 -->
      <el-card class="quick-actions-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span class="card-title">快捷操作</span>
          </div>
        </template>
        <div class="quick-actions">
          <div class="action-item" @click="goToCreateProject">
            <div class="action-icon action-icon--primary">
              <el-icon><Plus /></el-icon>
            </div>
            <span class="action-text">新建项目</span>
          </div>

          <div class="action-item" @click="goToUpload">
            <div class="action-icon action-icon--success">
              <el-icon><Upload /></el-icon>
            </div>
            <span class="action-text">上传文件</span>
          </div>

          <div class="action-item" @click="goToCreateExam">
            <div class="action-icon action-icon--warning">
              <el-icon><EditPen /></el-icon>
            </div>
            <span class="action-text">创建考试</span>
          </div>

          <div class="action-item" @click="goToRankings">
            <div class="action-icon action-icon--danger">
              <el-icon><TrendCharts /></el-icon>
            </div>
            <span class="action-text">查看排行</span>
          </div>
        </div>
      </el-card>

      <!-- 主体内容区 -->
      <el-row :gutter="20" class="content-row">
        <!-- 最近项目列表 -->
        <el-col :xs="24" :lg="12">
          <el-card class="list-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span class="card-title">最近项目</span>
                <el-button type="primary" text @click="goToProjects">
                  查看全部 <el-icon><ArrowRight /></el-icon>
                </el-button>
              </div>
            </template>

            <div v-if="recentProjects.length === 0" class="empty-tip">
              <el-empty description="暂无项目" :image-size="80" />
            </div>

            <div v-else class="item-list">
              <div
                v-for="project in recentProjects"
                :key="project.id"
                class="list-item"
                @click="goToProjectDetail(project.id)"
              >
                <div class="item-icon">
                  <el-icon><Folder /></el-icon>
                </div>
                <div class="item-info">
                  <span class="item-name">{{ project.name }}</span>
                  <span class="item-meta">
                    {{ project.file_count || 0 }} 个文件 · {{ formatRelativeTime(project.created_at) }}
                  </span>
                </div>
                <el-tag v-if="project.is_public" type="success" size="small">公开</el-tag>
                <el-tag v-else size="small">私有</el-tag>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 最近上传文件 -->
        <el-col :xs="24" :lg="12">
          <el-card class="list-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span class="card-title">最近上传</span>
                <el-button type="primary" text @click="goToFiles">
                  查看全部 <el-icon><ArrowRight /></el-icon>
                </el-button>
              </div>
            </template>

            <div v-if="recentFiles.length === 0" class="empty-tip">
              <el-empty description="暂无文件" :image-size="80" />
            </div>

            <div v-else class="item-list">
              <div
                v-for="file in recentFiles"
                :key="file.id"
                class="list-item"
                @click="goToFileDetail(file)"
              >
                <div class="item-icon">
                  <el-icon><Document /></el-icon>
                </div>
                <div class="item-info">
                  <span class="item-name">{{ file.name }}</span>
                  <span class="item-meta">
                    {{ formatRelativeTime(file.created_at) }}
                  </span>
                </div>
                <el-tag type="info" size="small">{{ file.version_count || 1 }} 个版本</el-tag>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 即将到来的考试 -->
      <el-card class="exams-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span class="card-title">即将到来的考试</span>
            <el-button type="primary" text @click="goToExams">
              查看全部 <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
        </template>

        <div v-if="upcomingExams.length === 0" class="empty-tip">
          <el-empty description="暂无待进行的考试" :image-size="80" />
        </div>

        <div v-else class="exam-list">
          <div
            v-for="exam in upcomingExams"
            :key="exam.id"
            class="exam-item"
            @click="goToExamDetail(exam.id)"
          >
            <div class="exam-info">
              <span class="exam-name">{{ exam.name }}</span>
              <span class="exam-time">
                <el-icon><Clock /></el-icon>
                {{ formatExamTime(exam.start_time, exam.end_time) }}
              </span>
            </div>
            <el-tag :type="getExamStatusType(exam)" size="small">
              {{ getExamStatus(exam) }}
            </el-tag>
          </div>
        </div>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import {
  FolderOpened,
  Document,
  View,
  Calendar,
  Plus,
  Upload,
  EditPen,
  TrendCharts,
  ArrowRight,
  Folder,
  Clock,
  DataBoard
} from '@element-plus/icons-vue'
import { getProjects } from '@/api/project'
import { getExams } from '@/api/exam'
import PageHeader from '@/components/common/PageHeader.vue'
import { useGsapScoped } from '@/composables/useGsapMotion'

defineOptions({ name: 'AdminDashboard' })

const router = useRouter()
const dashboardRoot = ref(null)
const { runGsap } = useGsapScoped(dashboardRoot)

// 加载状态
const loading = ref(true)

// 统计数据
const stats = ref({
  projectCount: 0,
  fileCount: 0,
  visitCount: 0,
  pendingExamCount: 0
})

// 最近项目
const recentProjects = ref([])

// 最近文件
const recentFiles = ref([])

// 即将到来的考试
const upcomingExams = ref([])

const DASHBOARD_EXAM_REFRESH_MS = 30000
let dashboardRefreshTimer = null
let dashboardRefreshInFlight = false

/**
 * 获取统计数据
 */
async function fetchStats() {
  try {
    let fileCount = 0
    let page = 1
    let hasMore = true

    while (hasMore) {
      const projectsRes = await getProjects({ page, page_size: 100 })
      const items = projectsRes.items || projectsRes || []
      if (page === 1) {
        stats.value.projectCount = projectsRes.total || items.length || 0
      }
      items.forEach(p => {
        fileCount += p.file_count || 0
      })
      hasMore = items.length === 100 && page * 100 < (projectsRes.total || Infinity)
      page++
    }
    stats.value.fileCount = fileCount

    const examsRes = await getExams({ status: 'upcoming', page_size: 100 })
    stats.value.pendingExamCount = examsRes.total || examsRes.length || 0
  } catch (error) {
    console.error('[Dashboard] 获取统计数据失败:', error)
  }
}

/**
 * 获取最近项目
 */
async function fetchRecentProjects() {
  try {
    const res = await getProjects({ page: 1, page_size: 5 })
    recentProjects.value = res.items || res || []
  } catch (error) {
    console.error('[Dashboard] 获取最近项目失败:', error)
  }
}

/**
 * 获取最近上传文件
 */
function fetchRecentFiles() {
  // 从最近项目中提取文件信息
  recentFiles.value = []
  recentProjects.value.forEach(project => {
    if (project.recent_files) {
      recentFiles.value.push(...project.recent_files.slice(0, 3))
    }
  })
  // 按时间排序并取前5个
  recentFiles.value.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  recentFiles.value = recentFiles.value.slice(0, 5)
}

/**
 * 获取即将到来的考试
 */
async function fetchUpcomingExams() {
  try {
    const res = await getExams({ status: 'upcoming', page_size: 100 })
    upcomingExams.value = (res.items || res || []).slice(0, 3)
  } catch (error) {
    console.error('[Dashboard] 获取考试列表失败:', error)
  }
}

async function refreshUpcomingExamData() {
  if (dashboardRefreshInFlight) return
  dashboardRefreshInFlight = true
  try {
    const res = await getExams({ status: 'upcoming', page_size: 100 })
    const items = res.items || res || []
    stats.value.pendingExamCount = res.total || items.length || 0
    upcomingExams.value = items.slice(0, 3)
  } finally {
    dashboardRefreshInFlight = false
  }
}

function handleDashboardVisibilityChange() {
  if (document.visibilityState === 'visible') {
    void refreshUpcomingExamData()
  }
}

function startDashboardAutoRefresh() {
  stopDashboardAutoRefresh()
  dashboardRefreshTimer = setInterval(() => {
    if (document.visibilityState !== 'hidden') {
      void refreshUpcomingExamData()
    }
  }, DASHBOARD_EXAM_REFRESH_MS)
  document.addEventListener('visibilitychange', handleDashboardVisibilityChange)
}

function stopDashboardAutoRefresh() {
  if (dashboardRefreshTimer) {
    clearInterval(dashboardRefreshTimer)
    dashboardRefreshTimer = null
  }
  document.removeEventListener('visibilitychange', handleDashboardVisibilityChange)
}

/**
 * 格式化相对时间
 */
function formatRelativeTime(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  const now = new Date()
  const diff = now - date

  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (diff < minute) {
    return '刚刚'
  } else if (diff < hour) {
    return `${Math.floor(diff / minute)} 分钟前`
  } else if (diff < day) {
    return `${Math.floor(diff / hour)} 小时前`
  } else {
    return `${Math.floor(diff / day)} 天前`
  }
}

/**
 * 格式化考试时间
 */
function formatExamTime(start, end) {
  if (!start) return '-'
  const startDate = new Date(start)
  const startStr = `${startDate.getMonth() + 1}/${startDate.getDate()} ${startDate.getHours().toString().padStart(2, '0')}:${startDate.getMinutes().toString().padStart(2, '0')}`

  if (!end) return startStr

  const endDate = new Date(end)
  const endStr = `${endDate.getHours().toString().padStart(2, '0')}:${endDate.getMinutes().toString().padStart(2, '0')}`
  return `${startStr} - ${endStr}`
}

/**
 * 获取考试状态
 */
function getExamStatus(exam) {
  const now = new Date()
  const start = new Date(exam.start_time)
  const end = new Date(exam.end_time)

  if (now < start) {
    return '未开始'
  } else if (now >= start && now <= end) {
    return '进行中'
  } else {
    return '已结束'
  }
}

/**
 * 获取考试状态对应的标签类型
 */
function getExamStatusType(exam) {
  const status = getExamStatus(exam)
  const typeMap = {
    '未开始': 'warning',
    '进行中': 'success',
    '已结束': 'info'
  }
  return typeMap[status] || 'info'
}

// 导航方法
function goToCreateProject() {
  router.push('/admin/projects?action=create')
}

function goToUpload() {
  router.push('/admin/projects')
}

function goToCreateExam() {
  router.push('/admin/exams?action=create')
}

function goToRankings() {
  router.push('/admin/rank/visit')
}

function goToProjects() {
  router.push('/admin/projects')
}

function goToFiles() {
  router.push('/admin/projects')
}

function goToExams() {
  router.push('/admin/exams')
}

function goToProjectDetail(id) {
  router.push(`/admin/projects/${id}`)
}

function goToFileDetail(file) {
  if (file.project_id) {
    router.push(`/admin/projects/${file.project_id}/diff/${file.id}`)
  }
}

function goToExamDetail(id) {
  router.push(`/admin/exams/${id}`)
}

function formatAnimatedCount(value) {
  return Math.round(Number(value) || 0).toLocaleString()
}

async function playDashboardIntro() {
  try {
    await nextTick()

    await runGsap((gsap, root) => {
      const tl = gsap.timeline({
        defaults: {
          duration: 0.34,
          ease: 'power2.out'
        }
      })

      tl.from('.stat-card', {
        y: 18,
        autoAlpha: 0,
        stagger: 0.045,
        clearProps: 'transform,opacity,visibility'
      })
        .from('.quick-actions-card', {
          y: 14,
          autoAlpha: 0,
          clearProps: 'transform,opacity,visibility'
        }, '-=0.16')
        .from('.list-card, .exams-card', {
          y: 16,
          autoAlpha: 0,
          stagger: 0.05,
          clearProps: 'transform,opacity,visibility'
        }, '-=0.14')

      root.querySelectorAll('.stat-value[data-count-to]').forEach((el) => {
        const target = Number(el.dataset.countTo || 0)
        const state = { value: 0 }

        gsap.to(state, {
          value: target,
          duration: 0.78,
          ease: 'power1.out',
          onUpdate: () => {
            el.textContent = formatAnimatedCount(state.value)
          },
          onComplete: () => {
            el.textContent = formatAnimatedCount(target)
          }
        })
      })
    })
  } catch (error) {
    console.warn('[Dashboard] GSAP intro skipped:', error)
  }
}

/**
 * 初始化数据
 */
async function initData() {
  loading.value = true
  try {
    await Promise.all([
      fetchStats(),
      fetchRecentProjects()
    ])
    fetchRecentFiles()
    await fetchUpcomingExams()
  } finally {
    loading.value = false
    void playDashboardIntro()
  }
}

onMounted(() => {
  initData()
  startDashboardAutoRefresh()
})

onUnmounted(() => {
  stopDashboardAutoRefresh()
})
</script>

<style scoped>
.dashboard-container {
  max-width: 1400px;
  margin: 0 auto;
}

/* 统计卡片 */
.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  height: 100%;
  cursor: default;
  will-change: transform, opacity;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
}

.stat-card:hover {
  transform: none;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 8px;
  font-size: 28px;
  color: #fff;
}

.stat-card--projects .stat-icon {
  background: linear-gradient(135deg, var(--workspace-blue, #2f5d8c) 0%, #24486f 100%);
}

.stat-card--files .stat-icon {
  background: linear-gradient(135deg, var(--workspace-accent, #0f766e) 0%, #0b5f59 100%);
}

.stat-card--visits .stat-icon {
  background: linear-gradient(135deg, var(--workspace-amber, #b7791f) 0%, #925f18 100%);
}

.stat-card--exams .stat-icon {
  background: linear-gradient(135deg, var(--color-danger, #b42318) 0%, #8f1c14 100%);
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary, #172033);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: var(--text-tertiary, #7a8798);
}

/* 快捷操作卡片 */
.quick-actions-card {
  margin-bottom: 20px;
  will-change: transform, opacity;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #172033);
}

.quick-actions {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.action-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 24px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
  min-width: 100px;
}

.action-item:hover {
  background-color: var(--surface-muted, #f6f8fb);
}

.action-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 8px;
  font-size: 24px;
  color: #fff;
}

.action-icon--primary {
  background: linear-gradient(135deg, var(--workspace-blue, #2f5d8c) 0%, #24486f 100%);
}

.action-icon--success {
  background: linear-gradient(135deg, var(--workspace-accent, #0f766e) 0%, #0b5f59 100%);
}

.action-icon--warning {
  background: linear-gradient(135deg, var(--workspace-amber, #b7791f) 0%, #925f18 100%);
}

.action-icon--danger {
  background: linear-gradient(135deg, var(--color-danger, #b42318) 0%, #8f1c14 100%);
}

.action-text {
  font-size: 14px;
  color: var(--text-secondary, #475569);
}

/* 内容行 */
.content-row {
  margin-bottom: 20px;
}

/* 列表卡片 */
.list-card {
  height: 100%;
  will-change: transform, opacity;
}

.empty-tip {
  padding: 40px 0;
}

/* 项目/文件列表 */
.item-list {
  display: flex;
  flex-direction: column;
}

.list-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color-light, #e4e9f0);
  cursor: pointer;
  transition: background-color 0.2s;
}

.list-item:last-child {
  border-bottom: none;
}

.list-item:hover {
  background-color: var(--surface-muted, #f6f8fb);
  margin: 0 -20px;
  padding-left: 20px;
  padding-right: 20px;
}

.item-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background-color: #e6eef5;
  border-radius: 8px;
  color: var(--workspace-blue, #2f5d8c);
  font-size: 18px;
}

.item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.item-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #172033);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-meta {
  font-size: 12px;
  color: var(--text-tertiary, #7a8798);
}

/* 考试卡片 */
.exams-card {
  margin-bottom: 20px;
  will-change: transform, opacity;
}

.exam-list {
  display: flex;
  flex-direction: column;
}

.exam-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color-light, #e4e9f0);
  cursor: pointer;
  transition: background-color 0.2s;
}

.exam-item:last-child {
  border-bottom: none;
}

.exam-item:hover {
  background-color: var(--surface-muted, #f6f8fb);
  margin: 0 -20px;
  padding-left: 20px;
  padding-right: 20px;
}

.exam-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.exam-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #172033);
}

.exam-time {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-tertiary, #7a8798);
}

/* 骨架屏 */
.skeleton-wrapper {
  padding: 20px 0;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .stat-content {
    flex-direction: column;
    text-align: center;
    gap: 12px;
  }

  .stat-icon {
    width: 48px;
    height: 48px;
    font-size: 24px;
  }

  .stat-value {
    font-size: 24px;
  }

  .quick-actions {
    justify-content: space-between;
  }

  .action-item {
    flex: 1;
    min-width: 70px;
    padding: 12px 8px;
  }

  .action-icon {
    width: 40px;
    height: 40px;
    font-size: 20px;
  }

  .action-text {
    font-size: 12px;
  }
}

@media (max-width: 480px) {
  .quick-actions {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .action-item {
    flex-direction: row;
    justify-content: flex-start;
    gap: 12px;
    padding: 12px;
  }
}
</style>
