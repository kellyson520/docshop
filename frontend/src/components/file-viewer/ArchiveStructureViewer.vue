<template>
  <section class="file-viewer file-viewer--archive" data-testid="archive-structure-viewer">
    <header class="file-viewer__header">
      <strong>{{ fileName }}</strong>
      <span class="file-viewer__meta">archive</span>
    </header>
    <p v-if="entryCountText" class="file-viewer__summary">{{ entryCountText }}</p>
    <ul v-if="rootNodes.length" class="file-viewer__list">
      <li v-for="node in rootNodes" :key="node">{{ node }}</li>
    </ul>
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

const entryCountText = computed(() => {
  const entryCount = props.analysisSummary?.entry_count ?? props.manifest?.summary?.entry_count
  return entryCount == null ? '' : `共 ${entryCount} 个条目`
})

const rootNodes = computed(() => props.analysisSummary?.root_nodes || props.manifest?.summary?.root_nodes || [])
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

.file-viewer__list {
  margin: 0;
  padding-left: 18px;
  color: #334155;
}
</style>
