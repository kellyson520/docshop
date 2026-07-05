<template>
  <div :class="['file-list-cards', `file-list-cards--${variant}`]" :data-testid="testId">
    <article
      v-for="(item, index) in items"
      :key="item.id || index"
      class="file-list-card"
      :class="{
        'file-list-card--parent': item?.type === 'parent',
      }"
    >
      <div class="file-list-card__head">
        <div class="file-list-card__identity">
          <slot name="icon" :item="item">
            <div class="file-list-card__icon">
              <slot name="icon-fallback" :item="item">📄</slot>
            </div>
          </slot>
          <div class="file-list-card__titles">
            <div class="file-list-card__title">
              <slot name="title" :item="item" />
            </div>
            <div v-if="$slots.subtitle" class="file-list-card__subtitle">
              <slot name="subtitle" :item="item" />
            </div>
          </div>
        </div>

        <div v-if="$slots.headerExtra" class="file-list-card__header-extra">
          <slot name="headerExtra" :item="item" />
        </div>
      </div>

      <div v-if="$slots.badges" class="file-list-card__badges">
        <slot name="badges" :item="item" />
      </div>

      <div v-if="$slots.meta" class="file-list-card__meta">
        <slot name="meta" :item="item" />
      </div>

      <div v-if="$slots.summary" class="file-list-card__summary">
        <slot name="summary" :item="item" />
      </div>

      <div v-if="$slots.actions" class="file-list-card__actions">
        <slot name="actions" :item="item" />
      </div>
    </article>
  </div>
</template>

<script setup>
defineProps({
  items: {
    type: Array,
    default: () => [],
  },
  variant: {
    type: String,
    default: 'default',
  },
  testId: {
    type: String,
    default: '',
  },
})
</script>

<style scoped>
.file-list-cards {
  display: grid;
  gap: 12px;
}

.file-list-card {
  padding: 14px 14px 12px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 16px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.96));
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
}

.file-list-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.file-list-card__identity {
  display: flex;
  min-width: 0;
  gap: 12px;
  align-items: flex-start;
}

.file-list-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(14, 165, 233, 0.16));
  color: var(--workspace-blue, #2f5d8c);
  font-size: 20px;
  flex: 0 0 auto;
}

.file-list-card__titles {
  min-width: 0;
}

.file-list-card__title {
  color: #0f172a;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.35;
  word-break: break-word;
}

.file-list-card__subtitle {
  margin-top: 2px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.4;
}

.file-list-card__header-extra {
  flex: 0 0 auto;
}

.file-list-card__badges,
.file-list-card__meta,
.file-list-card__summary,
.file-list-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.file-list-card__badges {
  margin-top: 12px;
}

.file-list-card__meta,
.file-list-card__summary {
  margin-top: 10px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
}

.file-list-card__summary {
  color: #475569;
}

.file-list-card__actions {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(226, 232, 240, 0.75);
}

.file-list-card__actions :deep(.el-button) {
  margin-left: 0;
}

.file-list-card__actions :deep(.el-dropdown) {
  display: inline-flex;
}

.file-list-cards--admin .file-list-card {
  border-color: rgba(191, 219, 254, 0.9);
}

.file-list-cards--share .file-list-card {
  border-color: rgba(209, 213, 219, 0.9);
}

.file-list-card--parent {
  padding-top: 12px;
  padding-bottom: 10px;
}

.file-list-card--parent .file-list-card__icon {
  width: 38px;
  height: 38px;
  border-radius: 12px;
}

.file-list-card--parent .file-list-card__badges {
  margin-top: 8px;
}

.file-list-card--parent .file-list-card__meta,
.file-list-card--parent .file-list-card__summary {
  margin-top: 6px;
}

.file-list-card--parent .file-list-card__actions {
  margin-top: 8px;
  padding-top: 8px;
  border-top: none;
}

@media (max-width: 767px) {
  .file-list-card__actions {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
    align-items: stretch;
  }

  .file-list-card__actions :deep(.el-button),
  .file-list-card__actions :deep(.el-dropdown),
  .file-list-card__actions :deep(.el-dropdown .el-button) {
    width: 100%;
    white-space: normal;
  }

  .file-list-card__actions :deep(.el-button) {
    min-height: 40px;
    justify-content: center;
  }

  .file-list-card--parent .file-list-card__actions {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
