<template>
  <section class="media-diff-view">
    <h3>媒体差异</h3>
    <div class="media-diff-grid">
      <video v-if="payload.left?.preview_url" controls :src="payload.left.preview_url"></video>
      <video v-if="payload.right?.preview_url" controls :src="payload.right.preview_url"></video>
    </div>
    <div class="media-diff-stats">
      <span>时长变化 {{ summary.duration_delta_seconds ?? 0 }}</span>
      <span>大小变化 {{ summary.size_delta_bytes ?? 0 }}</span>
    </div>
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
.media-diff-view {
  display: grid;
  gap: 12px;
}

.media-diff-view h3 {
  margin: 0;
  font-size: 18px;
  color: #1f2937;
}

.media-diff-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.media-diff-grid video {
  width: 100%;
  border-radius: 12px;
  background: #000;
}

.media-diff-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: #64748b;
  font-size: 13px;
}

@media (max-width: 768px) {
  .media-diff-grid {
    grid-template-columns: 1fr;
  }
}
</style>
