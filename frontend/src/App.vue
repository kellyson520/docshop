<template>
  <ErrorBoundary>
    <router-view v-slot="{ Component, route }">
      <keep-alive :include="cachedViews">
        <component :is="Component" :key="getLayoutKey(route)" />
      </keep-alive>
    </router-view>
  </ErrorBoundary>
</template>

<script setup>
import ErrorBoundary from '@/components/common/ErrorBoundary.vue'

// Cache high-traffic views to keep list filters and scroll state.
const cachedViews = ['ProjectList', 'CardManage']

function getLayoutKey(route) {
  return route.matched[0]?.path || route.path
}
</script>
