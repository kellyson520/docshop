<template>
  <section class="file-viewer file-viewer--pdf" data-testid="pdf-viewer">
    <strong>{{ fileName }}</strong>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  file: {
    type: Object,
    default: () => ({}),
  },
})

const fileName = computed(() => props.file?.display_name || props.file?.filename || '未命名文件')
</script>

<style scoped>
.file-viewer {
  padding: 16px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 14px;
  background: #fff;
}
</style>
