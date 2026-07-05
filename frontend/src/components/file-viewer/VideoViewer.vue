<template>
  <section class="video-viewer" data-testid="video-viewer">
    <div class="video-viewer__stage">
      <video
        v-if="videoUrl"
        :src="videoUrl"
        :poster="posterUrl || undefined"
        class="video-viewer__player"
        controls
        playsinline
        preload="metadata"
        data-testid="video-player"
      />
      <div v-else class="video-viewer__placeholder">
        <span>VIDEO</span>
      </div>
    </div>

    <div class="video-viewer__panel">
      <header class="video-viewer__header">
        <div>
          <p class="video-viewer__eyebrow">Video Preview</p>
          <h3 class="video-viewer__title">{{ fileName }}</h3>
        </div>
        <div class="video-viewer__chips">
          <span
            v-if="resolutionText"
            class="video-viewer__chip"
            data-testid="video-viewer-resolution"
          >
            {{ resolutionText }}
          </span>
          <span
            v-if="codecText"
            class="video-viewer__chip video-viewer__chip--strong"
            data-testid="video-viewer-codec"
          >
            {{ codecText }}
          </span>
        </div>
      </header>

      <p v-if="durationText" class="video-viewer__summary">{{ durationText }}</p>

      <dl class="video-viewer__meta-list">
        <div class="video-viewer__meta-row">
          <dt>Resolution</dt>
          <dd>{{ resolutionText || '—' }}</dd>
        </div>
        <div class="video-viewer__meta-row">
          <dt>Codec</dt>
          <dd>{{ codecText || '—' }}</dd>
        </div>
        <div class="video-viewer__meta-row">
          <dt>Bit Rate</dt>
          <dd data-testid="video-viewer-bitrate">{{ bitrateText || '—' }}</dd>
        </div>
        <div class="video-viewer__meta-row">
          <dt>Duration</dt>
          <dd>{{ durationText || '—' }}</dd>
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

const videoUrl = computed(() => {
  const asset = props.manifest?.primary_asset || {}
  return ['video', 'preview_video'].includes(asset.asset_type) ? asset.url || '' : ''
})

const posterUrl = computed(() => props.manifest?.poster_asset?.url || '')

const width = computed(() => summary.value?.dimensions?.width ?? null)
const height = computed(() => summary.value?.dimensions?.height ?? null)

const resolutionText = computed(() => {
  if (width.value == null || height.value == null) {
    return ''
  }
  return `${width.value} × ${height.value}`
})

const codecText = computed(() => summary.value?.codec || '')

const bitrateText = computed(() => {
  const rawValue = Number(summary.value?.bit_rate)
  if (!Number.isFinite(rawValue) || rawValue <= 0) {
    return ''
  }
  if (rawValue >= 1000000) {
    const mbps = rawValue / 1000000
    const normalized = Number.isInteger(mbps) ? String(mbps) : mbps.toFixed(1)
    return `${normalized} Mbps`
  }
  return `${Math.round(rawValue / 1000)} kbps`
})

const durationText = computed(() => {
  const duration = summary.value?.duration_seconds
  return duration == null ? '' : `Duration ${duration} s`
})
</script>

<style scoped>
.video-viewer {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(260px, 0.9fr);
  gap: 20px;
  padding: 20px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 22px;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.12), transparent 36%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.96));
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.08);
}

.video-viewer__stage {
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  min-height: 320px;
  padding: 12px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background:
    linear-gradient(180deg, rgba(15, 23, 42, 0.82), rgba(15, 23, 42, 0.94)),
    #0f172a;
}

.video-viewer__player,
.video-viewer__placeholder {
  display: block;
  width: 100%;
  min-height: 260px;
}

.video-viewer__player {
  height: min(72vh, 720px);
  max-width: 100%;
  object-fit: contain;
  background: #020617;
}

.video-viewer__placeholder {
  display: grid;
  place-items: center;
  color: rgba(226, 232, 240, 0.9);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.video-viewer__panel {
  display: grid;
  gap: 18px;
  align-content: start;
}

.video-viewer__header {
  display: grid;
  gap: 14px;
}

.video-viewer__eyebrow {
  margin: 0 0 6px;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.video-viewer__title {
  margin: 0;
  color: #0f172a;
  font-size: 22px;
  line-height: 1.2;
}

.video-viewer__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.video-viewer__chip {
  display: inline-flex;
  align-items: center;
  padding: 7px 12px;
  border-radius: 999px;
  color: #334155;
  background: rgba(226, 232, 240, 0.9);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.video-viewer__chip--strong {
  color: #1d4ed8;
  background: rgba(219, 234, 254, 0.88);
}

.video-viewer__summary {
  margin: 0;
  color: #475569;
  font-size: 14px;
}

.video-viewer__meta-list {
  display: grid;
  gap: 10px;
  margin: 0;
}

.video-viewer__meta-row {
  display: grid;
  grid-template-columns: minmax(0, 120px) minmax(0, 1fr);
  gap: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(226, 232, 240, 0.88);
}

.video-viewer__meta-row dt {
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.video-viewer__meta-row dd {
  margin: 0;
  color: #0f172a;
  font-size: 14px;
  font-weight: 600;
  text-align: right;
}

@media (max-width: 900px) {
  .video-viewer {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .video-viewer {
    padding: 16px;
    gap: 16px;
    border-radius: 18px;
  }

  .video-viewer__stage {
    min-height: 240px;
    padding: 8px;
  }

  .video-viewer__player,
  .video-viewer__placeholder {
    min-height: 220px;
  }

  .video-viewer__player {
    height: min(54vh, 420px);
  }

  .video-viewer__title {
    font-size: 18px;
  }

  .video-viewer__meta-row {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .video-viewer__meta-row dd {
    text-align: left;
  }
}
</style>
