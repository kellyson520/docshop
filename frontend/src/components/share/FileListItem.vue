<template>
  <div class="file-list-item" :class="{ 'is-latest': isLatest, 'is-selected': selected }" @click="handleClick">
    <!-- 文件图标 -->
    <div class="file-icon-wrapper" :class="`file-type-${fileType}`">
      <el-icon :size="24">
        <component :is="fileIcon" />
      </el-icon>
    </div>

    <!-- 文件信息 -->
    <div class="file-content">
      <div class="file-header-row">
        <h4 class="file-name" :title="fileName">{{ fileName }}</h4>
        <div class="file-badges">
          <el-tag v-if="isLatest" type="success" size="small" effect="light" class="status-tag">
            <el-icon><Check /></el-icon>
            最新
          </el-tag>
          <el-tag v-else type="info" size="small" effect="plain" class="status-tag">
            历史
          </el-tag>
          <el-tag
            v-if="isMajor"
            type="warning"
            size="small"
            effect="light"
            class="major-tag"
          >
            <el-icon><Star /></el-icon>
            重要
          </el-tag>
        </div>
      </div>

      <div class="file-meta-row">
        <span class="meta-item file-type">
          <el-tag :type="fileTypeTagType" size="small" effect="light">
            {{ fileType?.toUpperCase() }}
          </el-tag>
        </span>
        <span class="meta-item version">
          <el-icon><CollectionTag /></el-icon>
          v{{ versionCount }} 个版本
        </span>
        <span class="meta-item size">
          <el-icon><Document /></el-icon>
          {{ formatFileSize(fileSize) }}
        </span>
        <span class="meta-item time">
          <el-icon><Clock /></el-icon>
          {{ formatTime(updatedAt) }}
        </span>
      </div>

      <div v-if="changelog" class="file-changelog" :title="changelog">
        <el-icon><EditPen /></el-icon>
        <span>{{ changelog }}</span>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="file-actions" @click.stop>
      <el-tooltip content="查看版本" placement="top">
        <el-button
          circle
          type="primary"
          plain
          size="small"
          @click="$emit('view-versions', fileId)"
        >
          <el-icon><View /></el-icon>
        </el-button>
      </el-tooltip>

      <el-tooltip content="查看变更" placement="top">
        <el-button
          circle
          type="warning"
          plain
          size="small"
          @click="$emit('view-diff', fileId)"
        >
          <el-icon><Sort /></el-icon>
        </el-button>
      </el-tooltip>

      <el-tooltip content="下载" placement="top">
        <el-button
          circle
          type="success"
          plain
          size="small"
          :loading="downloading"
          @click="handleDownload"
        >
          <el-icon><Download /></el-icon>
        </el-button>
      </el-tooltip>

      <el-dropdown v-if="showMore" trigger="click" @command="handleCommand">
        <el-button circle plain size="small">
          <el-icon><MoreFilled /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="copy-link">
              <el-icon><Link /></el-icon>
              复制链接
            </el-dropdown-item>
            <el-dropdown-item command="share">
              <el-icon><Share /></el-icon>
              分享
            </el-dropdown-item>
            <el-dropdown-item v-if="canDelete" command="delete" divided>
              <el-icon><Delete /></el-icon>
              <span style="color: #f56c6c;">删除</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Document,
  Grid,
  Check,
  Star,
  CollectionTag,
  Clock,
  EditPen,
  View,
  Sort,
  Download,
  MoreFilled,
  Link,
  Share,
  Delete
} from '@element-plus/icons-vue'
import { formatFileSize } from '@/utils'

const props = defineProps({
  /**
   * 文件ID
   */
  fileId: {
    type: [String, Number],
    required: true
  },
  /**
   * 文件名
   */
  fileName: {
    type: String,
    required: true
  },
  /**
   * 文件类型
   */
  fileType: {
    type: String,
    default: 'file'
  },
  /**
   * 文件大小（字节）
   */
  fileSize: {
    type: Number,
    default: 0
  },
  /**
   * 版本数量
   */
  versionCount: {
    type: Number,
    default: 1
  },
  /**
   * 是否是最新版本
   */
  isLatest: {
    type: Boolean,
    default: true
  },
  /**
   * 是否重要版本
   */
  isMajor: {
    type: Boolean,
    default: false
  },
  /**
   * 更新时间
   */
  updatedAt: {
    type: String,
    default: ''
  },
  /**
   * 变更说明
   */
  changelog: {
    type: String,
    default: ''
  },
  /**
   * 是否选中
   */
  selected: {
    type: Boolean,
    default: false
  },
  /**
   * 是否显示更多操作
   */
  showMore: {
    type: Boolean,
    default: true
  },
  /**
   * 是否可以删除
   */
  canDelete: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'click',
  'view-versions',
  'view-diff',
  'download',
  'copy-link',
  'share',
  'delete'
])

const downloading = ref(false)

// 根据文件类型获取图标
const fileIcon = computed(() => {
  const iconMap = {
    xlsx: Grid,
    xls: Grid,
    csv: Grid,
    default: Document
  }
  return iconMap[props.fileType] || iconMap.default
})

// 文件类型标签样式
const fileTypeTagType = computed(() => {
  const typeMap = {
    pdf: 'danger',
    docx: 'primary',
    doc: 'primary',
    xlsx: 'success',
    xls: 'success',
    pptx: 'warning',
    ppt: 'warning',
    txt: 'info'
  }
  return typeMap[props.fileType] || 'info'
})

// 格式化时间（相对时间）
function formatTime(timeStr) {
  if (!timeStr) return '-'

  const date = new Date(timeStr)
  const now = new Date()
  const diffMs = now - date
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSecs < 60) {
    return '刚刚'
  } else if (diffMins < 60) {
    return `${diffMins} 分钟前`
  } else if (diffHours < 24) {
    return `${diffHours} 小时前`
  } else if (diffDays < 7) {
    return `${diffDays} 天前`
  } else if (diffDays < 30) {
    return `${Math.floor(diffDays / 7)} 周前`
  } else {
    return date.toLocaleDateString('zh-CN')
  }
}

// 处理点击
function handleClick() {
  emit('click', props.fileId)
}

// 处理下载
async function handleDownload() {
  if (downloading.value) return

  downloading.value = true
  try {
    emit('download', props.fileId)
  } finally {
    // 延迟重置，给用户视觉反馈
    setTimeout(() => {
      downloading.value = false
    }, 500)
  }
}

// 处理下拉菜单命令
function handleCommand(command) {
  switch (command) {
    case 'copy-link':
      emit('copy-link', props.fileId)
      break
    case 'share':
      emit('share', props.fileId)
      break
    case 'delete':
      emit('delete', props.fileId)
      break
  }
}
</script>

<style scoped>
.file-list-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #fff;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  transition:
    transform 0.3s ease,
    box-shadow 0.3s ease,
    border-color 0.3s ease,
    background-color 0.3s ease,
    color 0.3s ease,
    opacity 0.3s ease;
  cursor: pointer;
}

.file-list-item:hover {
  border-color: #409eff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.1);
  transform: translateY(-1px);
}

.file-list-item.is-latest {
  background: linear-gradient(135deg, #fff 0%, #f5f7fa 100%);
}

.file-list-item.is-selected {
  border-color: #409eff;
  background: #ecf5ff;
}

/* 文件图标 */
.file-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: #f5f7fa;
  color: #909399;
  transition:
    transform 0.3s ease,
    box-shadow 0.3s ease,
    border-color 0.3s ease,
    background-color 0.3s ease,
    color 0.3s ease,
    opacity 0.3s ease;
}

.file-list-item:hover .file-icon-wrapper {
  transform: scale(1.05);
}

.file-icon-wrapper.file-type-pdf {
  background: #fef0f0;
  color: #f56c6c;
}

.file-icon-wrapper.file-type-docx,
.file-icon-wrapper.file-type-doc {
  background: #ecf5ff;
  color: #409eff;
}

.file-icon-wrapper.file-type-xlsx,
.file-icon-wrapper.file-type-xls {
  background: #f0f9eb;
  color: #67c23a;
}

.file-icon-wrapper.file-type-pptx,
.file-icon-wrapper.file-type-ppt {
  background: #fdf6ec;
  color: #e6a23c;
}

.file-icon-wrapper.file-type-txt {
  background: #f4f4f5;
  color: #909399;
}

/* 文件内容 */
.file-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-header-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-name {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.file-badges {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.status-tag {
  font-weight: 500;
}

.status-tag .el-icon {
  margin-right: 2px;
}

.major-tag {
  font-weight: 500;
}

.major-tag .el-icon {
  margin-right: 2px;
}

/* 元信息行 */
.file-meta-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #606266;
}

.meta-item .el-icon {
  font-size: 14px;
  color: #909399;
}

.meta-item.file-type .el-tag {
  font-weight: 500;
}

/* 变更说明 */
.file-changelog {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
  overflow: hidden;
}

.file-changelog .el-icon {
  font-size: 14px;
  color: #409eff;
  flex-shrink: 0;
}

.file-changelog span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 操作按钮 */
.file-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.file-list-item:hover .file-actions {
  opacity: 1;
}

.file-actions .el-button {
  padding: 6px;
}

/* 响应式 */
@media (max-width: 768px) {
  .file-list-item {
    padding: 12px;
    gap: 12px;
  }

  .file-icon-wrapper {
    width: 40px;
    height: 40px;
  }

  .file-name {
    font-size: 14px;
  }

  .file-meta-row {
    gap: 12px;
  }

  .meta-item {
    font-size: 12px;
  }

  .file-actions {
    opacity: 1;
    flex-direction: column;
    gap: 4px;
  }

  .file-actions .el-button {
    padding: 4px;
  }
}

@media (max-width: 480px) {
  .file-list-item {
    flex-wrap: wrap;
  }

  .file-content {
    width: calc(100% - 60px);
  }

  .file-actions {
    width: 100%;
    justify-content: flex-end;
    flex-direction: row;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #ebeef5;
  }

  .file-badges {
    display: none;
  }
}
</style>
