<!--
  空状态组件
  用于在列表为空、搜索结果为空或加载失败时显示友好的提示信息
-->
<template>
  <div class="empty-state" :class="{ 'empty-state--compact': compact }">
    <!-- 图标区域 -->
    <div class="empty-state__icon">
      <el-icon :size="iconSize" :color="iconColor">
        <component :is="iconComponent" />
      </el-icon>
    </div>
    
    <!-- 标题 -->
    <h3 v-if="title" class="empty-state__title">
      {{ title }}
    </h3>
    
    <!-- 描述 -->
    <p v-if="description" class="empty-state__description">
      {{ description }}
    </p>
    
    <!-- 操作按钮区域 -->
    <div v-if="showAction" class="empty-state__action">
      <slot name="action">
        <el-button 
          :type="actionType" 
          :size="actionSize"
          @click="handleAction"
        >
          {{ actionText }}
        </el-button>
      </slot>
    </div>
  </div>
</template>

<script setup>
import { computed, useSlots } from 'vue'
import {
  FolderOpened,
  Search,
  WarningFilled,
  Document,
  DataLine,
  Box,
  Picture,
  Files,
  Connection,
  Calendar
} from '@element-plus/icons-vue'

/**
 * 图标映射表
 * 支持字符串名称或组件
 */
const iconMap = {
  FolderOpened,
  Search,
  WarningFilled,
  Document,
  DataLine,
  Box,
  Picture,
  Files,
  Connection,
  Calendar
}

const props = defineProps({
  /**
   * 图标名称或组件
   * 可选值：FolderOpened, Search, WarningFilled, Document, DataLine, Box, Picture, Files, Connection
   */
  icon: {
    type: [String, Object],
    default: 'FolderOpened'
  },
  /**
   * 图标大小
   */
  iconSize: {
    type: Number,
    default: 64
  },
  /**
   * 图标颜色
   */
  iconColor: {
    type: String,
    default: '#C0C4CC'
  },
  /**
   * 标题
   */
  title: {
    type: String,
    default: ''
  },
  /**
   * 描述文本
   */
  description: {
    type: String,
    default: ''
  },
  /**
   * 操作按钮文本
   */
  actionText: {
    type: String,
    default: ''
  },
  /**
   * 操作按钮类型
   */
  actionType: {
    type: String,
    default: 'primary'
  },
  /**
   * 操作按钮尺寸
   */
  actionSize: {
    type: String,
    default: 'default'
  },
  /**
   * 是否使用紧凑模式
   */
  compact: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['action'])
const slots = useSlots()

/**
 * 计算图标组件
 */
const iconComponent = computed(() => {
  if (typeof props.icon === 'string') {
    return iconMap[props.icon] || FolderOpened
  }
  return props.icon
})

/**
 * 是否显示操作按钮
 */
const showAction = computed(() => {
  return !!props.actionText || !!slots.action
})

/**
 * 处理操作按钮点击
 */
function handleAction() {
  emit('action')
}
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.empty-state--compact {
  padding: 24px;
}

.empty-state__icon {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state__title {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  line-height: 1.4;
}

.empty-state__description {
  margin: 0 0 24px;
  font-size: 14px;
  color: #909399;
  line-height: 1.6;
  max-width: 400px;
}

.empty-state--compact .empty-state__description {
  margin-bottom: 16px;
}

.empty-state__action {
  display: flex;
  gap: 12px;
}
</style>
