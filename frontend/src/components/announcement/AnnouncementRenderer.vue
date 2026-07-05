<template>
  <div class="announcement-renderer">
    <template v-for="(block, index) in normalizedBlocks" :key="`${block.type}-${index}`">
      <p v-if="block.type === 'paragraph'" class="announcement-paragraph">{{ block.text }}</p>
      <pre v-else-if="block.type === 'code'" class="announcement-code"><code>{{ block.content }}</code></pre>
      <a
        v-else-if="block.type === 'button'"
        class="announcement-button"
        :href="block.url || '#'"
      >
        {{ block.label || '查看详情' }}
      </a>
      <img
        v-else-if="block.type === 'image'"
        class="announcement-image"
        :src="resolveAsset(block.file_id)"
        :alt="block.caption || 'announcement image'"
      >
      <video
        v-else-if="block.type === 'video'"
        class="announcement-video"
        controls
        :src="resolveAsset(block.file_id)"
      ></video>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { buildAnnouncementAttachmentUrl } from '@/utils/resourceUrl'

const props = defineProps({
  blocks: {
    type: Array,
    default: () => [],
  },
})

const normalizedBlocks = computed(() => (
  Array.isArray(props.blocks) ? props.blocks.filter((block) => block && block.type) : []
))

function resolveAsset(fileId) {
  return buildAnnouncementAttachmentUrl(fileId)
}
</script>

<style scoped>
.announcement-renderer {
  display: grid;
  gap: 12px;
}

.announcement-paragraph,
.announcement-code {
  margin: 0;
  color: #334155;
  line-height: 1.7;
}

.announcement-code {
  padding: 12px;
  overflow: auto;
  border-radius: 12px;
  background: #0f172a;
  color: #e2e8f0;
  font-size: 13px;
}

.announcement-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-height: 40px;
  padding: 0 16px;
  border-radius: 999px;
  background: #2563eb;
  color: #fff;
  font-weight: 600;
  text-decoration: none;
}

.announcement-image,
.announcement-video {
  max-width: 100%;
  border-radius: 12px;
}
</style>
