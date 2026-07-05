<template>
  <el-dialog
    :model-value="modelValue"
    title="公告预览"
    width="560px"
    append-to-body
    @close="emit('update:modelValue', false)"
  >
    <div class="preview-dialog">
      <h3 v-if="title" class="preview-title">{{ title }}</h3>
      <AnnouncementRenderer v-if="blocks?.length" :blocks="blocks" />
      <p v-else class="preview-fallback">{{ fallbackContent || '暂无预览内容' }}</p>
    </div>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import AnnouncementRenderer from './AnnouncementRenderer.vue'

defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    default: '',
  },
  blocks: {
    type: Array,
    default: () => [],
  },
  fallbackContent: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue'])
</script>

<style scoped>
.preview-dialog {
  display: grid;
  gap: 14px;
}

.preview-title {
  margin: 0;
  font-size: 18px;
  color: #172033;
}

.preview-fallback {
  margin: 0;
  color: #475569;
  line-height: 1.7;
  white-space: pre-wrap;
}
</style>
