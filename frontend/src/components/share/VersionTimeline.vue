<template>
  <div class="version-timeline">
    <el-timeline>
      <el-timeline-item
        v-for="(version, index) in versions"
        :key="version.id"
        :timestamp="formatDate(version.created_at)"
        placement="top"
        :type="getTimelineType(index)"
        :icon="getTimelineIcon(index)"
        :size="index === 0 ? 'large' : 'normal'"
      >
        <transition name="slide-up" appear>
          <el-card
            shadow="hover"
            class="version-card"
            :class="{
              'is-latest': index === 0,
              'is-major': version.is_major,
              'is-selected': selectedVersionId === version.id
            }"
            @click="handleCardClick(version)"
          >
            <!-- 版本头部 -->
            <div class="version-header">
              <div class="version-badges">
                <el-tag
                  :type="index === 0 ? 'primary' : 'info'"
                  size="small"
                  effect="light"
                  class="version-tag"
                >
                  v{{ version.version_number }}
                </el-tag>
                <el-tag
                  v-if="index === 0"
                  type="success"
                  size="small"
                  effect="light"
                  class="latest-tag"
                >
                  <el-icon><StarFilled /></el-icon>
                  最新
                </el-tag>
                <el-tag
                  v-if="version.is_major"
                  type="warning"
                  size="small"
                  effect="light"
                  class="major-tag"
                >
                  <el-icon><Flag /></el-icon>
                  重要
                </el-tag>
              </div>
              <div class="version-size">
                <el-icon><Document /></el-icon>
                <span>{{ formatFileSize(version.file_size) }}</span>
              </div>
            </div>

            <!-- 变更说明 -->
            <div class="version-body">
              <div v-if="version.changelog" class="changelog">
                <el-icon><EditPen /></el-icon>
                <span>{{ version.changelog }}</span>
              </div>
              <div v-else class="changelog empty">
                <el-icon><InfoFilled /></el-icon>
                <span>无变更说明</span>
              </div>

              <!-- 变更统计 -->
              <div v-if="version.changes" class="changes-stats">
                <el-tooltip content="新增" placement="top">
                  <div v-if="version.changes.added > 0" class="stat-item added">
                    <el-icon><Plus /></el-icon>
                    <span>{{ version.changes.added }}</span>
                  </div>
                </el-tooltip>
                <el-tooltip content="删除" placement="top">
                  <div v-if="version.changes.deleted > 0" class="stat-item deleted">
                    <el-icon><Minus /></el-icon>
                    <span>{{ version.changes.deleted }}</span>
                  </div>
                </el-tooltip>
                <el-tooltip content="修改" placement="top">
                  <div v-if="version.changes.modified > 0" class="stat-item modified">
                    <el-icon><Edit /></el-icon>
                    <span>{{ version.changes.modified }}</span>
                  </div>
                </el-tooltip>
              </div>
            </div>

            <!-- 版本底部 -->
            <div class="version-footer">
              <div class="version-time">
                <el-icon><Clock /></el-icon>
                <span>{{ formatRelativeTime(version.created_at) }}</span>
              </div>
              <div class="version-actions" @click.stop>
                <el-tooltip content="下载此版本" placement="top">
                  <el-button
                    circle
                    type="primary"
                    plain
                    size="small"
                    :loading="version.downloading"
                    @click="handleDownload(version)"
                  >
                    <el-icon><Download /></el-icon>
                  </el-button>
                </el-tooltip>

                <el-tooltip
                  v-if="index < versions.length - 1"
                  content="与上一版本对比"
                  placement="top"
                >
                  <el-button
                    circle
                    type="warning"
                    plain
                    size="small"
                    @click="handleCompare(version)"
                  >
                    <el-icon><Sort /></el-icon>
                  </el-button>
                </el-tooltip>

                <el-dropdown v-if="showMoreActions" trigger="click" @command="handleCommand($event, version)">
                  <el-button circle plain size="small">
                    <el-icon><MoreFilled /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="preview">
                        <el-icon><View /></el-icon>
                        预览
                      </el-dropdown-item>
                      <el-dropdown-item command="copy-link">
                        <el-icon><Link /></el-icon>
                        复制链接
                      </el-dropdown-item>
                      <el-dropdown-item v-if="canRestore" command="restore" divided>
                        <el-icon><RefreshLeft /></el-icon>
                        恢复此版本
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </el-card>
        </transition>
      </el-timeline-item>
    </el-timeline>

    <!-- 空状态 -->
    <div v-if="versions.length === 0" class="empty-state">
      <el-empty description="暂无版本记录">
        <template #image>
          <div class="custom-empty-icon">
            <el-icon :size="64"><Clock /></el-icon>
          </div>
        </template>
      </el-empty>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  StarFilled,
  Flag,
  Document,
  EditPen,
  InfoFilled,
  Plus,
  Minus,
  Edit,
  Clock,
  Download,
  Sort,
  MoreFilled,
  View,
  Link,
  RefreshLeft
} from '@element-plus/icons-vue'
import { formatFileSize } from '@/utils'

const props = defineProps({
  /**
   * 版本列表
   */
  versions: {
    type: Array,
    default: () => []
  },
  /**
   * 当前选中的版本ID
   */
  selectedVersionId: {
    type: [String, Number],
    default: null
  },
  /**
   * 是否显示更多操作
   */
  showMoreActions: {
    type: Boolean,
    default: true
  },
  /**
   * 是否可以恢复版本
   */
  canRestore: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'select',
  'download',
  'compare',
  'preview',
  'copy-link',
  'restore'
])

// 获取时间线类型
function getTimelineType(index) {
  if (index === 0) return 'primary'
  if (props.versions[index]?.is_major) return 'warning'
  return 'info'
}

// 获取时间线图标
function getTimelineIcon(index) {
  if (index === 0) return StarFilled
  if (props.versions[index]?.is_major) return Flag
  return null
}

// 格式化日期
function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 格式化相对时间
function formatRelativeTime(dateStr) {
  if (!dateStr) return '-'

  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now - date
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)
  const diffWeeks = Math.floor(diffDays / 7)
  const diffMonths = Math.floor(diffDays / 30)

  if (diffSecs < 60) {
    return '刚刚'
  } else if (diffMins < 60) {
    return `${diffMins} 分钟前`
  } else if (diffHours < 24) {
    return `${diffHours} 小时前`
  } else if (diffDays < 7) {
    return `${diffDays} 天前`
  } else if (diffWeeks < 4) {
    return `${diffWeeks} 周前`
  } else if (diffMonths < 12) {
    return `${diffMonths} 个月前`
  } else {
    return date.toLocaleDateString('zh-CN')
  }
}

// 处理卡片点击
function handleCardClick(version) {
  emit('select', version)
}

// 处理下载
async function handleDownload(version) {
  if (version.downloading) return

  version.downloading = true
  try {
    emit('download', version)
  } finally {
    setTimeout(() => {
      version.downloading = false
    }, 500)
  }
}

// 处理对比
function handleCompare(version) {
  emit('compare', version)
}

// 处理下拉菜单命令
function handleCommand(command, version) {
  switch (command) {
    case 'preview':
      emit('preview', version)
      break
    case 'copy-link':
      emit('copy-link', version)
      break
    case 'restore':
      emit('restore', version)
      break
  }
}
</script>

<style scoped>
.version-timeline {
  padding: 8px 0;
}

.version-timeline :deep(.el-timeline-item__node) {
  background-color: #409eff;
}

.version-timeline :deep(.el-timeline-item__tail) {
  border-left-color: #e4e7ed;
}

.version-timeline :deep(.el-timeline-item__timestamp) {
  color: #909399;
  font-size: 13px;
}

/* 版本卡片 */
.version-card {
  border-radius: 10px;
  cursor: pointer;
  transition:
    transform 0.3s ease,
    box-shadow 0.3s ease,
    border-color 0.3s ease,
    background-color 0.3s ease,
    color 0.3s ease,
    opacity 0.3s ease;
  border: 1px solid transparent;
}

.version-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.version-card.is-latest {
  border-color: #409eff;
  background: linear-gradient(135deg, #fff 0%, #f5f7fa 100%);
}

.version-card.is-major {
  border-color: #e6a23c;
}

.version-card.is-selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.version-card :deep(.el-card__body) {
  padding: 16px;
}

/* 版本头部 */
.version-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.version-badges {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.version-tag {
  font-family: monospace;
  font-weight: 600;
  font-size: 13px;
}

.latest-tag {
  font-weight: 500;
}

.latest-tag .el-icon {
  margin-right: 2px;
}

.major-tag {
  font-weight: 500;
}

.major-tag .el-icon {
  margin-right: 2px;
}

.version-size {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #909399;
}

.version-size .el-icon {
  font-size: 14px;
}

/* 版本主体 */
.version-body {
  margin-bottom: 12px;
}

.changelog {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  margin-bottom: 12px;
}

.changelog .el-icon {
  margin-top: 2px;
  flex-shrink: 0;
  color: #409eff;
}

.changelog.empty {
  color: #c0c4cc;
  font-style: italic;
}

.changelog.empty .el-icon {
  color: #c0c4cc;
}

/* 变更统计 */
.changes-stats {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 4px;
}

.stat-item.added {
  background: #f0f9eb;
  color: #67c23a;
}

.stat-item.deleted {
  background: #fef0f0;
  color: #f56c6c;
}

.stat-item.modified {
  background: #fdf6ec;
  color: #e6a23c;
}

.stat-item .el-icon {
  font-size: 12px;
}

/* 版本底部 */
.version-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px dashed #e4e7ed;
}

.version-time {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
}

.version-time .el-icon {
  font-size: 13px;
}

.version-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.version-actions .el-button {
  padding: 6px;
}

/* 空状态 */
.empty-state {
  padding: 40px 0;
}

.custom-empty-icon {
  color: #dcdfe6;
  margin-bottom: 16px;
}

/* 动画 */
.slide-up-enter-active,
.slide-up-leave-active {
  transition:
    transform 0.4s ease,
    box-shadow 0.4s ease,
    border-color 0.4s ease,
    background-color 0.4s ease,
    color 0.4s ease,
    opacity 0.4s ease;
}

.slide-up-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.slide-up-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

/* 响应式 */
@media (max-width: 768px) {
  .version-card :deep(.el-card__body) {
    padding: 12px;
  }

  .version-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .version-badges {
    width: 100%;
  }

  .version-footer {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .version-actions {
    width: 100%;
    justify-content: flex-end;
  }
}

@media (max-width: 480px) {
  .version-timeline :deep(.el-timeline-item__timestamp) {
    font-size: 12px;
  }

  .changelog {
    font-size: 13px;
  }

  .changes-stats {
    gap: 8px;
  }

  .stat-item {
    font-size: 12px;
    padding: 3px 8px;
  }
}
</style>
