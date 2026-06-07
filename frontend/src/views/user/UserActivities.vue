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
import {
  Download, Search, RefreshRight, Timer, Location, Monitor,
  Upload, Download as DownloadIcon, Plus, Delete, EditPen, View, Share, User
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

// 模拟活动数据
const mockActivities = [
  {
    id: 1,
    action: 'upload',
    description: '上传了新文件',
    projectName: '项目A',
    time: '2024-01-15 14:30:25',
    ip: '192.168.1.100',
    device: 'Chrome / Windows',
    type: 'primary',
    detail: '上传文件：document_v2.pdf，大小：2.5MB'
  },
  {
    id: 2,
    action: 'create',
    description: '创建了新项目',
    projectName: '项目B',
    time: '2024-01-15 10:20:18',
    ip: '192.168.1.100',
    device: 'Chrome / Windows',
    type: 'success',
    detail: '创建项目：项目B，项目ID：PRJ-2024-001'
  },
  {
    id: 3,
    action: 'download',
    description: '下载了文件',
    projectName: '项目A',
    time: '2024-01-14 16:45:33',
    ip: '192.168.1.105',
    device: 'Safari / macOS',
    type: 'warning',
    detail: '下载文件：report_final.docx'
  },
  {
    id: 4,
    action: 'diff',
    description: '执行了版本对比',
    projectName: '项目C',
    time: '2024-01-14 09:15:42',
    ip: '192.168.1.100',
    device: 'Chrome / Windows',
    type: 'info',
    detail: '对比版本：v1.0 vs v1.1，发现差异：12处'
  },
  {
    id: 5,
    action: 'share',
    description: '分享了项目链接',
    projectName: '项目A',
    time: '2024-01-13 11:30:15',
    ip: '192.168.1.100',
    device: 'Chrome / Windows',
    type: 'primary',
    detail: '生成分享链接，有效期：7天'
  },
  {
    id: 6,
    action: 'edit',
    description: '编辑了项目信息',
    projectName: '项目B',
    time: '2024-01-13 09:20:08',
    ip: '192.168.1.100',
    device: 'Chrome / Windows',
    type: 'info',
    detail: '修改项目描述和标签'
  },
  {
    id: 7,
    action: 'delete',
    description: '删除了文件',
    projectName: '项目A',
    time: '2024-01-12 16:00:22',
    ip: '192.168.1.100',
    device: 'Chrome / Windows',
    type: 'danger',
    detail: '删除文件：old_version.pdf'
  },
  {
    id: 8,
    action: 'login',
    description: '用户登录',
    projectName: '',
    time: '2024-01-12 08:30:00',
    ip: '192.168.1.100',
    device: 'Chrome / Windows',
    type: 'success',
    detail: '登录成功'
  },
  {
    id: 9,
    action: 'upload',
    description: '上传了新文件',
    projectName: '项目C',
    time: '2024-01-11 15:45:30',
    ip: '192.168.1.110',
    device: 'Firefox / Linux',
    type: 'primary',
    detail: '上传文件：data_export.xlsx，大小：1.2MB'
  },
  {
    id: 10,
    action: 'download',
    description: '批量下载',
    projectName: '项目B',
    time: '2024-01-11 10:10:05',
    ip: '192.168.1.100',
    device: 'Chrome / Windows',
    type: 'warning',
    detail: '批量下载 5 个文件'
  }
]

function getActivityIcon(action) {
  const iconMap = {
    upload: 'Upload',
    download: 'Download',
    create: 'Plus',
    delete: 'Delete',
    edit: 'EditPen',
    diff: 'View',
    share: 'Share',
    login: 'User'
  }
  return iconMap[action] || 'CircleCheck'
}

function loadActivities() {
  loading.value = true
  // 模拟 API 调用
  setTimeout(() => {
    let filtered = [...mockActivities]
    
    // 类型筛选
    if (filter.type) {
      filtered = filtered.filter(item => item.action === filter.type)
    }
    
    // 关键词筛选
    if (filter.keyword) {
      const keyword = filter.keyword.toLowerCase()
      filtered = filtered.filter(item => 
        item.description.toLowerCase().includes(keyword) ||
        (item.projectName && item.projectName.toLowerCase().includes(keyword))
      )
    }
    
    // 日期筛选
    if (filter.dateRange && filter.dateRange.length === 2) {
      const startDate = new Date(filter.dateRange[0])
      const endDate = new Date(filter.dateRange[1])
      filtered = filtered.filter(item => {
        const itemDate = new Date(item.time)
        return itemDate >= startDate && itemDate <= endDate
      })
    }
    
    total.value = filtered.length
    
    // 分页
    const start = (pagination.page - 1) * pagination.pageSize
    const end = start + pagination.pageSize
    activities.value = filtered.slice(start, end)
    
    loading.value = false
  }, 500)
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
  // 模拟导出
  const data = activities.value.map(item => ({
    时间: item.time,
    操作: item.description,
    项目: item.projectName || '-',
    IP地址: item.ip || '-',
    设备: item.device || '-',
    详情: item.detail || '-'
  }))
  
  // 转换为 CSV
  const headers = Object.keys(data[0] || {})
  const csvContent = [
    headers.join(','),
    ...data.map(row => headers.map(h => `"${row[h]}"`).join(','))
  ].join('\n')
  
  // 下载
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `活动记录_${new Date().toISOString().split('T')[0]}.csv`
  link.click()
  
  ElMessage.success('导出成功')
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
