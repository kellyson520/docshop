<template>
  <section class="file-viewer file-viewer--office" data-testid="office-preview-viewer">
    <header class="file-viewer__header">
      <strong>{{ fileName }}</strong>
      <span class="file-viewer__meta">office</span>
    </header>
    <p v-if="pageCountText" class="file-viewer__summary">{{ pageCountText }}</p>
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
  analysisSummary: {
    type: Object,
    default: () => ({}),
  },
})

const fileName = computed(() => props.file?.display_name || props.file?.filename || '未命名文件')

const pageCountText = computed(() => {
  const pageCount = props.analysisSummary?.page_count ?? props.manifest?.summary?.page_count
  return pageCount == null ? '' : `共 ${pageCount} 页`
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
