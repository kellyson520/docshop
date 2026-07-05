<template>
  <section class="html-diff-view">
    <header class="html-diff-view__header">
      <div>
        <h3>HTML 语义对比</h3>
        <p>{{ summaryText }}</p>
      </div>
      <strong>{{ totalChanges }} 处变更</strong>
    </header>

    <div class="html-diff-view__stats">
      <button
        v-for="item in filters"
        :key="item.key"
        type="button"
        class="html-diff-view__stat"
        :class="{ 'is-active': activeFilter === item.key }"
        :data-testid="`html-diff-filter-${item.key}`"
        @click="activeFilter = item.key"
      >
        <span>{{ item.label }}</span>
        <strong>{{ item.count }}</strong>
      </button>
    </div>

    <div v-if="hasPreviewFrames" class="html-diff-view__frames">
      <article>
        <header>旧版预览</header>
        <iframe
          class="html-diff-view__frame"
          :src="previewUrls.old"
          title="old-html-runtime-preview"
          sandbox="allow-scripts allow-forms allow-modals allow-downloads"
          referrerpolicy="no-referrer"
        />
      </article>
      <article>
        <header>新版预览</header>
        <iframe
          class="html-diff-view__frame"
          :src="previewUrls.new"
          title="new-html-runtime-preview"
          sandbox="allow-scripts allow-forms allow-modals allow-downloads"
          referrerpolicy="no-referrer"
        />
      </article>
    </div>

    <div class="html-diff-view__list">
      <article
        v-for="(item, index) in visibleItems"
        :key="`${item.kind}-${index}-${item.path || item.new_path || item.old_path}`"
        class="html-diff-view__item"
      >
        <div class="html-diff-view__item-head">
          <el-tag size="small" effect="plain">{{ kindLabel(item.kind) }}</el-tag>
          <code>{{ item.path || item.new_path || item.old_path || '-' }}</code>
        </div>
        <div class="html-diff-view__item-meta">
          <span>{{ item.change_type || 'changed' }}</span>
          <span v-if="item.tag">&lt;{{ item.tag }}&gt;</span>
          <span v-if="item.attribute">{{ item.attribute }}</span>
        </div>
        <div class="html-diff-view__item-body">
          <pre v-if="item.old_text || item.old_value" class="is-old">{{ item.old_text || item.old_value }}</pre>
          <pre v-if="item.new_text || item.new_value" class="is-new">{{ item.new_text || item.new_value }}</pre>
          <pre v-if="item.text && !item.old_text && !item.new_text">{{ item.text }}</pre>
        </div>
      </article>

      <el-empty v-if="visibleItems.length === 0" description="当前筛选下没有差异" />
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  diffData: {
    type: Object,
    required: true,
  },
})

const activeFilter = ref('all')

const stats = computed(() => props.diffData?.stats || {})
const totalChanges = computed(() => Number(stats.value.total_changes || 0))
const summaryText = computed(() => (
  props.diffData?.summaryText
  || props.diffData?.summary_text
  || props.diffData?.summary
  || 'HTML 语义差异'
))

const previewUrls = computed(() => ({
  old: props.diffData?.payload?.old_preview_url || '',
  new: props.diffData?.payload?.new_preview_url || '',
}))

const hasPreviewFrames = computed(() => Boolean(previewUrls.value.old && previewUrls.value.new))

function listWithKind(kind, value) {
  return Array.isArray(value) ? value.map((item) => ({ ...item, kind })) : []
}

const groups = computed(() => ({
  text: listWithKind('text', props.diffData?.text),
  structure: listWithKind('structure', props.diffData?.nodes),
  attributes: listWithKind('attributes', props.diffData?.attributes),
  resources: listWithKind('resources', props.diffData?.resources),
  tables: listWithKind('tables', props.diffData?.tables),
}))

const allItems = computed(() => [
  ...groups.value.text,
  ...groups.value.structure,
  ...groups.value.attributes,
  ...groups.value.resources,
  ...groups.value.tables,
])

const filters = computed(() => [
  { key: 'all', label: '全部', count: allItems.value.length },
  { key: 'text', label: '文本', count: groups.value.text.length },
  { key: 'structure', label: '结构', count: groups.value.structure.length },
  { key: 'attributes', label: '属性', count: groups.value.attributes.length },
  { key: 'resources', label: '资源', count: groups.value.resources.length },
  { key: 'tables', label: '表格', count: groups.value.tables.length },
])

const visibleItems = computed(() => (
  activeFilter.value === 'all' ? allItems.value : groups.value[activeFilter.value] || []
))

function kindLabel(kind) {
  return {
    text: '文本',
    structure: '结构',
    attributes: '属性',
    resources: '资源',
    tables: '表格',
  }[kind] || kind
}
</script>

<style scoped>
.html-diff-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.html-diff-view__header,
.html-diff-view__item-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.html-diff-view__header h3 {
  margin: 0 0 4px;
  font-size: 18px;
}

.html-diff-view__header p {
  margin: 0;
  color: var(--text-secondary);
}

.html-diff-view__stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 10px;
}

.html-diff-view__stat {
  border: 1px solid var(--border-color-light);
  border-radius: 10px;
  background: var(--bg-secondary, #fff);
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  cursor: pointer;
}

.html-diff-view__stat.is-active {
  border-color: var(--workspace-blue, #2f5d8c);
  color: var(--workspace-blue, #2f5d8c);
  background: color-mix(in srgb, var(--workspace-blue, #2f5d8c) 8%, white);
}

.html-diff-view__frames {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.html-diff-view__frames article {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.html-diff-view__frame {
  width: 100%;
  min-height: 520px;
  border: 1px solid var(--border-color-light);
  border-radius: 10px;
  background: #fff;
}

.html-diff-view__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.html-diff-view__item {
  border: 1px solid var(--border-color-light);
  border-radius: 10px;
  padding: 12px;
  background: var(--bg-secondary, #fff);
}

.html-diff-view__item-head code {
  color: var(--text-tertiary);
  word-break: break-all;
}

.html-diff-view__item-meta {
  display: flex;
  gap: 8px;
  margin: 8px 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.html-diff-view__item-body {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px;
}

.html-diff-view__item-body pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  border-radius: 8px;
  padding: 10px;
  background: var(--surface-muted, #f8fafc);
}

.html-diff-view__item-body .is-old {
  background: rgba(239, 68, 68, 0.08);
}

.html-diff-view__item-body .is-new {
  background: rgba(34, 197, 94, 0.08);
}

@media (max-width: 900px) {
  .html-diff-view__frames {
    grid-template-columns: 1fr;
  }
}
</style>
