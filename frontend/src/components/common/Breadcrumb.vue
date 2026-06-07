<!--
  面包屑导航组件
  用于页面顶部的路径导航
-->
<template>
  <div class="breadcrumb-container">
    <el-breadcrumb :separator="separator">
      <el-breadcrumb-item
        v-for="(route, index) in breadcrumbs"
        :key="route.path || index"
        :to="route.path && index < breadcrumbs.length - 1 ? route.path : undefined"
      >
        <span :class="{ 'is-current': index === breadcrumbs.length - 1 }">
          {{ route.name }}
        </span>
      </el-breadcrumb-item>
    </el-breadcrumb>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps({
  /**
   * 路由数组
   * @type {Array<{path: string, name: string}>}
   */
  routes: {
    type: Array,
    default: () => []
  },
  /**
   * 分隔符
   */
  separator: {
    type: String,
    default: '/'
  }
})

const route = useRoute()

/**
 * 计算面包屑数据
 * 优先使用传入的 routes，否则从当前路由生成
 */
const breadcrumbs = computed(() => {
  // 如果传入了自定义 routes，优先使用
  if (props.routes && props.routes.length > 0) {
    return props.routes
  }

  // 从当前路由生成面包屑
  const matched = route.matched.filter(item => item.meta?.title)

  // 如果有自定义名称映射，使用映射
  const nameMap = {
    'admin': '首页',
    'dashboard': '仪表盘',
    'settings': '设置',
    'projects': '项目管理',
    'cards': '文档管理',
    'exams': '考试安排',
    'rank': '排行榜',
    'download': '下载排行',
    'visit': '访问排行'
  }

  return matched.map(item => ({
    path: item.path,
    name: item.meta?.title || nameMap[item.name] || item.name
  }))
})
</script>

<style scoped>
.breadcrumb-container {
  padding: 12px 0;
}

.breadcrumb-container :deep(.el-breadcrumb) {
  font-size: 14px;
}

.breadcrumb-container :deep(.el-breadcrumb__item) {
  cursor: pointer;
}

.breadcrumb-container :deep(.el-breadcrumb__inner) {
  color: #909399;
  transition: color 0.2s;
}

.breadcrumb-container :deep(.el-breadcrumb__inner a:hover) {
  color: #409eff;
}

.breadcrumb-container :deep(.el-breadcrumb__separator) {
  color: #c0c4cc;
}

.is-current {
  color: #303133;
  font-weight: 500;
}
</style>
