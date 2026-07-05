<template>
  <div class="user-activities">
    <el-page-header title="活动记录" @back="$router.back()" />
    
    <el-card class="activities-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="header-title">操作记录</span>
            <el-tag type="info" size="small">共 {{ total }} 条</el-tag>
          </div>
          <div class="header-right">
            <el-button type="primary" text @click="exportActivities">
              <el-icon><Download /></el-icon>
              导出记录
            </el-button>
          </div>
        </div>
      </template>

      <!-- 筛选区 -->
      <div class="filter-section">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="8" :md="6">
            <el-select v-model="filter.type" placeholder="活动类型" clearable class="filter-item">
              <el-option label="全部类型" value="" />
              <el-option label="上传文件" value="upload" />
              <el-option label="下载文件" value="download" />
              <el-option label="创建项目" value="create" />
              <el-option label="删除项目" value="delete" />
              <el-option label="编辑项目" value="edit" />
              <el-option label="版本对比" value="diff" />
              <el-option label="分享项目" value="share" />
              <el-option label="登录" value="login" />
            </el-select>
          </el-col>
          <el-col :xs="24" :sm="8" :md="6">
            <el-date-picker
              v-model="filter.dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              class="filter-item"
              value-format="YYYY-MM-DD"
            />
          </el-col>
          <el-col :xs="24" :sm="8" :md="6">
            <el-input v-model="filter.keyword" placeholder="搜索关键词" clearable class="filter-item">
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :xs="24" :sm="24" :md="6" class="filter-actions">
            <el-button type="primary" @click="handleFilter">
              <el-icon><Search /></el-icon>
              查询
            </el-button>
            <el-button @click="resetFilter">
              <el-icon><RefreshRight /></el-icon>
              重置
            </el-button>
          </el-col>
        </el-row>
      </div>

      <!-- 活动列表 -->
      <div class="activities-list">
        <el-timeline>
          <el-timeline-item
            v-for="activity in activities"
            :key="activity.id"
            :type="activity.type"
            :timestamp="activity.time"
            :icon="getActivityIcon(activity.action)"
            placement="top"
          >
            <el-card shadow="hover" class="activity-card">
              <div class="activity-content">
                <div class="activity-main">
                  <div class="activity-icon-wrapper" :class="activity.action">
                    <el-icon :size="20">
                      <component :is="getActivityIcon(activity.action)" />
                    </el-icon>
                  </div>
                  <div class="activity-info">
                    <div class="activity-title">
                      <span class="action-text">{{ activity.description }}</span>
                      <el-tag v-if="activity.projectName" size="small" type="info" effect="plain">
                        {{ activity.projectName }}
                      </el-tag>
                    </div>
                    <div class="activity-meta">
                      <span class="meta-item">
                        <el-icon><Timer /></el-icon>
                        {{ activity.time }}
                      </span>
                      <span v-if="activity.ip" class="meta-item">
                        <el-icon><Location /></el-icon>
                        {{ activity.ip }}
                      </span>
                      <span v-if="activity.device" class="meta-item">
                        <el-icon><Monitor /></el-icon>
                        {{ activity.device }}
                      </span>
                    </div>
                  </div>
                </div>
                <div class="activity-actions">
                  <el-button text type="primary" size="small" @click="viewDetail(activity)">
                    查看详情
                  </el-button>
                </div>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>

        <el-empty v-if="activities.length === 0 && !loading" description="暂无活动记录" />
        
        <div v-if="loading" class="loading-wrapper">
          <el-skeleton :rows="5" animated />
        </div>
      </div>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialog.visible" title="活动详情" width="500px" destroy-on-close>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="操作类型">
          <el-tag :type="detailDialog.data?.type">{{ detailDialog.data?.description }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="项目名称">{{ detailDialog.data?.projectName || '-' }}</el-descriptions-item>
        <el-descriptions-item label="操作时间">{{ detailDialog.data?.time }}</el-descriptions-item>
        <el-descriptions-item label="IP 地址">{{ detailDialog.data?.ip || '-' }}</el-descriptions-item>
        <el-descriptions-item label="设备信息">{{ detailDialog.data?.device || '-' }}</el-descriptions-item>
        <el-descriptions-item label="详细内容">
          <div class="detail-content">{{ detailDialog.data?.detail || '暂无详细内容' }}</div>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { get } from '@/api/client'
import {
  Download, Search, RefreshRight, Timer, Location, Monitor,
  Upload, Plus, Delete, EditPen, View, Share, User
} from '@element-plus/icons-vue'

const loading = ref(false)
const total = ref(0)

const filter = reactive({
  type: '',
  dateRange: [],
  keyword: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20
})

const activities = ref([])

const detailDialog = reactive({
  visible: false,
  data: null
})

const actionTypeMap = {
  view: 'primary',
  visit: 'primary',
  upload: 'primary',
  create: 'success',
  login: 'success',
  download: 'warning',
  diff: 'info',
  edit: 'info',
  share: 'primary',
  delete: 'danger'
}

function getActivityIcon(action) {
  const iconMap = {
    upload: 'Upload',
    download: 'Download',
    create: 'Plus',
    delete: 'Delete',
    edit: 'EditPen',
    diff: 'View',
    share: 'Share',
    login: 'User',
    view: 'View',
    visit: 'View'
  }
  return iconMap[action] || 'CircleCheck'
}

function inferAction(item) {
  const action = item.action || item.action_type
  if (action) return action

  const method = String(item.request_method || '').toUpperCase()
  const path = String(item.request_path || '')
  if (method === 'POST' && path.includes('/upload')) return 'upload'
  if (method === 'GET' && path.includes('/download')) return 'download'
  if (method === 'POST') return 'create'
  if (method === 'PUT' || method === 'PATCH') return 'edit'
  if (method === 'DELETE') return 'delete'
  return 'view'
}

function describeAction(item, action) {
  if (item.description) return item.description
  const path = item.request_path || item.target_type || 'resource'
  const labels = {
    upload: 'Uploaded file',
    download: 'Downloaded file',
    create: 'Created resource',
    delete: 'Deleted resource',
    edit: 'Edited resource',
    diff: 'Compared versions',
    share: 'Shared project',
    login: 'User login',
    view: 'Viewed page',
    visit: 'Viewed page'
  }
  return `${labels[action] || 'Performed action'}: ${path}`
}

function normalizeActivity(item, index) {
  const action = inferAction(item)
  const browser = item.browser_name || item.browser
  const os = item.os_name || item.os
  const device = item.device || [browser, os].filter(Boolean).join(' / ') || item.device_type || ''
  const projectName = item.projectName || item.project_name || item.target_name || item.target_id || ''
  const time = item.time || item.timestamp || item.created_at || ''

  return {
    id: item.id || `${time}-${index}`,
    action,
    description: describeAction(item, action),
    projectName,
    time,
    ip: item.ip || item.ip_address || '',
    device,
    type: item.type || actionTypeMap[action] || 'info',
    detail: item.detail || [
      item.request_method && item.request_path ? `${item.request_method} ${item.request_path}` : '',
      item.response_status ? `Status: ${item.response_status}` : '',
      item.response_time_ms ? `Duration: ${item.response_time_ms}ms` : ''
    ].filter(Boolean).join('\n')
  }
}

function applyClientFilters(list) {
  let filtered = list

  if (filter.type) {
    filtered = filtered.filter(item => item.action === filter.type)
  }

  if (filter.keyword) {
    const keyword = filter.keyword.toLowerCase()
    filtered = filtered.filter(item =>
      item.description.toLowerCase().includes(keyword) ||
      (item.projectName && item.projectName.toLowerCase().includes(keyword)) ||
      (item.detail && item.detail.toLowerCase().includes(keyword))
    )
  }

  if (filter.dateRange && filter.dateRange.length === 2) {
    const startDate = new Date(filter.dateRange[0])
    const endDate = new Date(filter.dateRange[1])
    endDate.setHours(23, 59, 59, 999)
    filtered = filtered.filter(item => {
      const itemDate = new Date(item.time)
      return itemDate >= startDate && itemDate <= endDate
    })
  }

  return filtered
}

function buildActivityParams() {
  const params = {
    page: pagination.page,
    page_size: pagination.pageSize,
    action_type: filter.type || undefined,
    keyword: filter.keyword || undefined
  }

  if (filter.dateRange && filter.dateRange.length === 2) {
    params.start_date = filter.dateRange[0]
    params.end_date = filter.dateRange[1]
  }

  return params
}

async function loadActivities() {
  loading.value = true
  try {
    const data = await get('/admin/tracking/logs', buildActivityParams())
    const rawItems = Array.isArray(data) ? data : (data.items || [])
    const normalized = rawItems.map(normalizeActivity)
    const filtered = applyClientFilters(normalized)

    activities.value = filtered
    total.value = filter.type || filter.keyword || filter.dateRange?.length === 2
      ? filtered.length
      : (data.total ?? filtered.length)
  } catch (error) {
    activities.value = []
    total.value = 0
    ElMessage.error(error.message || 'Failed to load activity records')
  } finally {
    loading.value = false
  }
}

function handleFilter() {
  pagination.page = 1
  loadActivities()
}

function resetFilter() {
  filter.type = ''
  filter.dateRange = []
  filter.keyword = ''
  pagination.page = 1
  loadActivities()
}

function handleSizeChange(size) {
  pagination.pageSize = size
  pagination.page = 1
  loadActivities()
}

function handlePageChange(page) {
  pagination.page = page
  loadActivities()
}

function viewDetail(activity) {
  detailDialog.data = activity
  detailDialog.visible = true
}

function exportActivities() {
  if (!activities.value.length) {
    ElMessage.warning('No activity records to export')
    return
  }

  const data = activities.value.map(item => ({
    Time: item.time,
    Action: item.description,
    Project: item.projectName || '-',
    IP: item.ip || '-',
    Device: item.device || '-',
    Detail: item.detail || '-'
  }))

  const headers = Object.keys(data[0] || {})
  const csvContent = [
    headers.join(','),
    ...data.map(row => headers.map(h => `"${String(row[h]).replace(/"/g, '""')}"`).join(','))
  ].join('\n')

  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `activities_${new Date().toISOString().split('T')[0]}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)

  ElMessage.success('Exported successfully')
}

onMounted(() => {
  loadActivities()
})
</script>

<style scoped>
.user-activities {
  height: calc(100vh - 48px);
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
}

.activities-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-top: 16px;
  overflow: hidden;
}

.activities-card :deep(.el-card__header) {
  flex: 0 0 auto;
}

.activities-card :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px 20px 18px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
}

/* 筛选区 */
.filter-section {
  flex: 0 0 auto;
  padding: 14px;
  background: var(--bg-primary, #f5f7fa);
  border-radius: 8px;
  margin-bottom: 14px;
}

.filter-item {
  width: 100%;
}

.filter-actions {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

/* 活动列表 */
.activities-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 4px 12px 0;
  scrollbar-gutter: stable;
}

.activities-list::-webkit-scrollbar {
  width: 8px;
}

.activities-list::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(47, 93, 140, 0.24);
}

.activities-list::-webkit-scrollbar-track {
  background: transparent;
}

.activity-card {
  margin-bottom: 8px;
}

.activity-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.activity-main {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}

.activity-icon-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.activity-icon-wrapper.upload { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.activity-icon-wrapper.download { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
.activity-icon-wrapper.create { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
.activity-icon-wrapper.delete { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
.activity-icon-wrapper.edit { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
.activity-icon-wrapper.diff { background: linear-gradient(135deg, #30cfd0 0%, #330867 100%); }
.activity-icon-wrapper.share { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); color: #606266; }
.activity-icon-wrapper.login { background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); color: #606266; }

.activity-info {
  flex: 1;
}

.activity-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.action-text {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary, #303133);
}

.activity-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-secondary, #909399);
}

.activity-actions {
  flex-shrink: 0;
}

/* 分页 */
.pagination-wrapper {
  flex: 0 0 auto;
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
  border-top: 1px solid var(--border-color, #e4e7ed);
}

.loading-wrapper {
  padding: 20px 0;
}

.detail-content {
  white-space: pre-wrap;
  line-height: 1.6;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .user-activities {
    height: calc(100vh - 94px);
  }

  .filter-section {
    padding: 12px;
  }

  .filter-actions {
    margin-top: 12px;
    justify-content: flex-end;
  }

  .activity-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .activity-main {
    width: 100%;
  }

  .activity-actions {
    width: 100%;
    display: flex;
    justify-content: flex-end;
  }

  .activity-meta {
    gap: 12px;
  }
}
</style>
