<template>
  <section class="file-viewer file-viewer--fallback" data-testid="fallback-file-card">
    <header class="file-viewer__header">
      <strong>{{ fileName }}</strong>
      <span class="file-viewer__meta">{{ manifest?.type || 'fallback' }}</span>
    </header>
    <p v-if="statusText" class="file-viewer__summary">{{ statusText }}</p>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  file: {
    type: Object,
    default: () => ({}),
  },
  manifest: {
    type: Object,
    default: () => ({}),
  },
})

const fileName = computed(() => props.file?.display_name || props.file?.filename || '未命名文件')

const statusText = computed(() => {
  const status = props.manifest?.status
  return status ? `预览状态：${status}` : ''
})
</script>

<style scoped>
.file-viewer {
  display: grid;
  gap: 8px;
  padding: 16px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 14px;
  background: #fff;
}

.file-viewer__header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.file-viewer__meta {
  color: #64748b;
  font-size: 12px;
  text-transform: uppercase;
}

.file-viewer__summary {
  margin: 0;
  color: #475569;
  font-size: 13px;
}
</style>
