<template>
  <div class="breadcrumb-container">
    <el-breadcrumb :separator="separator">
      <el-breadcrumb-item
        v-for="(routeItem, index) in breadcrumbs"
        :key="routeItem.path || index"
        :to="routeItem.path && index < breadcrumbs.length - 1 ? routeItem.path : undefined"
      >
        <span :class="{ 'is-current': index === breadcrumbs.length - 1 }">
          {{ routeItem.name }}
        </span>
      </el-breadcrumb-item>
    </el-breadcrumb>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps({
  routes: {
    type: Array,
    default: () => [],
  },
  separator: {
    type: String,
    default: '/',
  },
})

const route = useRoute()

const nameMap = {
  admin: '首页',
  dashboard: '仪表盘',
  settings: '设置',
  projects: '项目管理',
  cards: '文档管理',
  exams: '考试安排',
  rank: '排行榜',
  download: '下载排行',
  visit: '访问排行',
}

const breadcrumbs = computed(() => {
  if (props.routes?.length) {
    return props.routes.map((item) => ({
      path: item.path,
      name: item.name || item.title || '',
    }))
  }

  return route.matched
    .filter((item) => item.meta?.title || item.name)
    .map((item) => ({
      path: item.path,
      name: item.meta?.title || nameMap[item.name] || item.name,
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
