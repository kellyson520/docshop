<template>
  <section class="html-viewer" data-testid="html-viewer">
    <iframe
      v-if="previewUrl"
      :src="previewUrl"
      class="html-viewer__frame"
      data-testid="html-viewer-frame"
      loading="lazy"
      sandbox="allow-scripts allow-forms allow-modals allow-downloads"
      referrerpolicy="no-referrer"
    />
    <div v-else class="html-viewer__empty">
      暂无可用的 HTML 预览地址
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  manifest: {
    type: Object,
    default: () => ({}),
  },
})

const previewUrl = computed(() => props.manifest?.primary_asset?.url || '')
</script>

<style scoped>
.html-viewer {
  min-height: 72vh;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 16px;
  overflow: hidden;
  background: #ffffff;
}

.html-viewer__frame {
  display: block;
  width: 100%;
  min-height: 72vh;
  border: none;
  background: #ffffff;
}

.html-viewer__empty {
  display: grid;
  place-items: center;
  min-height: 320px;
  color: #64748b;
  font-size: 14px;
}
</style>
