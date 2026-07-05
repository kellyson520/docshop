<template>
  <section class="archive-diff-view">
    <h3>结构差异</h3>
    <div class="archive-diff-tags">
      <span class="archive-tag archive-tag--add">新增 {{ summary.files_added ?? 0 }}</span>
      <span class="archive-tag archive-tag--del">删除 {{ summary.files_removed ?? 0 }}</span>
    </div>
    <ul class="archive-path-list">
      <li v-for="path in payload.added_paths || []" :key="`added-${path}`">+ {{ path }}</li>
      <li v-for="path in payload.removed_paths || []" :key="`removed-${path}`">- {{ path }}</li>
    </ul>
  </section>
</template>

<script setup>
defineProps({
  payload: {
    type: Object,
    default: () => ({}),
  },
  summary: {
    type: Object,
    default: () => ({}),
  },
})
</script>

<style scoped>
.archive-diff-view {
  display: grid;
  gap: 12px;
}

.archive-diff-view h3 {
  margin: 0;
  font-size: 18px;
  color: #1f2937;
}

.archive-diff-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.archive-tag {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.archive-tag--add {
  background: #dcfce7;
  color: #166534;
}

.archive-tag--del {
  background: #fee2e2;
  color: #991b1b;
}

.archive-path-list {
  margin: 0;
  padding-left: 18px;
  color: #334155;
  line-height: 1.7;
}
</style>
