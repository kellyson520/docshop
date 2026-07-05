<template>
  <div class="xlsx-diff">
    <div v-if="sheetList.length === 0" class="empty-state">
      <el-empty description="无表格数据" />
    </div>

    <template v-else>
      <div class="xlsx-toolbar">
        <div>
          <div class="toolbar-title">XLSX 工作表对比</div>
          <div class="toolbar-subtitle">按工作表拆分，直接展示行列增删与单元格变化。</div>
        </div>
        <div class="toolbar-stats">
          <span class="stat-pill">{{ sheetList.length }} 个工作表</span>
          <span class="stat-pill stat-pill--mod">{{ totalCells }} 个单元格变更</span>
        </div>
      </div>

      <el-tabs v-model="activeSheetKey" type="border-card" class="sheet-tabs">
        <el-tab-pane
          v-for="sheet in sheetList"
          :key="sheet.key"
          :label="sheet.sheet_name || sheet.key"
          :name="sheet.key"
        >
          <div class="sheet-panel">
            <div class="sheet-head">
              <div class="sheet-title">
                <strong>{{ sheet.sheet_name || sheet.key }}</strong>
                <span>{{ shapeLabel(sheet.shape_old) }} → {{ shapeLabel(sheet.shape_new) }}</span>
              </div>
              <div class="sheet-tags">
                <el-tag type="warning" effect="plain" size="small">
                  {{ sheet.stats?.cells_modified || 0 }} 处修改
                </el-tag>
                <el-tag v-if="sheet.stats?.rows_added" type="success" effect="plain" size="small">
                  +{{ sheet.stats.rows_added }} 行
                </el-tag>
                <el-tag v-if="sheet.stats?.rows_deleted" type="danger" effect="plain" size="small">
                  -{{ sheet.stats.rows_deleted }} 行
                </el-tag>
                <el-tag v-if="sheet.stats?.cols_added" type="success" effect="plain" size="small">
                  +{{ sheet.stats.cols_added }} 列
                </el-tag>
                <el-tag v-if="sheet.stats?.cols_deleted" type="danger" effect="plain" size="small">
                  -{{ sheet.stats.cols_deleted }} 列
                </el-tag>
              </div>
            </div>

            <div v-if="sheet.added_rows?.length || sheet.deleted_rows?.length || sheet.added_cols?.length || sheet.deleted_cols?.length" class="mutations">
              <div v-if="sheet.added_rows?.length" class="mutation-group">
                <span class="mutation-label">新增行</span>
                <el-tag
                  v-for="row in sheet.added_rows"
                  :key="`ar-${row}`"
                  type="success"
                  effect="plain"
                  size="small"
                >
                  第 {{ row }} 行
                </el-tag>
              </div>
              <div v-if="sheet.deleted_rows?.length" class="mutation-group">
                <span class="mutation-label">删除行</span>
                <el-tag
                  v-for="row in sheet.deleted_rows"
                  :key="`dr-${row}`"
                  type="danger"
                  effect="plain"
                  size="small"
                >
                  第 {{ row }} 行
                </el-tag>
              </div>
              <div v-if="sheet.added_cols?.length" class="mutation-group">
                <span class="mutation-label">新增列</span>
                <el-tag
                  v-for="col in sheet.added_cols"
                  :key="`ac-${col}`"
                  type="success"
                  effect="plain"
                  size="small"
                >
                  {{ col }}
                </el-tag>
              </div>
              <div v-if="sheet.deleted_cols?.length" class="mutation-group">
                <span class="mutation-label">删除列</span>
                <el-tag
                  v-for="col in sheet.deleted_cols"
                  :key="`dc-${col}`"
                  type="danger"
                  effect="plain"
                  size="small"
                >
                  {{ col }}
                </el-tag>
              </div>
            </div>

            <el-table
              v-if="sheet.cell_changes?.length"
              :data="sheet.cell_changes"
              border
              stripe
              size="small"
              class="change-table"
              :max-height="560"
            >
              <el-table-column label="单元格" width="120">
                <template #default="{ row }">
                  <span class="cell-address">{{ cellAddress(row.col) }}{{ row.row }}</span>
                </template>
              </el-table-column>
              <el-table-column label="旧值" min-width="180" show-overflow-tooltip>
                <template #default="{ row }">
                  <span class="old-value">{{ formatCellValue(row.old_value) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="新值" min-width="180" show-overflow-tooltip>
                <template #default="{ row }">
                  <span class="new-value">{{ formatCellValue(row.new_value) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="类型" width="100" align="center">
                <template #default="{ row }">
                  <el-tag :type="tagType(row.change_type)" size="small" effect="light">
                    {{ tagLabel(row.change_type) }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>

            <div v-if="sheet.cell_changes?.length" class="mobile-change-list">
              <article
                v-for="cell in sheet.cell_changes"
                :key="`mobile-${cell.row}-${cell.col}`"
                class="mobile-change-card"
              >
                <div class="mobile-change-head">
                  <span class="cell-address">{{ cellAddress(cell.col) }}{{ cell.row }}</span>
                  <el-tag :type="tagType(cell.change_type)" size="small" effect="light">
                    {{ tagLabel(cell.change_type) }}
                  </el-tag>
                </div>
                <div class="mobile-cell-side mobile-cell-side--old">
                  <span>旧值</span>
                  <p>{{ formatCellValue(cell.old_value) }}</p>
                </div>
                <div class="mobile-cell-side mobile-cell-side--new">
                  <span>新值</span>
                  <p>{{ formatCellValue(cell.new_value) }}</p>
                </div>
              </article>
            </div>

            <el-empty v-else description="该工作表没有单元格级变更" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  diffData: {
    type: Object,
    default: () => ({})
  }
})

const sheetList = computed(() => normalizeSheets(props.diffData?.sheets))
const activeSheetKey = ref('')

const totalCells = computed(() =>
  sheetList.value.reduce((sum, sheet) => sum + (sheet.stats?.cells_modified || 0), 0)
)

watch(
  sheetList,
  (list) => {
    if (!list.length) {
      activeSheetKey.value = ''
      return
    }
    if (!list.find((sheet) => sheet.key === activeSheetKey.value)) {
      activeSheetKey.value = list[0].key
    }
  },
  { immediate: true }
)

function normalizeSheets(rawSheets) {
  if (!rawSheets) return []

  if (Array.isArray(rawSheets)) {
    return rawSheets.map((sheet, index) => ({
      key: String(sheet.sheet_name || sheet.name || index),
      sheet_name: sheet.sheet_name || sheet.name || `Sheet ${index + 1}`,
      ...sheet
    }))
  }

  if (typeof rawSheets === 'object') {
    return Object.entries(rawSheets).map(([sheetName, sheet], index) => ({
      key: String(sheetName || index),
      sheet_name: sheetName,
      ...sheet
    }))
  }

  return []
}

function shapeLabel(shape) {
  if (!Array.isArray(shape) || shape.length < 2) return '0 x 0'
  return `${shape[0]} x ${shape[1]}`
}

function formatCellValue(value) {
  if (value === null || value === undefined || value === '') return '(空)'
  return String(value)
}

function cellAddress(col) {
  const colIndex = Number(col)
  if (!Number.isFinite(colIndex) || colIndex <= 0) return ''

  let index = colIndex
  let letters = ''
  while (index > 0) {
    index -= 1
    letters = String.fromCharCode(65 + (index % 26)) + letters
    index = Math.floor(index / 26)
  }
  return letters
}

function tagType(changeType) {
  const type = String(changeType || '').toLowerCase()
  if (type === 'added') return 'success'
  if (type === 'deleted') return 'danger'
  return 'warning'
}

function tagLabel(changeType) {
  const type = String(changeType || '').toLowerCase()
  if (type === 'added') return '新增'
  if (type === 'deleted') return '删除'
  return '修改'
}
</script>

<style scoped>
.xlsx-diff {
  width: 100%;
}

.xlsx-toolbar {
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

.stat-pill--mod {
  background: #fffbeb;
  color: #92400e;
}

.sheet-panel {
  display: grid;
  gap: 14px;
  padding: 4px 0 0;
}

.sheet-head {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sheet-title {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}

.sheet-title strong {
  font-size: 15px;
  color: var(--text-primary, #1f2937);
}

.sheet-title span {
  color: var(--text-secondary, #64748b);
  font-size: 12px;
}

.sheet-tags,
.mutations {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.mutations {
  display: grid;
  gap: 10px;
}

.mutation-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.mutation-label {
  font-size: 12px;
  color: var(--text-secondary, #64748b);
  min-width: 56px;
}

.change-table {
  border-radius: 8px;
  overflow: hidden;
}

.mobile-change-list {
  display: none;
}

.cell-address {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: var(--text-primary, #1f2937);
}

.old-value {
  color: #b91c1c;
  text-decoration: line-through;
}

.new-value {
  color: #166534;
}

.empty-state {
  padding: 42px 0;
  text-align: center;
}

@media (max-width: 640px) {
  .xlsx-toolbar {
    flex-direction: column;
  }

  .toolbar-stats {
    justify-content: flex-start;
  }

  .change-table {
    display: none;
  }

  .mobile-change-list {
    display: grid;
    gap: 10px;
  }

  .mobile-change-card {
    min-width: 0;
    overflow: hidden;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.96);
  }

  .mobile-change-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 9px 10px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }

  .mobile-cell-side {
    display: grid;
    gap: 4px;
    padding: 10px;
  }

  .mobile-cell-side + .mobile-cell-side {
    border-top: 1px dashed rgba(148, 163, 184, 0.24);
  }

  .mobile-cell-side span {
    width: max-content;
    padding: 2px 7px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 800;
  }

  .mobile-cell-side--old span {
    background: #fee2e2;
    color: #991b1b;
  }

  .mobile-cell-side--new span {
    background: #dcfce7;
    color: #166534;
  }

  .mobile-cell-side p {
    margin: 0;
    color: var(--text-primary, #1f2937);
    font-size: 13px;
    line-height: 1.65;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
  }
}
</style>
