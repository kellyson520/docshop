<!--
  页面头部通用组件
  用于页面顶部的标题、操作按钮区域
-->
<template>
  <div class="page-header">
    <!-- 面包屑导航 -->
    <Breadcrumb v-if="showBreadcrumb" :routes="breadcrumbs" />

    <!-- 主标题区域 -->
    <div class="header-content">
      <!-- 左侧：图标 + 标题 -->
      <div class="header-left">
        <div v-if="headerIcon" class="header-icon">
          <component :is="headerIcon" />
        </div>
        <div class="header-titles">
          <h1 class="header-title">{{ title }}</h1>
          <p v-if="subtitle" class="header-subtitle">{{ subtitle }}</p>
        </div>
      </div>

      <!-- 右侧：操作按钮 -->
      <div v-if="$slots.actions || hasActions" class="header-actions">
        <slot name="actions">
          <component
            :is="action.component"
            v-for="(action, index) in actions"
            :key="index"
            v-bind="action.props"
            @click="action.onClick"
          >
            {{ action.text }}
          </component>
        </slot>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, markRaw, toRaw } from 'vue'
import Breadcrumb from './Breadcrumb.vue'

const props = defineProps({
  /**
   * 页面标题
   */
  title: {
    type: String,
    required: true
  },
  /**
   * 副标题
   */
  subtitle: {
    type: String,
    default: ''
  },
  /**
   * 图标组件
   */
  icon: {
    type: [Object, Function],
    default: null
  },
  /**
   * 操作按钮配置
   * @type {Array<{component: string, text: string, props?: object, onClick?: Function}>}
   */
  actions: {
    type: Array,
    default: null
  },
  /**
   * 是否显示面包屑
   */
  showBreadcrumb: {
    type: Boolean,
    default: true
  },
  /**
   * 自定义面包屑路由
   * @type {Array<{path: string, name: string}>}
   */
  breadcrumbs: {
    type: Array,
    default: () => []
  }
})

const hasActions = computed(() => Array.isArray(props.actions) && props.actions.length > 0)
const headerIcon = computed(() => {
  if (!props.icon) return null
  return typeof props.icon === 'object' ? markRaw(toRaw(props.icon)) : props.icon
})
</script>

<style scoped>
.page-header {
  display: block;
  margin-bottom: clamp(14px, 2vw, 20px);
  padding-bottom: clamp(12px, 2vw, 18px);
  border-bottom: 1px solid var(--border-color-light, #e4e9f0);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, var(--workspace-blue, #2f5d8c), var(--workspace-accent, #0f766e));
  border-radius: 8px;
  color: #fff;
  font-size: 22px;
  box-shadow: 0 10px 22px rgba(47, 93, 140, 0.22);
}

.header-titles {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary, #172033);
  line-height: 1.3;
  letter-spacing: 0;
  overflow-wrap: anywhere;
}

.header-subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary, #475569);
  line-height: 1.4;
}

.header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  min-width: 0;
  flex-wrap: wrap;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .page-header {
    margin-bottom: 16px;
    padding-bottom: 12px;
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .header-left {
    width: 100%;
  }

  .header-icon {
    width: 40px;
    height: 40px;
    font-size: 20px;
  }

  .header-title {
    font-size: 20px;
  }

  .header-actions {
    width: 100%;
    justify-content: stretch;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
    gap: 8px;
  }

  .header-actions :deep(.el-button) {
    width: 100%;
    min-height: 40px;
  }
}
</style>
