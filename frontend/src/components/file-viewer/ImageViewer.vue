<template>
  <section class="image-viewer" data-testid="image-viewer">
    <div class="image-viewer__preview-card">
      <img
        v-if="previewUrl"
        :src="previewUrl"
        :alt="fileName"
        class="image-viewer__preview"
        data-testid="image-viewer-preview"
      />
      <div v-else class="image-viewer__placeholder">
        <span>{{ formatText || 'IMAGE' }}</span>
      </div>
      <div class="image-viewer__overlay">
        <span class="image-viewer__badge">{{ formatText || 'IMAGE' }}</span>
        <span v-if="dimensionsText" class="image-viewer__badge image-viewer__badge--subtle">
          {{ dimensionsText }}
        </span>
      </div>
    </div>

    <div class="image-viewer__panel">
      <header class="image-viewer__header">
        <div>
          <p class="image-viewer__eyebrow">Image Preview</p>
          <h3 class="image-viewer__title">{{ fileName }}</h3>
        </div>
        <div class="image-viewer__chips">
          <span
            v-if="dimensionsText"
            class="image-viewer__chip"
            data-testid="image-viewer-dimensions"
          >
            {{ dimensionsText }}
          </span>
          <span
            v-if="formatText"
            class="image-viewer__chip image-viewer__chip--strong"
            data-testid="image-viewer-format"
          >
            {{ formatText }}
          </span>
        </div>
      </header>

      <dl class="image-viewer__meta-list">
        <div class="image-viewer__meta-row">
          <dt>Color Mode</dt>
          <dd data-testid="image-viewer-mode">{{ colorModeText }}</dd>
        </div>
        <div class="image-viewer__meta-row">
          <dt>Alpha</dt>
          <dd data-testid="image-viewer-alpha">{{ alphaText }}</dd>
        </div>
        <div class="image-viewer__meta-row">
          <dt>Aspect Ratio</dt>
          <dd data-testid="image-viewer-ratio">{{ aspectRatioText }}</dd>
        </div>
        <div class="image-viewer__meta-row">
          <dt>Orientation</dt>
          <dd data-testid="image-viewer-orientation">{{ orientationText }}</dd>
        </div>
      </dl>
    </div>
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

const fileName = computed(() => props.file?.display_name || props.file?.filename || 'Unnamed file')

const summary = computed(() => {
  const analysisSummary = props.analysisSummary || {}
  return Object.keys(analysisSummary).length ? analysisSummary : props.manifest?.summary || {}
})

const previewUrl = computed(() => props.manifest?.primary_asset?.url || '')

const width = computed(() => summary.value?.dimensions?.width ?? null)
const height = computed(() => summary.value?.dimensions?.height ?? null)

const dimensionsText = computed(() => {
  if (width.value == null || height.value == null) {
    return ''
  }
  return `${width.value} × ${height.value}`
})

const formatText = computed(() => summary.value?.format || '')
const colorModeText = computed(() => summary.value?.color_mode || '—')

const alphaText = computed(() => {
  const value = summary.value?.has_alpha
  if (typeof value !== 'boolean') {
    return '—'
  }
  return value ? 'Yes' : 'No'
})

const aspectRatioText = computed(() => summary.value?.aspect_ratio || '—')
const orientationText = computed(() => {
  const value = summary.value?.orientation
  return value == null ? '—' : String(value)
})
</script>

<style scoped>
.image-viewer {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.9fr);
  gap: 20px;
  padding: 20px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 22px;
  background:
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.12), transparent 38%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.96));
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.08);
}

.image-viewer__preview-card {
  position: relative;
  min-height: 260px;
  overflow: hidden;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background:
    linear-gradient(135deg, rgba(15, 23, 42, 0.06), rgba(148, 163, 184, 0.18)),
    #e2e8f0;
}

.image-viewer__preview {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 260px;
  object-fit: contain;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.92), rgba(226, 232, 240, 0.92));
}

.image-viewer__placeholder {
  display: grid;
  place-items: center;
  min-height: 260px;
  color: #0f172a;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.image-viewer__overlay {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.image-viewer__badge,
.image-viewer__chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.image-viewer__badge {
  color: #e2e8f0;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(10px);
}

.image-viewer__badge--subtle {
  color: #f8fafc;
  background: rgba(30, 41, 59, 0.52);
}

.image-viewer__panel {
  display: grid;
  gap: 18px;
  align-content: start;
}

.image-viewer__header {
  display: grid;
  gap: 14px;
}

.image-viewer__eyebrow {
  margin: 0 0 6px;
  color: #0369a1;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.image-viewer__title {
  margin: 0;
  color: #0f172a;
  font-size: 22px;
  line-height: 1.2;
}

.image-viewer__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.image-viewer__chip {
  color: #334155;
  background: rgba(226, 232, 240, 0.9);
}

.image-viewer__chip--strong {
  color: #075985;
  background: rgba(186, 230, 253, 0.9);
}

.image-viewer__meta-list {
  display: grid;
  gap: 10px;
  margin: 0;
}

.image-viewer__meta-row {
  display: grid;
  grid-template-columns: minmax(0, 120px) minmax(0, 1fr);
  gap: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(226, 232, 240, 0.88);
}

.image-viewer__meta-row dt {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.image-viewer__meta-row dd {
  margin: 0;
  color: #0f172a;
  font-size: 14px;
  font-weight: 600;
  text-align: right;
}

@media (max-width: 900px) {
  .image-viewer {
    grid-template-columns: 1fr;
  }

  .image-viewer__preview,
  .image-viewer__preview-card,
  .image-viewer__placeholder {
    min-height: 220px;
  }
}

@media (max-width: 640px) {
  .image-viewer {
    padding: 16px;
    gap: 16px;
    border-radius: 18px;
  }

  .image-viewer__title {
    font-size: 18px;
  }

  .image-viewer__meta-row {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .image-viewer__meta-row dd {
    text-align: left;
  }
}
</style>
