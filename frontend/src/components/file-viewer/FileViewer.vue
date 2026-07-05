<template>
  <component :is="viewerComponent" v-bind="viewerProps" />
</template>

<script setup>
import { computed } from 'vue'
import ArchiveStructureViewer from './ArchiveStructureViewer.vue'
import FallbackFileCard from './FallbackFileCard.vue'
import HtmlViewer from './HtmlViewer.vue'
import ImageViewer from './ImageViewer.vue'
import OfficePreviewViewer from './OfficePreviewViewer.vue'
import PdfViewer from './PdfViewer.vue'
import VideoViewer from './VideoViewer.vue'

const props = defineProps({
  file: {
    type: Object,
    required: true,
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

const viewerComponent = computed(() => {
  switch (props.manifest?.type) {
    case 'video_native':
      return VideoViewer
    case 'image_native':
      return ImageViewer
    case 'pdf_native':
      return PdfViewer
    case 'html_runtime':
    case 'html_native':
      return HtmlViewer
    case 'office_pdf':
      return OfficePreviewViewer
    case 'archive_structure':
      return ArchiveStructureViewer
    default:
      return FallbackFileCard
  }
})

const viewerProps = computed(() => ({
  file: props.file,
  manifest: props.manifest || {},
  analysisSummary: props.analysisSummary || {},
}))
</script>
