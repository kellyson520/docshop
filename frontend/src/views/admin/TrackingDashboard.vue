<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <PageHeader
      title="用户追踪监控面板"
      :breadcrumbs="breadcrumbs"
      subtitle="实时监控网站访问和用户行为"
    >
      <template #actions>
        <el-button @click="handleExport" :loading="exporting" :disabled="exporting" class="btn-hover-lift">
          <el-icon><Download /></el-icon>
          导出数据
        </el-button>
        <el-button @click="handleRefresh" :loading="isRefreshing">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </template>
    </PageHeader>

    <el-card shadow="never" class="tracking-control-card mb-4">
      <div class="tracking-controls">
        <div class="control-group">
          <span class="control-label">统计周期</span>
          <el-radio-group v-model="statsPeriod" size="small" @change="handlePeriodChange">
            <el-radio-button
              v-for="option in periodOptions"
              :key="option.value"
              :label="option.value"
            >
              {{ option.label }}
            </el-radio-button>
          </el-radio-group>
        </div>
        <div class="control-group">
          <span class="control-label">趋势粒度</span>
          <el-select
            v-model="statsGranularity"
            size="small"
            class="control-select"
            @change="fetchStats"
          >
            <el-option label="自动对齐" value="auto" />
            <el-option label="按小时" value="hour" />
            <el-option label="按天" value="day" />
          </el-select>
        </div>
        <div class="control-group">
          <span class="control-label">实时窗口</span>
          <el-select
            v-model="realtimeMinutes"
            size="small"
            class="control-select"
            @change="handleRealtimeWindowChange"
          >
            <el-option
              v-for="option in realtimeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </div>
        <div class="range-summary">
          <el-tag size="small" type="info">{{ currentPeriodLabel }}</el-tag>
          <el-tag size="small" type="success">趋势：{{ trendGranularityLabel }}</el-tag>
          <el-tag size="small" type="warning">日志已对齐统计周期</el-tag>
        </div>
      </div>
    </el-card>

    <!-- 配置卡片 -->
    <el-card shadow="never" class="config-card mb-4">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon><Setting /></el-icon>
            追踪配置
          </span>
        </div>
      </template>
      <div class="config-grid" v-if="config">
        <div class="config-item">
          <label class="config-label">总开关</label>
          <el-switch
            v-model="config.enable_tracking"
            :active-value="1"
            :inactive-value="0"
            @change="updateConfig('enable_tracking', $event)"
          />
        </div>
        <div class="config-item">
          <label class="config-label">IP追踪</label>
          <el-switch
            v-model="config.enable_ip_tracking"
            :active-value="1"
            :inactive-value="0"
            @change="updateConfig('enable_ip_tracking', $event)"
          />
        </div>
        <div class="config-item">
          <label class="config-label">设备追踪</label>
          <el-switch
            v-model="config.enable_device_tracking"
            :active-value="1"
            :inactive-value="0"
            @change="updateConfig('enable_device_tracking', $event)"
          />
        </div>
        <div class="config-item">
          <label class="config-label">位置追踪</label>
          <el-switch
            v-model="config.enable_location_tracking"
            :active-value="1"
            :inactive-value="0"
            @change="updateConfig('enable_location_tracking', $event)"
          />
        </div>
        <div class="config-item">
          <label class="config-label">行为追踪</label>
          <el-switch
            v-model="config.enable_behavior_tracking"
            :active-value="1"
            :inactive-value="0"
            @change="updateConfig('enable_behavior_tracking', $event)"
          />
        </div>
        <div class="config-item">
          <label class="config-label">IP匿名化</label>
          <el-switch
            v-model="config.anonymize_ip"
            :active-value="1"
            :inactive-value="0"
            @change="updateConfig('anonymize_ip', $event)"
          />
        </div>
        <div class="config-item full-width">
          <label class="config-label">数据保留天数</label>
          <el-slider
            v-model="config.data_retention_days"
            :min="1"
            :max="365"
            show-stops
            @change="updateConfig('data_retention_days', $event)"
          />
          <span class="slider-value">{{ config.data_retention_days }} 天</span>
        </div>
      </div>
    </el-card>

    <!-- 统计概览 -->
    <el-row :gutter="20" class="mb-4">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-icon bg-primary">
            <el-icon><View /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.total_visits || 0 }}</div>
            <div class="stat-label">总访问量 · {{ currentPeriodLabel }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-icon bg-success">
            <el-icon><User /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.unique_visitors || 0 }}</div>
            <div class="stat-label">独立访客 · {{ currentPeriodLabel }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-icon bg-warning">
            <el-icon><Timer /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.response_time?.avg_ms || 0 }}ms</div>
            <div class="stat-label">平均响应时间 · {{ currentPeriodLabel }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-icon bg-info">
            <el-icon><Clock /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ realtimeStats.online_sessions || 0 }}</div>
            <div class="stat-label">在线会话 · {{ recentWindowLabel }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 实时统计 -->
    <el-card shadow="never" class="mb-4">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon><DataLine /></el-icon>
            实时统计
          </span>
          <span class="refresh-time">{{ recentWindowLabel }} · 更新于 {{ lastUpdateTime }}</span>
        </div>
      </template>
      <div class="realtime-stats">
        <div class="realtime-stat-item">
          <div class="realtime-value">{{ realtimeStats.recent_visits || 0 }}</div>
          <div class="realtime-label">{{ recentWindowLabel }}访问</div>
        </div>
        <div class="realtime-stat-item">
          <div class="realtime-value">{{ realtimeStats.online_sessions || 0 }}</div>
          <div class="realtime-label">{{ recentWindowLabel }}在线会话</div>
        </div>
        <div class="realtime-stat-item">
          <div class="realtime-value">{{ realtimeStats.active_users?.length || 0 }}</div>
          <div class="realtime-label">{{ recentWindowLabel }}活跃用户</div>
        </div>
      </div>
      <div class="realtime-detail-grid">
        <div class="top-paths" v-if="realtimeStats.top_paths && realtimeStats.top_paths.length > 0">
          <h3>热门路径 · {{ recentWindowLabel }}</h3>
          <el-table :data="realtimeStats.top_paths" size="small" stripe>
            <el-table-column prop="path" label="路径" min-width="200" />
            <el-table-column prop="count" label="访问次数" width="120" align="center" />
          </el-table>
        </div>
        <div class="top-paths" v-if="realtimeStats.active_users && realtimeStats.active_users.length > 0">
          <h3>活跃用户 · {{ recentWindowLabel }}</h3>
          <el-table :data="realtimeStats.active_users" size="small" stripe>
            <el-table-column prop="user_id" label="用户ID" min-width="220" show-overflow-tooltip />
            <el-table-column prop="count" label="访问次数" width="120" align="center" />
          </el-table>
        </div>
      </div>
    </el-card>

    <!-- 访问统计 -->
    <el-card shadow="never" class="mb-4">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon><TrendCharts /></el-icon>
            访问统计
          </span>
          <span class="metric-chip">{{ currentPeriodLabel }} · {{ trendGranularityLabel }}</span>
        </div>
      </template>

      <!-- 设备分布 -->
      <div class="distribution-section">
        <h3>设备分布</h3>
        <div class="distribution-grid">
          <div class="distribution-item">
            <h4>设备类型</h4>
            <el-table :data="deviceDistributionRows" size="small" stripe>
              <el-table-column prop="type" label="类型" />
              <el-table-column prop="count" label="数量" width="80" align="center" />
            </el-table>
          </div>
          <div class="distribution-item">
            <h4>浏览器</h4>
            <el-table :data="browserDistributionRows" size="small" stripe>
              <el-table-column prop="name" label="浏览器" />
              <el-table-column prop="count" label="数量" width="80" align="center" />
            </el-table>
          </div>
          <div class="distribution-item">
            <h4>操作系统</h4>
            <el-table :data="osDistributionRows" size="small" stripe>
              <el-table-column prop="name" label="系统" />
              <el-table-column prop="count" label="数量" width="80" align="center" />
            </el-table>
          </div>
        </div>
      </div>

      <!-- 每日趋势 -->
      <div class="trend-section">
        <h3>{{ trendTitle }}</h3>
        <el-table :data="trendRows" size="small" stripe>
          <el-table-column prop="label" :label="trendColumnLabel" width="160" />
          <el-table-column prop="visits" label="访问量" width="100" align="center" />
          <el-table-column prop="visitors" label="访客数" width="100" align="center" />
        </el-table>
      </div>

      <div class="distribution-section secondary-distribution">
        <h3>状态与地域</h3>
        <div class="distribution-grid">
          <div class="distribution-item">
            <h4>状态码</h4>
            <el-table :data="statusDistributionRows" size="small" stripe>
              <el-table-column prop="status" label="状态" />
              <el-table-column prop="count" label="数量" width="80" align="center" />
            </el-table>
          </div>
          <div class="distribution-item">
            <h4>访问地域</h4>
            <el-table :data="countryDistributionRows" size="small" stripe>
              <el-table-column prop="country" label="国家/地区" />
              <el-table-column prop="count" label="数量" width="80" align="center" />
            </el-table>
          </div>
          <div class="distribution-item">
            <h4>响应时间</h4>
            <div class="response-grid">
              <div>
                <strong>{{ stats.response_time?.min_ms || 0 }}ms</strong>
                <span>最小</span>
              </div>
              <div>
                <strong>{{ stats.response_time?.avg_ms || 0 }}ms</strong>
                <span>平均</span>
              </div>
              <div>
                <strong>{{ stats.response_time?.max_ms || 0 }}ms</strong>
                <span>最大</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 访问日志 -->
    <el-card shadow="never" class="mb-4">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon><Document /></el-icon>
            访问日志
          </span>
          <span class="metric-chip">日志范围：{{ logsRangeLabel }}</span>
        </div>
      </template>
      <div class="logs-controls">
        <el-input
          v-model="logsFilter.ip"
          placeholder="搜索IP"
          clearable
          size="small"
          class="logs-filter-input"
        />
        <el-select v-model="logsFilter.device_type" placeholder="设备类型" clearable size="small" class="logs-filter-select">
          <el-option label="桌面端" value="desktop" />
          <el-option label="移动端" value="mobile" />
          <el-option label="平板" value="tablet" />
        </el-select>
        <el-date-picker
          v-model="logsRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          size="small"
          class="logs-range-picker"
          @change="handleLogsSearch"
        />
        <el-button type="primary" size="small" @click="handleLogsSearch">查询</el-button>
        <el-button size="small" @click="alignLogsRangeToStatsPeriod">对齐周期</el-button>
        <el-button size="small" @click="resetLogsFilter">重置</el-button>
      </div>

      <el-table :data="logRows" v-loading="logsLoading" size="small" stripe class="logs-table">
        <el-table-column prop="timestamp" label="时间" width="180" />
        <el-table-column prop="ip_address" label="IP地址" width="150" />
        <el-table-column prop="device_type" label="设备" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="getDeviceTypeTag(row.device_type)">
              {{ getDeviceTypeText(row.device_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="os_name" label="系统" width="120" />
        <el-table-column prop="browser_name" label="浏览器" width="120" />
        <el-table-column prop="request_path" label="请求路径" min-width="200" show-overflow-tooltip />
        <el-table-column prop="response_status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.response_status)" size="small">
              {{ row.response_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="response_time_ms" label="响应时间" width="100" align="center">
          <template #default="{ row }">
            {{ row.response_time_ms }}ms
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="logsPage"
        v-model:page-size="logsPageSize"
        :total="logs.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="handleLogsSizeChange"
        @current-change="fetchLogs"
        class="mt-4"
      />
    </el-card>

    <!-- 清理日志 -->
    <el-card shadow="never" class="cleanup-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">
            <el-icon><Delete /></el-icon>
            数据清理
          </span>
        </div>
      </template>
      <div class="cleanup-controls">
        <span class="cleanup-label">清理</span>
        <el-input-number
          v-model="cleanupDays"
          :min="1"
          :max="365"
          size="small"
        />
        <span class="cleanup-label">天前的日志</span>
        <el-button type="danger" size="small" @click="cleanupLogs" :loading="cleanupLoading">
          执行清理
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Download, Refresh, Setting, View, User, Timer, Clock,
  DataLine, TrendCharts, Document, Delete
} from '@element-plus/icons-vue'
import { get, put, del } from '@/api/client'
import PageHeader from '@/components/common/PageHeader.vue'

// ==================== 面包屑 ====================
const breadcrumbs = [
  { title: '追踪监控' }
]

// 配置
const config = ref(null)
const configLoading = ref(false)
const trackingSwitchFields = [
  'enable_tracking',
  'enable_ip_tracking',
  'enable_device_tracking',
  'enable_location_tracking',
  'enable_behavior_tracking',
  'anonymize_ip'
]

function normalizeTrackingConfig(raw = {}) {
  const normalized = { ...raw }
  trackingSwitchFields.forEach((field) => {
    normalized[field] = raw[field] ? 1 : 0
  })
  return normalized
}

// 实时统计
const realtimeStats = ref({})
const lastUpdateTime = ref('--')
let realtimeInterval = null
const isRefreshing = ref(false)
const realtimeMinutes = ref(5)

// 统计
const stats = ref({})
const statsPeriod = ref(7)
const statsGranularity = ref('auto')
const statsLoading = ref(false)

// 日志
const logs = ref({ items: [], total: 0 })
const logsPage = ref(1)
const logsPageSize = ref(20)
const logsFilter = ref({ ip: '', device_type: '' })
const logsRange = ref([])
const logsLoading = ref(false)
const exporting = ref(false)

// 清理
const cleanupDays = ref(90)
const cleanupLoading = ref(false)

const periodOptions = [
  { label: '今天', value: 1 },
  { label: '7天', value: 7 },
  { label: '30天', value: 30 },
  { label: '90天', value: 90 }
]

const realtimeOptions = [
  { label: '最近5分钟', value: 5 },
  { label: '最近15分钟', value: 15 },
  { label: '最近30分钟', value: 30 },
  { label: '最近60分钟', value: 60 }
]

const timezoneOffsetMinutes = -new Date().getTimezoneOffset()

const currentPeriodLabel = computed(() => periodOptions.find(item => item.value === statsPeriod.value)?.label || `${statsPeriod.value}天`)
const recentWindowLabel = computed(() => realtimeOptions.find(item => item.value === realtimeMinutes.value)?.label || `最近${realtimeMinutes.value}分钟`)
const resolvedGranularity = computed(() => stats.value?.granularity || (statsPeriod.value === 1 ? 'hour' : 'day'))
const trendGranularityLabel = computed(() => resolvedGranularity.value === 'hour' ? '按小时' : '按天')
const trendRows = computed(() => stats.value?.trend || stats.value?.daily_trend || [])
const trendTitle = computed(() => `${currentPeriodLabel.value}趋势`)
const trendColumnLabel = computed(() => resolvedGranularity.value === 'hour' ? '小时' : '日期')
const deviceDistributionRows = computed(() => stats.value?.device_distribution || [])
const browserDistributionRows = computed(() => stats.value?.browser_distribution || [])
const osDistributionRows = computed(() => stats.value?.os_distribution || [])
const statusDistributionRows = computed(() => stats.value?.status_distribution || [])
const countryDistributionRows = computed(() => stats.value?.country_distribution || [])
const logRows = computed(() => logs.value?.items || [])
const logsRangeLabel = computed(() => {
  if (!logsRange.value || logsRange.value.length !== 2) return '未限定'
  return `${formatRangeDate(logsRange.value[0])} 至 ${formatRangeDate(logsRange.value[1])}`
})

function isRequestCanceled(error) {
  return error?.name === 'CanceledError' ||
    error?.name === 'AbortError' ||
    error?.code === 'ERR_CANCELED' ||
    String(error?.message || '').includes('重复请求被取消')
}

function getStatsRange() {
  const end = new Date()
  const start = new Date(end)
  start.setHours(0, 0, 0, 0)
  if (statsPeriod.value > 1) {
    start.setDate(start.getDate() - statsPeriod.value + 1)
  }
  return [start, end]
}

function alignLogsRangeToStatsPeriod() {
  logsRange.value = getStatsRange()
  logsPage.value = 1
  fetchLogs()
}

function formatRangeDate(value) {
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  const pad = (number) => String(number).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function toApiDate(value) {
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString()
}

function buildLogsParams(overrides = {}) {
  const params = {
    page: logsPage.value,
    page_size: logsPageSize.value,
    ...logsFilter.value,
    ...overrides
  }
  if (logsRange.value && logsRange.value.length === 2) {
    params.start_date = toApiDate(logsRange.value[0])
    params.end_date = toApiDate(logsRange.value[1])
  }
  return params
}

// 获取配置（client.js 已解包 ApiResponse，直接取 data）
const fetchConfig = async () => {
  try {
    config.value = normalizeTrackingConfig(await get('/admin/tracking/config'))
  } catch (error) {
    if (isRequestCanceled(error)) return
    ElMessage.error('获取配置失败')
  }
}

// 更新配置
const updateConfig = async (key, value) => {
  if (configLoading.value) return
  configLoading.value = true
  try {
    const params = { [key]: value }
    const result = await put('/admin/tracking/config', null, { params })
    if (result?.config) {
      config.value = normalizeTrackingConfig(result.config)
    }
    ElMessage.success('配置已更新')
  } catch (error) {
    if (isRequestCanceled(error)) return
    ElMessage.error('更新配置失败')
    await fetchConfig()
  } finally {
    configLoading.value = false
  }
}

// 获取实时统计
const fetchRealtimeStats = async () => {
  try {
    realtimeStats.value = await get('/admin/tracking/realtime', { minutes: realtimeMinutes.value })
    lastUpdateTime.value = new Date().toLocaleTimeString()
  } catch (error) {
    if (isRequestCanceled(error)) return
    console.error('获取实时统计失败', error)
  }
}

// 获取统计
const fetchStats = async () => {
  statsLoading.value = true
  try {
    stats.value = await get('/admin/tracking/stats', {
      days: statsPeriod.value,
      granularity: statsGranularity.value,
      timezone_offset_minutes: timezoneOffsetMinutes
    })
  } catch (error) {
    if (isRequestCanceled(error)) return
    ElMessage.error('获取统计失败')
  } finally {
    statsLoading.value = false
  }
}

// 获取日志
const fetchLogs = async () => {
  logsLoading.value = true
  try {
    logs.value = await get('/admin/tracking/logs', buildLogsParams())
  } catch (error) {
    if (isRequestCanceled(error)) return
    ElMessage.error('获取日志失败')
  } finally {
    logsLoading.value = false
  }
}

// 重置日志筛选
const resetLogsFilter = () => {
  logsFilter.value = { ip: '', device_type: '' }
  logsPage.value = 1
  alignLogsRangeToStatsPeriod()
}

const handleLogsSearch = () => {
  logsPage.value = 1
  fetchLogs()
}

const handleLogsSizeChange = () => {
  logsPage.value = 1
  fetchLogs()
}

const handlePeriodChange = async () => {
  logsRange.value = getStatsRange()
  logsPage.value = 1
  await Promise.all([fetchStats(), fetchLogs()])
}

const handleRealtimeWindowChange = () => {
  fetchRealtimeStats()
  startPolling()
}

// 获取设备类型标签
const getDeviceTypeTag = (type) => {
  const map = { desktop: '', mobile: 'success', tablet: 'warning' }
  return map[type] || 'info'
}

// 获取设备类型文本
const getDeviceTypeText = (type) => {
  const map = { desktop: '桌面端', mobile: '移动端', tablet: '平板' }
  return map[type] || type
}

// 获取状态类型
const getStatusType = (status) => {
  if (status >= 200 && status < 300) return 'success'
  if (status >= 300 && status < 400) return 'warning'
  return 'danger'
}

// 清理日志
const cleanupLogs = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要清理 ${cleanupDays.value} 天前的日志吗？`,
      '确认清理',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    cleanupLoading.value = true
    const result = await del('/admin/tracking/logs', { params: { days: cleanupDays.value } })
    ElMessage.success(`已清理 ${result.deleted_count} 条日志`)
    fetchLogs()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清理失败')
    }
  } finally {
    cleanupLoading.value = false
  }
}

// 刷新所有数据
const handleRefresh = async () => {
  isRefreshing.value = true
  try {
    await Promise.all([fetchConfig(), fetchRealtimeStats(), fetchStats(), fetchLogs()])
    ElMessage.success('数据已刷新')
  } finally {
    isRefreshing.value = false
  }
}

async function fetchAllLogsForExport() {
  const pageSize = 200
  let page = 1
  let total = 0
  const rows = []

  do {
    const data = await get('/admin/tracking/logs', buildLogsParams({ page, page_size: pageSize }), { cancelable: false })
    const items = data?.items || []
    total = Number(data?.total || items.length || 0)
    rows.push(...items)
    if (!items.length) break
    page += 1
  } while (rows.length < total)

  return rows
}

// 导出数据
const handleExport = async () => {
  if (exporting.value) return
  exporting.value = true
  try {
    const rows = await fetchAllLogsForExport()
    if (!rows.length) {
      ElMessage.warning('当前范围没有可导出的日志')
      return
    }

    const headers = ['时间', 'IP地址', '设备', '系统', '浏览器', '请求路径', '状态', '响应时间(ms)']
    const body = rows.map(row => [
      row.timestamp,
      row.ip_address,
      getDeviceTypeText(row.device_type),
      row.os_name || '',
      row.browser_name || '',
      row.request_path || '',
      row.response_status || '',
      row.response_time_ms || 0
    ])
    downloadCsv(`tracking-${statsPeriod.value}d-${Date.now()}.csv`, [headers, ...body])
    ElMessage.success(`已导出 ${rows.length} 条日志`)
  } catch (error) {
    if (!isRequestCanceled(error)) {
      ElMessage.error('导出失败')
    }
  } finally {
    exporting.value = false
  }
}

function escapeCsvCell(value) {
  const text = String(value ?? '')
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

function downloadCsv(filename, rows) {
  const csv = rows.map(row => row.map(escapeCsvCell).join(',')).join('\r\n')
  const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// ==================== 页面可见性轮询控制 ====================

/**
 * 开始轮询实时统计
 */
function startPolling() {
  stopPolling()
  realtimeInterval = setInterval(fetchRealtimeStats, 30000)
}

/**
 * 停止轮询实时统计
 */
function stopPolling() {
  if (realtimeInterval) {
    clearInterval(realtimeInterval)
    realtimeInterval = null
  }
}

/**
 * 处理页面可见性变化
 * 标签页不可见时暂停轮询，可见时恢复
 */
function handleVisibilityChange() {
  if (document.hidden) {
    stopPolling()
  } else {
    // 页面重新可见时立即刷新一次，然后恢复轮询
    fetchRealtimeStats()
    startPolling()
  }
}

// 初始化
onMounted(() => {
  logsRange.value = getStatsRange()
  fetchConfig()
  fetchRealtimeStats()
  fetchStats()
  fetchLogs()

  // 定时刷新实时统计
  startPolling()

  // 监听页面可见性变化
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  stopPolling()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<style scoped>
/* 页面头部 */
.refresh-time {
  font-size: 12px;
  color: #909399;
}

.tracking-control-card {
  border: 1px solid var(--border-color-light, #e4e9f0);
  border-radius: 12px;
}

.tracking-controls {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.control-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.control-label {
  color: var(--text-tertiary, #7a8798);
  font-size: 13px;
  white-space: nowrap;
}

.control-select {
  width: 128px;
}

.range-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-left: auto;
}

.metric-chip {
  color: var(--text-tertiary, #7a8798);
  font-size: 12px;
}

/* 配置卡片 */
.config-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.config-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.config-item.full-width {
  grid-column: 1 / -1;
  flex-direction: column;
  align-items: flex-start;
}

.config-label {
  font-size: 14px;
  color: #606266;
  min-width: 80px;
}

.slider-value {
  margin-top: 8px;
  font-size: 14px;
  color: #909399;
}

/* 统计卡片 */
.stat-card {
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
}

.stat-icon.bg-primary { background: linear-gradient(135deg, #1A5276, #2980b9); }
.stat-icon.bg-success { background: linear-gradient(135deg, #27AE60, #2ecc71); }
.stat-icon.bg-warning { background: linear-gradient(135deg, #F39C12, #f1c40f); }
.stat-icon.bg-info { background: linear-gradient(135deg, var(--color-info, #64748b), #8a97a8); }

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary, #172033);
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: var(--text-tertiary, #7a8798);
  margin-top: 4px;
}

/* 实时统计 */
.realtime-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.realtime-stat-item {
  text-align: center;
  padding: 20px;
  background: linear-gradient(135deg, #f8fafc 0%, #e6eef5 100%);
  border: 1px solid var(--border-color-light, #e4e9f0);
  border-radius: 8px;
}

[data-theme="dark"] .realtime-stat-item {
  background: linear-gradient(135deg, #1a3a5c, #1a2a4c);
}

.realtime-value {
  font-size: 36px;
  font-weight: 700;
  color: var(--workspace-blue, #2f5d8c);
  line-height: 1.2;
}

.realtime-label {
  font-size: 14px;
  color: var(--text-tertiary, #7a8798);
  margin-top: 8px;
}

.realtime-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.top-paths {
  margin-top: 16px;
}

.top-paths h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: var(--text-secondary, #475569);
  font-weight: 500;
}

/* 分布区域 */
.distribution-section {
  margin-bottom: 24px;
}

.distribution-section h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: var(--text-primary, #172033);
  font-weight: 600;
}

.distribution-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.distribution-item h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: var(--text-secondary, #475569);
  font-weight: 500;
}

.secondary-distribution {
  margin-top: 24px;
}

.response-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.response-grid div {
  display: grid;
  gap: 4px;
  padding: 14px;
  text-align: center;
  background: var(--surface-muted, #f6f8fb);
  border: 1px solid var(--border-color-light, #e4e9f0);
  border-radius: 8px;
}

.response-grid strong {
  color: var(--workspace-blue, #2f5d8c);
  font-size: 18px;
}

.response-grid span {
  color: var(--text-tertiary, #7a8798);
  font-size: 12px;
}

/* 趋势区域 */
.trend-section {
  margin-top: 24px;
}

.trend-section h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  color: #303133;
  font-weight: 600;
}

/* 日志区域 */
.logs-controls {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.logs-filter-input {
  width: 180px;
}

.logs-filter-select {
  width: 120px;
}

.logs-range-picker {
  width: 340px;
}

.logs-table {
  border-radius: 8px;
  overflow: hidden;
}

/* 清理区域 */
.cleanup-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.cleanup-label {
  font-size: 14px;
  color: #606266;
}

/* 响应式 */
@media (max-width: 768px) {
  .tracking-controls,
  .control-group {
    align-items: stretch;
    width: 100%;
  }

  .tracking-controls {
    flex-direction: column;
  }

  .control-group {
    flex-direction: column;
  }

  .control-select,
  .range-summary {
    width: 100%;
    margin-left: 0;
  }

  .config-grid {
    grid-template-columns: 1fr;
  }

  .realtime-stats {
    grid-template-columns: 1fr;
  }

  .realtime-stat-item {
    padding: 16px;
  }

  .realtime-detail-grid {
    grid-template-columns: 1fr;
  }

  .realtime-detail-grid > *,
  .top-paths,
  .trend-section,
  .distribution-item {
    min-width: 0;
    max-width: 100%;
  }

  .stat-card {
    flex-direction: column;
    text-align: center;
  }

  .stat-value {
    font-size: 24px;
  }

  .distribution-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .card-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 6px;
  }

  .metric-chip,
  .refresh-time {
    white-space: normal;
  }

  .logs-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .logs-filter-input,
  .logs-filter-select,
  .logs-range-picker {
    width: 100%;
  }

  .cleanup-controls {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
