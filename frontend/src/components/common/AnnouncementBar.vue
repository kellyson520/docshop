<template>
  <div v-if="scrollItems.length" class="announce-scroll">
    <div ref="scrollViewportRef" class="scroll-viewport">
      <div
        ref="scrollTrackRef"
        class="scroll-track"
        :class="{ 'is-static': !shouldAnimateScroll }"
        :style="scrollTrackStyle"
      >
        <div
          v-for="groupIndex in renderGroupCount"
          :key="groupIndex"
          :ref="groupIndex === 1 ? setScrollGroupRef : undefined"
          class="scroll-group"
        >
          <span
            v-for="(a, i) in scrollItems"
            :key="`${groupIndex}-${a.id || i}`"
            class="scroll-item"
          >
            <span class="scroll-icon" aria-hidden="true"></span>
            <span class="scroll-prefix">公告</span>
            <span class="scroll-text">{{ a.title }}: {{ announcementPreviewText(a) }}</span>
            <span v-if="i < scrollItems.length - 1" class="scroll-sep">|</span>
          </span>
        </div>
      </div>
    </div>
  </div>

  <el-dialog v-model="popupVisible" :title="popupItem?.title" width="420px" :close-on-click-modal="false">
    <AnnouncementRenderer
      v-if="Array.isArray(popupItem?.content_blocks) && popupItem.content_blocks.length"
      :blocks="popupItem.content_blocks"
    />
    <p v-else style="white-space: pre-wrap">{{ popupItem?.content }}</p>
    <template #footer><el-button type="primary" @click="popupVisible = false">我知道了</el-button></template>
  </el-dialog>

  <div v-if="sidebarVisible" class="announce-toast">
    <div class="toast-header">
      <strong>{{ sidebarItems[0]?.title }}</strong>
      <el-button text :icon="Close" size="small" @click="sidebarVisible = false" />
    </div>
    <AnnouncementRenderer
      v-if="Array.isArray(sidebarItems[0]?.content_blocks) && sidebarItems[0].content_blocks.length"
      :blocks="sidebarItems[0].content_blocks"
    />
    <p v-else class="toast-body">{{ sidebarItems[0]?.content }}</p>
  </div>

  <div v-if="bottomItems.length" class="announce-bottom">
    <span v-for="(a, i) in bottomItems" :key="a.id" class="bottom-item">
      {{ a.title }}: {{ announcementPreviewText(a) }}
      <span v-if="i < bottomItems.length - 1" class="bottom-sep">|</span>
    </span>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Close } from '@element-plus/icons-vue'
import AnnouncementRenderer from '@/components/announcement/AnnouncementRenderer.vue'
import { listActiveAnnouncements } from '@/api/announcement'
import { useEventChannel } from '@/composables/useEventChannel'

const all = ref([])
const popupVisible = ref(false)
const popupItem = ref(null)
const sidebarVisible = ref(false)
const scrollViewportRef = ref(null)
const scrollTrackRef = ref(null)
const scrollGroupRef = ref(null)
const shouldAnimateScroll = ref(false)
const scrollDuration = ref(24)
let resizeObserver = null

const scrollItems = computed(() => all.value.filter((a) => a.display_mode === 'scroll'))
const sidebarItems = computed(() => all.value.filter((a) => a.display_mode === 'sidebar'))
const bottomItems = computed(() => all.value.filter((a) => a.display_mode === 'bottom'))
const renderGroupCount = computed(() => (scrollItems.value.length ? 2 : 0))
const scrollTrackStyle = computed(() => shouldAnimateScroll.value
  ? { '--scroll-duration': `${scrollDuration.value}s` }
  : {})

function setScrollGroupRef(el) {
  scrollGroupRef.value = el || null
}

function announcementPreviewText(item = {}) {
  if (Array.isArray(item.content_blocks) && item.content_blocks.length) {
    const firstText = item.content_blocks
      .map((block) => block?.text || block?.content || block?.label || '')
      .find(Boolean)
    if (firstText) return firstText
  }
  return item.content || ''
}

async function fetchAnnouncements() {
  try {
    all.value = await listActiveAnnouncements()
  } catch {
    all.value = []
  }

  const popup = all.value.find((a) => a.display_mode === 'popup')
  const sidebar = all.value.find((a) => a.display_mode === 'sidebar')

  sidebarVisible.value = !!sidebar

  if (popup) {
    const dismissed = sessionStorage.getItem(`ann_popup_${popup.id}`)
    if (!dismissed) {
      popupItem.value = popup
      popupVisible.value = true
      sessionStorage.setItem(`ann_popup_${popup.id}`, '1')
    }
  }

  await updateScrollMetrics()
}

async function updateScrollMetrics() {
  await nextTick()

  const viewportWidth = scrollViewportRef.value?.clientWidth || 0
  const contentWidth = scrollGroupRef.value?.scrollWidth || 0

  if (!viewportWidth || !contentWidth) {
    shouldAnimateScroll.value = scrollItems.value.length > 0
    scrollDuration.value = 24
    return
  }

  shouldAnimateScroll.value = scrollItems.value.length > 0
  const travelWidth = Math.max(contentWidth, viewportWidth)
  scrollDuration.value = Math.max(18, Math.round(travelWidth / 70))
}

watch(scrollItems, () => {
  updateScrollMetrics()
}, { deep: true })

useEventChannel({
  topics: ['announcements'],
  onEvent: (event) => {
    if (event?.data?.topic === 'announcements' && String(event?.data?.type || '').startsWith('announcement.')) {
      void fetchAnnouncements()
    }
  },
})

onMounted(async () => {
  await fetchAnnouncements()

  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      updateScrollMetrics()
    })
    if (scrollViewportRef.value) resizeObserver.observe(scrollViewportRef.value)
    if (scrollGroupRef.value) resizeObserver.observe(scrollGroupRef.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect?.()
})
</script>

<style scoped>
.announce-scroll {
  background: linear-gradient(90deg, #fff7ed, #fef3c7);
  border-bottom: 1px solid #fde68a;
  overflow: hidden;
  padding: 8px 0;
}

.scroll-viewport {
  overflow: hidden;
  white-space: nowrap;
}

.scroll-track {
  display: inline-flex;
  min-width: max-content;
  align-items: center;
  will-change: transform;
  animation: announce-marquee var(--scroll-duration, 24s) linear infinite;
}

.scroll-track.is-static {
  animation: none;
  transform: translateX(0);
}

.scroll-group {
  display: inline-flex;
  align-items: center;
  min-width: 100vw;
  padding-left: 100vw;
  flex-shrink: 0;
}

.scroll-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #92400e;
  margin-right: 40px;
}

.scroll-icon {
  width: 7px;
  height: 7px;
  flex: 0 0 7px;
  border-radius: 999px;
  background: #d97706;
  box-shadow: 0 0 0 3px rgba(217, 119, 6, 0.14);
}

.scroll-prefix {
  color: #7c2d12;
  font-weight: 700;
}

.scroll-sep {
  color: #d97706;
  margin-left: 20px;
}

@keyframes announce-marquee {
  from { transform: translate3d(0, 0, 0); }
  to { transform: translate3d(-50%, 0, 0); }
}

.announce-toast {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 1000;
  width: 320px;
  padding: 16px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, .12);
  animation: toast-in .3s ease;
}

.toast-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.toast-header strong {
  font-size: 14px;
  color: #1f2937;
}

.toast-body {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: #6b7280;
}

@keyframes toast-in {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.announce-bottom {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 500;
  padding: 10px 20px;
  font-size: 14px;
  text-align: center;
  color: #e2e8f0;
  background: #1e293b;
}

.bottom-sep {
  margin: 0 16px;
  color: #475569;
}

@media (prefers-reduced-motion: reduce) {
  .scroll-track,
  .announce-toast {
    animation: none !important;
    transform: none !important;
  }
}
</style>
