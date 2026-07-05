<template>
  <ErrorBoundary>
    <router-view v-slot="{ Component, route }">
      <transition name="docshop-route" mode="out-in" appear>
        <keep-alive :include="cachedViews">
          <component :is="Component" :key="getLayoutKey(route)" />
        </keep-alive>
      </transition>
    </router-view>
  </ErrorBoundary>
</template>

<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import ErrorBoundary from '@/components/common/ErrorBoundary.vue'
import { bindMotionPreferenceSync, initMotionPreference } from '@/utils/motionPreference'

// Cache high-traffic views to keep list filters and scroll state.
const cachedViews = ['ProjectList', 'CardManage']
let stopMotionPreferenceSync = null

function getLayoutKey(route) {
  return route.matched[0]?.path || route.path
}

onMounted(() => {
  initMotionPreference()
  stopMotionPreferenceSync = bindMotionPreferenceSync()
})

onBeforeUnmount(() => {
  stopMotionPreferenceSync?.()
  stopMotionPreferenceSync = null
})
</script>
