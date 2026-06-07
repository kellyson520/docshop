<template>
  <section v-if="hasChanges" class="diff-summary">
    <div class="summary-shell">
      <div class="summary-head">
        <div class="summary-title">
          <span class="summary-kicker">变更概览</span>
          <h3>{{ summary || '文档对比完成' }}</h3>
          <div v-if="taskMetaItems.length" class="summary-meta">
            <span v-for="item in taskMetaItems" :key="item.label">{{ item.label }} {{ item.value }}</span>
          </div>
        </div>
        <div v-if="changeItems.length" class="summary-position">
          <span>{{ currentHunk + 1 }}</span>
          <span>/</span>
          <span>{{ changeItems.length }}</span>
        </div>
      </div>

      <div class="summary-stats">
        <button class="stat-chip stat-chip--add" type="button" @click="jumpByType('insert')">
          <el-icon><Plus /></el-icon>
          <span>新增</span>
          <strong>{{ insertCount }}</strong>
        </button>
        <button class="stat-chip stat-chip--del" type="button" @click="jumpByType('delete')">
          <el-icon><Minus /></el-icon>
          <span>删除</span>
          <strong>{{ deleteCount }}</strong>
        </button>
        <button class="stat-chip stat-chip--mod" type="button" @click="jumpByType('modified')">
          <el-icon><Edit /></el-icon>
          <span>修改</span>
          <strong>{{ modifiedCount }}</strong>
        </button>
        <button class="stat-chip stat-chip--move" type="button" @click="jumpByType('move')">
          <el-icon><Sort /></el-icon>
          <span>移动</span>
          <strong>{{ moveCount }}</strong>
        </button>
        <button v-if="tableCount" class="stat-chip stat-chip--table stat-chip--passive" type="button">
          <el-icon><Sort /></el-icon>
          <span>表格</span>
          <strong>{{ tableCount }}</strong>
        </button>
        <button v-if="imageAddedCount" class="stat-chip stat-chip--image-add stat-chip--passive" type="button">
          <el-icon><Picture /></el-icon>
          <span>图片新增</span>
          <strong>{{ imageAddedCount }}</strong>
        </button>
        <button v-if="imageDeletedCount" class="stat-chip stat-chip--image-del stat-chip--passive" type="button">
          <el-icon><Minus /></el-icon>
          <span>图片删除</span>
          <strong>{{ imageDeletedCount }}</strong>
        </button>
        <button v-if="imageReplacedCount" class="stat-chip stat-chip--image-replace stat-chip--passive" type="button">
          <el-icon><Refresh /></el-icon>
          <span>图片替换</span>
          <strong>{{ imageReplacedCount }}</strong>
        </button>
        <button v-if="imageResizedCount" class="stat-chip stat-chip--image-resize stat-chip--passive" type="button">
          <el-icon><Refresh /></el-icon>
          <span>尺寸调整</span>
          <strong>{{ imageResizedCount }}</strong>
        </button>
      </div>

      <div class="summary-nav">
        <el-button-group>
          <el-button size="small" :disabled="!changeItems.length" @click="prevHunk">
            <el-icon><ArrowUp /></el-icon>
            上一处
          </el-button>
          <el-button size="small" :disabled="!changeItems.length" @click="nextHunk">
            下一处
            <el-icon><ArrowDown /></el-icon>
          </el-button>
        </el-button-group>
      </div>

      <div v-if="changeItems.length" class="change-list">
        <button
          v-for="(item, idx) in changeItems"
          :key="`${item.index}-${idx}`"
          type="button"
          class="change-item"
          :class="[{ active: idx === currentHunk }, `change-item--${item.type}`]"
          @click="selectHunk(idx)"
        >
          <span class="change-marker">{{ item.label }}</span>
          <span class="change-preview">{{ item.preview }}</span>
        </button>
      </div>

      <div v-else class="summary-empty">
        当前数据没有逐段明细，仅保留摘要信息。
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Plus, Minus, Edit, ArrowUp, ArrowDown, Sort, Picture, Refresh } from '@element-plus/icons-vue'

const props = defineProps({
  summary: { type: String, default: '' },
  stats: { type: Object, default: () => ({}) },
  status: { type: String, default: '' },
  metadata: { type: Object, default: () => ({}) },
  paragraphs: { type: Array, default: () => [] },
  tables: { type: Array, default: () => [] },
  images: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['jump-to'])

const currentHunk = ref(0)

const changeItems = computed(() => {
  const items = []

  for (let i = 0; i < props.paragraphs.length; i += 1) {
    const paragraph = props.paragraphs[i] || {}
    const type = normalizeType(paragraph.change_type || paragraph.op)
    if (!type) continue

    const text = cleanText(paragraph.new_text || paragraph.old_text || paragraph.text || '')
    items.push({
      index: i,
      type,
      label: labelByType(type),
      preview: truncate(text)
    })
  }

  return items
})

const insertCount = computed(() => pickCount(['paragraphs_added', 'added'], 'insert'))
const deleteCount = computed(() => pickCount(['paragraphs_deleted', 'deleted'], 'delete'))
const modifiedCount = computed(() => pickCount(['paragraphs_modified', 'modified'], 'modified'))
const moveCount = computed(() => pickCount(['paragraphs_moved', 'moved'], 'move'))
const tableCount = computed(() => pickStatNumber(['tables_changed'], props.tables.length))
const imageAddedCount = computed(() => pickImageCount(['image_added', 'images_added'], 'added'))
const imageDeletedCount = computed(() => pickImageCount(['image_deleted', 'images_deleted'], 'deleted'))
const imageReplacedCount = computed(() => pickImageCount(['image_replaced', 'images_replaced'], 'replaced'))
const imageResizedCount = computed(() => pickImageCount(['image_resized', 'images_resized'], 'resized'))
const nonTextChangeCount = computed(() =>
  tableCount.value +
  imageAddedCount.value +
  imageDeletedCount.value +
  imageReplacedCount.value +
  imageResizedCount.value
)

const hasChanges = computed(() =>
  changeItems.value.length > 0 ||
  nonTextChangeCount.value > 0 ||
  Boolean(props.summary)
)

const taskMetaItems = computed(() => {
  const items = []
  const status = props.status || props.metadata?.status
  const elapsed = props.metadata?.elapsed_ms ?? props.stats?.elapsed_ms
  const fileType = props.metadata?.file_type
  if (status) items.push({ label: '状态', value: status })
  if (elapsed !== undefined && elapsed !== null && elapsed !== '') items.push({ label: '耗时', value: `${elapsed} ms` })
  if (fileType) items.push({ label: '类型', value: fileType })
  return items
})

watch(changeItems, () => {
  if (currentHunk.value >= changeItems.value.length) {
    currentHunk.value = 0
  }
})

function normalizeType(value) {
  const type = String(value || '').toLowerCase()
  if (type === 'insert') return 'insert'
  if (type === 'delete') return 'delete'
  if (type === 'move' || type === 'moved') return 'move'
  if (type === 'replace' || type === 'modified' || type === 'modify') return 'modified'
  return ''
}

function labelByType(type) {
  if (type === 'insert') return '新增'
  if (type === 'delete') return '删除'
  if (type === 'move') return '移动'
  return '修改'
}

function cleanText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim()
}

function truncate(value, limit = 72) {
  if (!value) return '无文本预览'
  return value.length > limit ? `${value.slice(0, limit)}…` : value
}

function pickCount(keys, fallbackType) {
  const value = pickStatNumber(keys, 0)
  if (value > 0) return value
  return changeItems.value.filter((item) => item.type === fallbackType).length
}

function pickStatNumber(keys, fallback = 0) {
  const stats = props.stats || {}
  for (const key of keys) {
    const value = Number(stats[key])
    if (Number.isFinite(value) && value > 0) return value
  }
  return Number(fallback || 0)
}

function pickImageCount(statKeys, imageKey) {
  const fromStats = pickStatNumber(statKeys, 0)
  if (fromStats > 0) return fromStats
  const value = (props.images || {})[imageKey]
  if (Array.isArray(value)) return value.length
  const number = Number(value)
  return Number.isFinite(number) && number > 0 ? number : 0
}

function selectHunk(idx) {
  const item = changeItems.value[idx]
  if (!item) return
  currentHunk.value = idx
  emit('jump-to', item.index)
}

function prevHunk() {
  if (!changeItems.value.length) return
  const next = currentHunk.value - 1
  currentHunk.value = next < 0 ? changeItems.value.length - 1 : next
  emit('jump-to', changeItems.value[currentHunk.value].index)
}

function nextHunk() {
  if (!changeItems.value.length) return
  const next = currentHunk.value + 1
  currentHunk.value = next >= changeItems.value.length ? 0 : next
  emit('jump-to', changeItems.value[currentHunk.value].index)
}

function jumpByType(type) {
  const index = changeItems.value.findIndex((item) => item.type === type)
  if (index >= 0) selectHunk(index)
}

defineExpose({ currentHunk, selectHunk, prevHunk, nextHunk })
</script>

<style scoped>
.diff-summary {
  margin-bottom: 16px;
}

.summary-shell {
  border: 1px solid var(--border-color-light, #e5e7eb);
  border-radius: 8px;
  background: var(--bg-secondary, #fff);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.05);
  padding: 16px;
}

.summary-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.summary-kicker {
  display: inline-flex;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
  color: var(--color-primary, #1a5276);
  margin-bottom: 6px;
}

.summary-title h3 {
  margin: 0;
  font-size: 16px;
  line-height: 1.35;
  color: var(--text-primary, #1f2937);
}

.summary-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.summary-meta span {
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.12);
  color: var(--text-secondary, #64748b);
  font-size: 12px;
}

.summary-position {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 999px;
  background: var(--bg-tertiary, #f8fafc);
  color: var(--text-secondary, #64748b);
  font-size: 12px;
  white-space: nowrap;
}

.summary-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}

.stat-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 12px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: var(--bg-tertiary, #f8fafc);
  color: var(--text-primary, #1f2937);
  font-size: 13px;
  cursor: pointer;
  transition: transform 0.15s ease, border-color 0.15s ease, background-color 0.15s ease;
}

.stat-chip strong {
  font-size: 14px;
}

.stat-chip:hover {
  transform: translateY(-1px);
}

.stat-chip--passive {
  cursor: default;
}

.stat-chip--passive:hover {
  transform: none;
}

.stat-chip--add {
  border-color: rgba(34, 197, 94, 0.18);
  color: #166534;
  background: #f0fdf4;
}

.stat-chip--del {
  border-color: rgba(239, 68, 68, 0.18);
  color: #991b1b;
  background: #fef2f2;
}

.stat-chip--mod {
  border-color: rgba(245, 158, 11, 0.18);
  color: #92400e;
  background: #fffbeb;
}

.stat-chip--move {
  border-color: rgba(99, 102, 241, 0.2);
  color: #3730a3;
  background: #eef2ff;
}

.stat-chip--table {
  border-color: rgba(14, 165, 233, 0.2);
  color: #075985;
  background: #f0f9ff;
}

.stat-chip--image-add {
  border-color: rgba(16, 185, 129, 0.2);
  color: #047857;
  background: #ecfdf5;
}

.stat-chip--image-del {
  border-color: rgba(248, 113, 113, 0.2);
  color: #b91c1c;
  background: #fff1f2;
}

.stat-chip--image-replace {
  border-color: rgba(217, 119, 6, 0.2);
  color: #92400e;
  background: #fffbeb;
}

.stat-chip--image-resize {
  border-color: rgba(20, 184, 166, 0.2);
  color: #0f766e;
  background: #f0fdfa;
}

.summary-nav {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.change-list {
  max-height: 300px;
  overflow: auto;
  border: 1px solid var(--border-color-light, #e5e7eb);
  border-radius: 8px;
}

.change-item {
  width: 100%;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  background: transparent;
  border: 0;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  text-align: left;
  cursor: pointer;
  transition: background-color 0.15s ease, transform 0.15s ease;
}

.change-item:last-child {
  border-bottom: 0;
}

.change-item:hover {
  background: rgba(59, 130, 246, 0.04);
}

.change-item.active {
  background: rgba(59, 130, 246, 0.08);
}

.change-marker {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 42px;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.change-item--insert .change-marker {
  background: #dcfce7;
  color: #166534;
}

.change-item--delete .change-marker {
  background: #fee2e2;
  color: #991b1b;
}

.change-item--modified .change-marker {
  background: #fef3c7;
  color: #92400e;
}

.change-item--move .change-marker {
  background: #e0e7ff;
  color: #3730a3;
}

.change-preview {
  min-width: 0;
  color: var(--text-secondary, #475569);
  font-size: 13px;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-empty {
  padding: 14px 12px 4px;
  color: var(--text-secondary, #64748b);
  font-size: 13px;
}

@media (max-width: 640px) {
  .summary-head {
    flex-direction: column;
  }

  .summary-position {
    align-self: flex-start;
  }

  .summary-nav {
    justify-content: flex-start;
  }
}
</style>
