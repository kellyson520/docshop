<template>
  <div class="pdf-diff">
    <div v-if="!hasChanges" class="empty-state">
      <el-empty description="两个版本内容相同，无差异" />
    </div>

    <template v-else>
      <div class="pdf-toolbar">
        <div>
          <div class="toolbar-title">PDF 对比结果</div>
          <div class="toolbar-subtitle">按页展示内容变更，并补充表格级差异摘要。</div>
        </div>
        <div class="toolbar-stats">
          <span class="stat-pill stat-pill--add">新增 {{ counts.added }} 页</span>
          <span class="stat-pill stat-pill--del">删除 {{ counts.deleted }} 页</span>
          <span class="stat-pill stat-pill--mod">修改 {{ counts.modified }} 页</span>
          <span class="stat-pill">{{ tableDiffs.length }} 个表格</span>
        </div>
      </div>

      <div class="mode-switch">
        <el-radio-group v-model="viewMode" size="small">
          <el-radio-button value="text">页内预览</el-radio-button>
          <el-radio-button value="summary">摘要列表</el-radio-button>
        </el-radio-group>
      </div>

      <div v-if="viewMode === 'text'" class="page-grid">
        <article v-for="item in pageDiffs" :key="item.page_number" class="page-card">
          <div class="page-head">
            <div class="page-title">
              <strong>第 {{ item.page_number }} 页</strong>
              <el-tag :type="tagType(item.change_type)" effect="plain" size="small">
                {{ tagLabel(item.change_type) }}
              </el-tag>
            </div>
            <div v-if="item.similarity" class="page-similarity">
              相似度 {{ Math.round(item.similarity * 100) }}%
            </div>
          </div>

          <div class="preview-grid">
            <div class="preview-panel">
              <div class="preview-label">旧版本</div>
              <p class="preview-text preview-text--old">
                {{ item.old_text_preview || '未提供旧页内容' }}
              </p>
            </div>
            <div class="preview-panel">
              <div class="preview-label">新版本</div>
              <p class="preview-text preview-text--new">
                {{ item.new_text_preview || '未提供新页内容' }}
              </p>
            </div>
          </div>
        </article>
      </div>

      <div v-else class="summary-panel">
        <el-timeline>
          <el-timeline-item
            v-for="item in pageDiffs"
            :key="`summary-${item.page_number}`"
            :type="timelineType(item.change_type)"
            :timestamp="`第 ${item.page_number} 页`"
            placement="top"
          >
            <el-card shadow="never" class="change-card">
              <div class="change-topline">
                <el-tag :type="tagType(item.change_type)" size="small" effect="plain">
                  {{ tagLabel(item.change_type) }}
                </el-tag>
                <span v-if="item.similarity" class="change-similarity">
                  相似度 {{ Math.round(item.similarity * 100) }}%
                </span>
              </div>
              <p class="change-preview">{{ item.new_text_preview || item.old_text_preview || '内容变更' }}</p>
              <div class="change-meta">
                <span v-if="item.old_text_preview">旧页有内容</span>
                <span v-if="item.new_text_preview">新页有内容</span>
                <span v-if="item.diff_line_count">差异行 {{ item.diff_line_count }}</span>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </div>

      <section v-if="tableDiffs.length" class="table-section">
        <div class="section-head">
          <h4>表格变更</h4>
          <span>{{ tableDiffs.length }} 个</span>
        </div>
        <div class="table-grid">
          <article v-for="table in tableDiffs" :key="`${table.page_number}-${table.table_index}`" class="table-card">
            <div class="table-head">
              <strong>第 {{ table.page_number }} 页，表格 #{{ table.table_index + 1 }}</strong>
              <el-tag v-if="table.cell_changes?.length" type="warning" size="small" effect="plain">
                {{ table.cell_changes.length }} 处单元格变化
              </el-tag>
            </div>
            <div class="shape-row">
              <span>{{ shapeLabel(table.old_shape) }}</span>
              <el-icon><ArrowRight /></el-icon>
              <span>{{ shapeLabel(table.new_shape) }}</span>
            </div>
            <div v-if="table.cell_changes?.length" class="cell-list">
              <div v-for="cell in table.cell_changes.slice(0, 20)" :key="`${cell.row}-${cell.col}`" class="cell-item">
                <span class="cell-pos">{{ cell.row }},{{ cell.col }}</span>
                <span class="cell-value cell-value--old">{{ formatCell(cell.old_value) }}</span>
                <el-icon><ArrowRight /></el-icon>
                <span class="cell-value cell-value--new">{{ formatCell(cell.new_value) }}</span>
              </div>
            </div>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'

const props = defineProps({
  diffData: {
    type: Object,
    default: () => ({})
  }
})

const viewMode = ref('text')

const pageDiffs = computed(() => normalizePageDiffs(props.diffData))
const tableDiffs = computed(() => Array.isArray(props.diffData?.table_diffs) ? props.diffData.table_diffs : [])
const counts = computed(() => ({
  added: pageDiffs.value.filter((item) => normalizeType(item.change_type) === 'added').length,
  deleted: pageDiffs.value.filter((item) => normalizeType(item.change_type) === 'deleted').length,
  modified: pageDiffs.value.filter((item) => normalizeType(item.change_type) === 'modified').length
}))
const hasChanges = computed(() => pageDiffs.value.length > 0 || tableDiffs.value.length > 0)

function normalizePageDiffs(diffData) {
  const raw = diffData?.page_diffs || diffData?.changes || []
  if (!Array.isArray(raw)) return []
  return raw.map((item) => ({
    ...item,
    change_type: item.change_type || item.type || 'modified'
  }))
}

function normalizeType(value) {
  const type = String(value || '').toLowerCase()
  if (type === 'added' || type === 'insert') return 'added'
  if (type === 'deleted' || type === 'delete') return 'deleted'
  return 'modified'
}

function tagType(value) {
  const type = normalizeType(value)
  if (type === 'added') return 'success'
  if (type === 'deleted') return 'danger'
  return 'warning'
}

function tagLabel(value) {
  const type = normalizeType(value)
  if (type === 'added') return '新增'
  if (type === 'deleted') return '删除'
  return '修改'
}

function timelineType(value) {
  const type = normalizeType(value)
  if (type === 'added') return 'success'
  if (type === 'deleted') return 'danger'
  return 'warning'
}

function shapeLabel(shape) {
  if (!Array.isArray(shape) || shape.length < 2) return '0 x 0'
  return `${shape[0]} x ${shape[1]}`
}

function formatCell(value) {
  if (value === null || value === undefined || value === '') return '(空)'
  return String(value)
}
</script>

<style scoped>
.pdf-diff {
  width: 100%;
}

.pdf-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
  padding: 14px 16px;
  border: 1px solid var(--border-color-light, #e5e7eb);
  border-radius: 8px;
  background: var(--bg-secondary, #fff);
}

.toolbar-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #1f2937);
}

.toolbar-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-secondary, #64748b);
}

.toolbar-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.stat-pill {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--bg-tertiary, #f8fafc);
  color: var(--text-secondary, #475569);
  font-size: 12px;
}

.stat-pill--add {
  background: #f0fdf4;
  color: #166534;
}

.stat-pill--del {
  background: #fef2f2;
  color: #991b1b;
}

.stat-pill--mod {
  background: #fffbeb;
  color: #92400e;
}

.mode-switch {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.page-grid {
  display: grid;
  gap: 12px;
}

.page-card,
.table-card {
  border: 1px solid var(--border-color-light, #e5e7eb);
  border-radius: 8px;
  background: var(--bg-secondary, #fff);
  padding: 14px;
}

.page-head,
.table-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.page-similarity,
.change-similarity {
  color: var(--text-secondary, #64748b);
  font-size: 12px;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.preview-panel {
  min-width: 0;
  padding: 12px;
  border-radius: 8px;
  background: var(--bg-tertiary, #f8fafc);
}

.preview-label {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary, #64748b);
}

.preview-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-primary, #1f2937);
  white-space: pre-wrap;
  word-break: break-word;
}

.preview-text--old {
  color: #b91c1c;
}

.preview-text--new {
  color: #166534;
}

.summary-panel {
  padding: 2px 0 0;
}

.change-card {
  margin-bottom: 0;
}

.change-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.change-preview {
  margin: 0 0 8px;
  color: var(--text-primary, #1f2937);
  font-size: 13px;
  line-height: 1.7;
}

.change-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--text-secondary, #64748b);
  font-size: 12px;
}

.table-section {
  margin-top: 18px;
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.section-head h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
}

.section-head span {
  color: var(--text-secondary, #64748b);
  font-size: 12px;
}

.table-grid {
  display: grid;
  gap: 12px;
}

.shape-row {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary, #64748b);
  font-size: 12px;
  margin-bottom: 10px;
}

.cell-list {
  display: grid;
  gap: 6px;
}

.cell-item {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  font-size: 12px;
}

.cell-pos {
  color: var(--text-tertiary, #94a3b8);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

.cell-value {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cell-value--old {
  color: #b91c1c;
  text-decoration: line-through;
}

.cell-value--new {
  color: #166534;
}

.empty-state {
  padding: 42px 0;
  text-align: center;
}

@media (max-width: 960px) {
  .preview-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .pdf-toolbar {
    flex-direction: column;
  }

  .toolbar-stats,
  .mode-switch {
    justify-content: flex-start;
  }

  .cell-item {
    grid-template-columns: 1fr;
    gap: 6px;
    padding: 8px;
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 10px;
    background: rgba(248, 250, 252, 0.72);
  }

  .cell-value {
    white-space: normal;
    overflow-wrap: anywhere;
  }

  .preview-panel,
  .table-card,
  .change-card {
    border-radius: 12px;
  }

  .preview-text,
  .change-preview {
    overflow-wrap: anywhere;
  }
}
</style>
