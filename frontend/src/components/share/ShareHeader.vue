<template>
  <div class="share-header-component">
    <div class="header-content">
      <!-- 左侧：项目/文件信息 -->
      <div class="header-left">
        <div class="item-icon" :class="`type-${itemType}`">
          <el-icon :size="28">
            <component :is="iconComponent" />
          </el-icon>
        </div>
        <div class="item-info">
          <h2 class="item-name" :title="itemName">{{ itemName }}</h2>
          <div class="item-meta">
            <el-tag
              v-if="isPublic"
              type="success"
              size="small"
              effect="light"
              class="visibility-tag"
            >
              <el-icon><Unlock /></el-icon>
              公开分享
            </el-tag>
            <el-tag
              v-else
              type="warning"
              size="small"
              effect="light"
              class="visibility-tag"
            >
              <el-icon><Lock /></el-icon>
              私密分享
            </el-tag>
            <span v-if="expireInfo" class="expire-badge" :class="expireClass">
              <el-icon><Timer /></el-icon>
              {{ expireInfo }}
            </span>
          </div>
        </div>
      </div>

      <!-- 右侧：分享者信息和统计 -->
      <div class="header-right">
        <!-- 分享者信息 -->
        <div class="sharer-info" v-if="sharer">
          <el-avatar
            :size="36"
            :src="sharer.avatar"
            :icon="UserFilled"
            class="sharer-avatar"
          />
          <div class="sharer-details">
            <span class="sharer-name">{{ sharer.name || '未知用户' }}</span>
            <span class="sharer-label">分享者</span>
          </div>
        </div>

        <el-divider direction="vertical" class="header-divider" />

        <!-- 访问统计 -->
        <div class="stats-section">
          <div class="stat-item">
            <div class="stat-icon-wrapper views">
              <el-icon><View /></el-icon>
            </div>
            <div class="stat-details">
              <span class="stat-number">{{ formatNumber(visitCount) }}</span>
              <span class="stat-label">浏览</span>
            </div>
          </div>
          <div class="stat-item" v-if="downloadCount !== undefined">
            <div class="stat-icon-wrapper downloads">
              <el-icon><Download /></el-icon>
            </div>
            <div class="stat-details">
              <span class="stat-number">{{ formatNumber(downloadCount) }}</span>
              <span class="stat-label">下载</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：描述信息 -->
    <div v-if="description" class="header-description">
      <el-icon><InfoFilled /></el-icon>
      <span>{{ description }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  Document,
  Folder,
  Grid,
  UserFilled,
  Unlock,
  Lock,
  Timer,
  View,
  Download,
  InfoFilled
} from '@element-plus/icons-vue'

const props = defineProps({
  /**
   * 项目/文件名称
   */
  itemName: {
    type: String,
    required: true
  },
  /**
   * 项目/文件类型
   */
  itemType: {
    type: String,
    default: 'file'
  },
  /**
   * 是否公开分享
   */
  isPublic: {
    type: Boolean,
    default: true
  },
  /**
   * 分享者信息
   */
  sharer: {
    type: Object,
    default: () => ({
      name: '',
      avatar: ''
    })
  },
  /**
   * 访问次数
   */
  visitCount: {
    type: Number,
    default: 0
  },
  /**
   * 下载次数
   */
  downloadCount: {
    type: Number,
    default: undefined
  },
  /**
   * 有效期（ISO日期字符串）
   */
  expireAt: {
    type: String,
    default: ''
  },
  /**
   * 描述信息
   */
  description: {
    type: String,
    default: ''
  }
})

// 根据类型获取图标组件
const iconComponent = computed(() => {
  const iconMap = {
    file: Document,
    project: Folder,
    folder: Folder,
    xlsx: Grid,
    xls: Grid,
    default: Document
  }
  return iconMap[props.itemType] || iconMap.default
})

// 有效期信息
const expireInfo = computed(() => {
  if (!props.expireAt) return '永久有效'

  const expireDate = new Date(props.expireAt)
  const now = new Date()
  const diffMs = expireDate - now

  if (diffMs <= 0) return '已过期'

  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays <= 1) {
    const diffHours = Math.ceil(diffMs / (1000 * 60 * 60))
    return `剩余 ${diffHours} 小时`
  }

  if (diffDays <= 30) {
    return `剩余 ${diffDays} 天`
  }

  return `有效期至 ${expireDate.toLocaleDateString('zh-CN')}`
})

// 有效期样式类
const expireClass = computed(() => {
  if (!props.expireAt) return 'permanent'

  const expireDate = new Date(props.expireAt)
  const now = new Date()
  const diffMs = expireDate - now

  if (diffMs <= 0) return 'expired'

  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays <= 3) return 'urgent'
  if (diffDays <= 7) return 'warning'

  return 'normal'
})

// 格式化数字
function formatNumber(num) {
  if (num === undefined || num === null) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toString()
}
</script>

<style scoped>
.share-header-component {
  background: linear-gradient(135deg, #fff 0%, #f5f7fa 100%);
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  border: 1px solid #ebeef5;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}

/* 左侧信息 */
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  min-width: 0;
}

.item-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
  color: #909399;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.item-icon.type-file,
.item-icon.type-docx,
.item-icon.type-doc {
  background: linear-gradient(135deg, #ecf5ff 0%, #d9ecff 100%);
  color: #409eff;
}

.item-icon.type-project,
.item-icon.type-folder {
  background: linear-gradient(135deg, #fdf6ec 0%, #faecd8 100%);
  color: #e6a23c;
}

.item-icon.type-xlsx,
.item-icon.type-xls {
  background: linear-gradient(135deg, #f0f9eb 0%, #e1f3d8 100%);
  color: #67c23a;
}

.item-icon.type-pdf {
  background: linear-gradient(135deg, #fef0f0 0%, #fde2e2 100%);
  color: #f56c6c;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.visibility-tag {
  font-weight: 500;
}

.visibility-tag .el-icon {
  margin-right: 4px;
}

.expire-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 4px;
  background: #f4f4f5;
  color: #606266;
}

.expire-badge .el-icon {
  font-size: 12px;
}

.expire-badge.permanent {
  background: #f0f9eb;
  color: #67c23a;
}

.expire-badge.normal {
  background: #ecf5ff;
  color: #409eff;
}

.expire-badge.warning {
  background: #fdf6ec;
  color: #e6a23c;
}

.expire-badge.urgent {
  background: #fef0f0;
  color: #f56c6c;
}

.expire-badge.expired {
  background: #f4f4f5;
  color: #909399;
  text-decoration: line-through;
}

/* 右侧信息 */
.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-shrink: 0;
}

.sharer-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sharer-avatar {
  border: 2px solid #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.sharer-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sharer-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.sharer-label {
  font-size: 12px;
  color: #909399;
}

.header-divider {
  height: 40px;
  border-color: #e4e7ed;
}

/* 统计区域 */
.stats-section {
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stat-icon-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon-wrapper.views {
  background: #ecf5ff;
  color: #409eff;
}

.stat-icon-wrapper.downloads {
  background: #f0f9eb;
  color: #67c23a;
}

.stat-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-number {
  font-size: 18px;
  font-weight: 700;
  color: #303133;
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

/* 描述信息 */
.header-description {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #e4e7ed;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.header-description .el-icon {
  margin-top: 2px;
  color: #909399;
  flex-shrink: 0;
}

/* 响应式 */
@media (max-width: 992px) {
  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }

  .header-right {
    width: 100%;
    justify-content: space-between;
  }
}

@media (max-width: 768px) {
  .share-header-component {
    padding: 16px;
  }

  .item-icon {
    width: 48px;
    height: 48px;
  }

  .item-name {
    font-size: 18px;
  }

  .header-right {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .header-divider {
    display: none;
  }

  .stats-section {
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 480px) {
  .item-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .sharer-info {
    gap: 8px;
  }

  .sharer-details {
    display: none;
  }
}
</style>
