<template>
  <div class="docx-diff">
    <div v-if="!hasAnyChanges" class="empty-state">
      <el-empty description="两个版本内容相同，无差异" />
    </div>

    <template v-else>
      <div class="diff-toolbar">
        <div class="toolbar-copy">
          <div class="toolbar-title">DOCX 逐段对比</div>
          <div class="toolbar-subtitle">按类型/操作筛选，搜索后只显示命中的文字、表格和图片。</div>
        </div>
        <div class="toolbar-stats">
          <span class="stat-pill stat-pill--add">新增 {{ counts.insert }}</span>
          <span class="stat-pill stat-pill--del">删除 {{ counts.delete }}</span>
          <span class="stat-pill stat-pill--mod">修改 {{ counts.modified }}</span>
          <span class="stat-pill stat-pill--move">移动 {{ counts.move }}</span>
          <span class="stat-pill">{{ tables.length }} 个表格</span>
          <span class="stat-pill">{{ imageCount }} 张图片</span>
        </div>
        <div class="toolbar-controls">
          <div class="filter-strip" aria-label="DOCX diff filters">
            <button
              v-for="option in filterOptions"
              :key="option.id"
              type="button"
              class="filter-chip"
              :class="{ 'filter-chip--active': activeFilter === option.id }"
              :data-testid="`docx-filter-${option.id}`"
              @click="setFilter(option.id)"
            >
              {{ option.label }}
            </button>
          </div>
          <label class="search-box">
            <span>搜索</span>
            <input
              v-model="searchQuery"
              data-testid="docx-diff-search"
              class="diff-search-input"
              type="search"
              placeholder="段落 / 表格 / 图片名 / hash"
            />
          </label>
        </div>
      </div>

      <div v-if="!hasVisibleChanges" class="filter-empty">当前筛选没有匹配结果</div>

      <section v-if="showTextPanel" ref="paragraphShellRef" class="paragraph-diff-shell">
        <header class="paragraph-shell-head">
          <div>
            <h4>逐段对比</h4>
            <p>共 {{ renderedParagraphs.length }} 段，{{ changedParagraphIndexes.length }} 处变更</p>
          </div>
          <button
            type="button"
            class="next-change-button"
            :disabled="changedParagraphIndexes.length === 0"
            @click="jumpToNextChange"
          >
            下一处修改
          </button>
        </header>

      <div class="diff-container">
        <section class="diff-panel">
          <header class="panel-header">
            <span>旧版本</span>
            <span class="panel-meta">{{ visibleParagraphs.length }} / {{ paragraphs.length }} 段</span>
          </header>
          <div ref="oldPanelRef" class="panel-body" @scroll="onOldScroll">
            <div
              v-for="(para, index) in renderedParagraphs"
              :key="`old-${index}-${imageKey(para)}`"
              :data-hunk="index"
              class="diff-line"
              :class="[getOldClass(para), { 'hunk-flash': flashingIndex === index, 'search-hit': isSearchHit(para) }]"
            >
              <span class="line-index">{{ index + 1 }}</span>
              <div class="line-content">
                <template v-if="getOp(para) === 'equal'">{{ para.old_text || para.text }}</template>
                <template v-else-if="getOp(para) === 'delete'">{{ para.old_text || para.text }}</template>
                <template v-else-if="getOp(para) === 'move'">
                  <span class="move-badge">{{ moveDescription(para) }}</span>
                  {{ para.old_text || para.text }}
                </template>
                <template v-else-if="getOp(para) === 'modified'">
                  <span
                    v-for="(seg, si) in renderCharDiffs(para.char_diffs, 'old')"
                    :key="si"
                    :class="seg.class"
                  >
                    {{ seg.text }}
                  </span>
                </template>
              </div>
            </div>
          </div>
        </section>

        <section class="diff-panel">
          <header class="panel-header">
            <span>新版本</span>
            <span class="panel-meta">{{ visibleParagraphs.length }} / {{ paragraphs.length }} 段</span>
          </header>
          <div ref="newPanelRef" class="panel-body" @scroll="onNewScroll">
            <div
              v-for="(para, index) in renderedParagraphs"
              :key="`new-${index}-${imageKey(para)}`"
              :data-hunk="index"
              class="diff-line"
              :class="[getNewClass(para), { 'hunk-flash': flashingIndex === index, 'search-hit': isSearchHit(para) }]"
            >
              <span class="line-index">{{ index + 1 }}</span>
              <div class="line-content">
                <template v-if="getOp(para) === 'equal'">{{ para.new_text || para.text }}</template>
                <template v-else-if="getOp(para) === 'insert'">{{ para.new_text || para.text }}</template>
                <template v-else-if="getOp(para) === 'move'">
                  <span class="move-badge">{{ moveDescription(para) }}</span>
                  {{ para.new_text || para.text }}
                </template>
                <template v-else-if="getOp(para) === 'modified'">
                  <span
                    v-for="(seg, si) in renderCharDiffs(para.char_diffs, 'new')"
                    :key="si"
                    :class="seg.class"
                  >
                    {{ seg.text }}
                  </span>
                </template>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div class="mobile-diff-list" aria-label="移动端逐段对比">
        <article
          v-for="(para, index) in renderedParagraphs"
          :key="`mobile-${index}-${imageKey(para)}`"
          :data-hunk="index"
          class="mobile-diff-card"
          :class="[`mobile-diff-card--${getOp(para)}`, { 'hunk-flash': flashingIndex === index, 'search-hit': isSearchHit(para) }]"
        >
          <div class="mobile-diff-head">
            <span class="mobile-line-index">第 {{ index + 1 }} 段</span>
            <span class="mobile-op-badge">{{ opLabel(para) }}</span>
          </div>

          <template v-if="getOp(para) === 'equal'">
            <div class="mobile-side mobile-side--same">
              <span class="mobile-side-label">内容</span>
              <p>{{ para.new_text || para.old_text || para.text }}</p>
            </div>
          </template>

          <template v-else>
            <div v-if="getOp(para) !== 'insert'" class="mobile-side mobile-side--old">
              <span class="mobile-side-label">旧版</span>
              <p v-if="getOp(para) !== 'modified'">
                <span v-if="getOp(para) === 'move'" class="move-badge">{{ moveDescription(para) }}</span>
                {{ para.old_text || para.text || '（空）' }}
              </p>
              <p v-else>
                <span
                  v-for="(seg, si) in renderCharDiffs(para.char_diffs, 'old')"
                  :key="`mobile-old-${si}`"
                  :class="seg.class"
                >
                  {{ seg.text }}
                </span>
              </p>
            </div>

            <div v-if="getOp(para) !== 'delete'" class="mobile-side mobile-side--new">
              <span class="mobile-side-label">新版</span>
              <p v-if="getOp(para) !== 'modified'">
                <span v-if="getOp(para) === 'move'" class="move-badge">{{ moveDescription(para) }}</span>
                {{ para.new_text || para.text || '（空）' }}
              </p>
              <p v-else>
                <span
                  v-for="(seg, si) in renderCharDiffs(para.char_diffs, 'new')"
                  :key="`mobile-new-${si}`"
                  :class="seg.class"
                >
                  {{ seg.text }}
                </span>
              </p>
            </div>
          </template>
        </article>
      </div>

      <div v-if="hasMoreParagraphs" class="load-more-row">
        <button type="button" class="load-more-button" data-testid="docx-load-more" @click="loadMoreParagraphs">
          再显示 {{ remainingParagraphCount }} 段
        </button>
      </div>
      </section>

      <section v-if="visibleTables.length" class="section-block">
        <div class="section-head">
          <h4>表格变更</h4>
          <span>{{ visibleTables.length }} / {{ tables.length }} 个表格</span>
        </div>
        <div class="table-grid">
          <article v-for="table in visibleTables" :key="table.table_index" class="diff-card">
            <div class="card-topline">
              <strong>表格 #{{ table.table_index + 1 }}</strong>
              <el-tag v-if="table.structure_changed" type="warning" size="small">结构变化</el-tag>
            </div>
            <div class="shape-row">
              <span>{{ tableShapeLabel(table, 'old') }}</span>
              <el-icon><ArrowRight /></el-icon>
              <span>{{ tableShapeLabel(table, 'new') }}</span>
            </div>

            <div class="excel-compare">
              <div class="excel-pane">
                <div class="excel-title">旧表</div>
                <div class="excel-diff-table">
                  <div class="excel-row excel-row--head">
                    <span class="excel-corner"></span>
                    <span v-for="colIndex in tableColCount(table)" :key="`old-head-${colIndex}`" class="excel-col-head">
                      {{ colLabel(colIndex - 1) }}
                    </span>
                  </div>
                  <div v-for="rowIndex in tableRowCount(table, 'old')" :key="`old-row-${rowIndex}`" class="excel-row">
                    <span class="excel-row-head">{{ rowIndex }}</span>
                    <span
                      v-for="colIndex in tableColCount(table)"
                      :key="`old-cell-${rowIndex}-${colIndex}`"
                      class="excel-cell"
                      :class="cellClass(table, 'old', rowIndex - 1, colIndex - 1)"
                    >
                      {{ cellValue(table, 'old', rowIndex - 1, colIndex - 1) }}
                    </span>
                  </div>
                </div>
              </div>

              <div class="excel-pane">
                <div class="excel-title">新表</div>
                <div class="excel-diff-table">
                  <div class="excel-row excel-row--head">
                    <span class="excel-corner"></span>
                    <span v-for="colIndex in tableColCount(table)" :key="`new-head-${colIndex}`" class="excel-col-head">
                      {{ colLabel(colIndex - 1) }}
                    </span>
                  </div>
                  <div v-for="rowIndex in tableRowCount(table, 'new')" :key="`new-row-${rowIndex}`" class="excel-row">
                    <span class="excel-row-head">{{ rowIndex }}</span>
                    <span
                      v-for="colIndex in tableColCount(table)"
                      :key="`new-cell-${rowIndex}-${colIndex}`"
                      class="excel-cell"
                      :class="cellClass(table, 'new', rowIndex - 1, colIndex - 1)"
                    >
                      {{ cellValue(table, 'new', rowIndex - 1, colIndex - 1) }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="cellChanges(table).length" class="cell-list">
              <div
                v-for="cell in cellChanges(table).slice(0, 20)"
                :key="`${cell.row}-${cell.col}`"
                class="cell-item"
                :class="`cell-item--${cell.change_type || 'replace'}`"
              >
                <span class="cell-pos">{{ cell.row }},{{ cell.col }}</span>
                <template v-if="cell.change_type === 'insert'">
                  <span class="cell-value cell-value--new">+ {{ cell.new_value || '(新增)' }}</span>
                </template>
                <template v-else-if="cell.change_type === 'delete'">
                  <span class="cell-value cell-value--old">- {{ cell.old_value || '(删除)' }}</span>
                </template>
                <template v-else>
                  <span class="cell-value cell-value--old">{{ cell.old_value || '(空)' }}</span>
                  <el-icon><ArrowRight /></el-icon>
                  <span class="cell-value cell-value--new">{{ cell.new_value || '(空)' }}</span>
                </template>
              </div>
              <div v-if="cellChanges(table).length > 20" class="more-hint">
                还有 {{ cellChanges(table).length - 20 }} 处未展开
              </div>
            </div>

            <div v-if="table.added_rows?.length || table.deleted_rows?.length || table.added_cols?.length || table.deleted_cols?.length" class="tag-row">
              <el-tag v-for="row in table.added_rows || []" :key="`ar-${row}`" type="success" effect="plain" size="small">+ 行 {{ rowLabel(row) }}</el-tag>
              <el-tag v-for="row in table.deleted_rows || []" :key="`dr-${row}`" type="danger" effect="plain" size="small">- 行 {{ rowLabel(row) }}</el-tag>
              <el-tag v-for="col in table.added_cols || []" :key="`ac-${col}`" type="success" effect="plain" size="small">+ 列 {{ colLabel(col) }}</el-tag>
              <el-tag v-for="col in table.deleted_cols || []" :key="`dc-${col}`" type="danger" effect="plain" size="small">- 列 {{ colLabel(col) }}</el-tag>
            </div>
            <div v-if="table.row_moves?.length || table.col_moves?.length" class="tag-row">
              <el-tag v-for="(move, mi) in table.row_moves || []" :key="`rm-${mi}`" type="warning" effect="plain" size="small">
                {{ rowMoveLabel(move) }}
              </el-tag>
              <el-tag v-for="(move, mi) in table.col_moves || []" :key="`cm-${mi}`" type="warning" effect="plain" size="small">
                {{ colMoveLabel(move) }}
              </el-tag>
            </div>
          </article>
        </div>
      </section>

      <section v-if="hasVisibleImageChanges" class="section-block">
        <div class="section-head">
          <h4>图片变更</h4>
          <span>{{ visibleImageCount }} / {{ imageCount }} 处</span>
        </div>
        <div class="image-grid">
          <div v-for="img in visibleAddedImageItems" :key="`a-${imageKey(img)}`" class="image-item image-item--add image-card">
            <div class="image-card-head">
              <el-icon><Plus /></el-icon>
              <strong>新增图片</strong>
              <span>{{ imageName(img) }}</span>
            </div>
            <div class="image-thumb">
              <img v-if="img.data_uri" :src="img.data_uri" :alt="imageName(img)" loading="lazy" />
              <span v-else>无缩略图</span>
            </div>
            <div class="image-meta">
              <span>hash {{ img.short_hash || shortHash(img.sha256) || '未知' }}</span>
              <span>{{ imageSize(img) }}</span>
              <span>{{ imagePosition(img) }}</span>
            </div>
          </div>
          <div v-for="img in visibleDeletedImageItems" :key="`d-${imageKey(img)}`" class="image-item image-item--del image-card">
            <div class="image-card-head">
              <el-icon><Delete /></el-icon>
              <strong>删除图片</strong>
              <span>{{ imageName(img) }}</span>
            </div>
            <div class="image-thumb image-thumb--deleted">删除占位</div>
            <div class="image-meta">
              <span>hash {{ img.short_hash || shortHash(img.sha256) || '未知' }}</span>
              <span>{{ imageSize(img) }}</span>
              <span>{{ imagePosition(img) }}</span>
            </div>
          </div>
          <div v-for="img in visibleReplacedImageItems" :key="`r-${img.filename || imageKey(img.new)}`" class="image-item image-item--replace image-card image-compare-card--replaced">
            <div class="image-card-head">
              <el-icon><Refresh /></el-icon>
              <strong>图片替换</strong>
              <span>{{ img.filename || imageName(img.new) }}</span>
            </div>
            <div class="image-compare-grid">
              <div class="image-compare-pane">
                <span class="compare-label compare-label--old">旧图</span>
                <div class="image-thumb">
                  <img v-if="img.old?.data_uri" :src="img.old.data_uri" :alt="imageName(img.old)" loading="lazy" />
                  <span v-else>无缩略图</span>
                </div>
                <div class="image-meta image-meta--compact">
                  <span>hash {{ img.old?.short_hash || shortHash(img.old?.sha256) || '未知' }}</span>
                  <span>{{ imageSize(img.old) }}</span>
                </div>
              </div>
              <div class="image-compare-pane">
                <span class="compare-label compare-label--new">新图</span>
                <div class="image-thumb">
                  <img v-if="img.new?.data_uri" :src="img.new.data_uri" :alt="imageName(img.new)" loading="lazy" />
                  <span v-else>无缩略图</span>
                </div>
                <div class="image-meta image-meta--compact">
                  <span>hash {{ img.new?.short_hash || shortHash(img.new?.sha256) || '未知' }}</span>
                  <span>{{ imageSize(img.new) }}</span>
                </div>
              </div>
            </div>
            <small>{{ formatBytes(img.old_size) }} → {{ formatBytes(img.new_size) }}</small>
          </div>
          <div v-for="img in visibleResizedImageItems" :key="`z-${img.filename || imageKey(img.new)}`" class="image-item image-item--resize image-card">
            <div class="image-card-head">
              <el-icon><Refresh /></el-icon>
              <strong>尺寸调整</strong>
              <span>{{ img.filename || imageName(img.new) }}</span>
            </div>
            <div class="image-thumb">
              <img v-if="(img.new || img.old)?.data_uri" :src="(img.new || img.old).data_uri" :alt="imageName(img.new || img.old)" loading="lazy" />
              <span v-else>无缩略图</span>
            </div>
            <div class="image-meta">
              <span>{{ formatImageSizePair(img.old_width_cm, img.old_height_cm) }}</span>
              <span>→</span>
              <span>{{ formatImageSizePair(img.new_width_cm, img.new_height_cm) }}</span>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import { ArrowRight, Plus, Delete, Refresh } from '@element-plus/icons-vue'

const props = defineProps({
  diffData: { type: Object, default: () => ({}) }
})

const oldPanelRef = ref(null)
const newPanelRef = ref(null)
const paragraphShellRef = ref(null)
const flashingIndex = ref(-1)
const searchQuery = ref('')
const activeFilter = ref('all')
const paragraphRenderLimit = ref(300)
const currentChangeCursor = ref(-1)
let syncing = false
let flashTimer = null

const filterOptions = [
  { id: 'all', label: '全部' },
  { id: 'text', label: '文字' },
  { id: 'table', label: '表格' },
  { id: 'image', label: '图片' },
  { id: 'insert', label: '新增' },
  { id: 'delete', label: '删除' },
  { id: 'modified', label: '修改' },
  { id: 'move', label: '移动' },
  { id: 'replace', label: '替换' },
  { id: 'resize', label: '尺寸' }
]

const paragraphs = computed(() => props.diffData?.paragraphs || props.diffData?.text || props.diffData?.changes?.text || [])
const tables = computed(() => props.diffData?.tables || props.diffData?.changes?.tables || [])
const imageDiffs = computed(() => props.diffData?.images || props.diffData?.changes?.images || null)
const normalizedSearch = computed(() => searchQuery.value.trim().toLowerCase())
const counts = computed(() => ({
  insert: paragraphs.value.filter((p) => getOp(p) === 'insert').length,
  delete: paragraphs.value.filter((p) => getOp(p) === 'delete').length,
  modified: paragraphs.value.filter((p) => getOp(p) === 'modified').length,
  move: uniqueMoveCount(paragraphs.value)
}))
const addedImageItems = computed(() => normalizeImageList(imageDiffs.value?.added, imageDiffs.value?.added_items, imageDiffs.value?.added_list))
const deletedImageItems = computed(() => normalizeImageList(imageDiffs.value?.deleted, imageDiffs.value?.deleted_items, imageDiffs.value?.deleted_list))
const replacedImageItems = computed(() => normalizeImageList(imageDiffs.value?.replaced, imageDiffs.value?.replaced_list))
const resizedImageItems = computed(() => normalizeImageList(imageDiffs.value?.resized, imageDiffs.value?.resized_list))
const imageCount = computed(() => addedImageItems.value.length + deletedImageItems.value.length + replacedImageItems.value.length + resizedImageItems.value.length)
const visibleParagraphs = computed(() => paragraphs.value.filter((para) => paragraphMatchesFilter(para) && paragraphMatchesSearch(para)))
const renderedParagraphs = computed(() => visibleParagraphs.value.slice(0, paragraphRenderLimit.value))
const changedParagraphIndexes = computed(() => renderedParagraphs.value
  .map((para, index) => (getOp(para) === 'equal' ? -1 : index))
  .filter((index) => index >= 0))
const visibleTables = computed(() => tables.value.filter((table) => tableMatchesFilter(table) && tableMatchesSearch(table)))
const visibleAddedImageItems = computed(() => filterImageGroup(addedImageItems.value, 'insert'))
const visibleDeletedImageItems = computed(() => filterImageGroup(deletedImageItems.value, 'delete'))
const visibleReplacedImageItems = computed(() => filterImageGroup(replacedImageItems.value, 'replace'))
const visibleResizedImageItems = computed(() => filterImageGroup(resizedImageItems.value, 'resize'))
const visibleImageCount = computed(() => visibleAddedImageItems.value.length + visibleDeletedImageItems.value.length + visibleReplacedImageItems.value.length + visibleResizedImageItems.value.length)
const hasImageChanges = computed(() => imageCount.value > 0)
const hasVisibleImageChanges = computed(() => visibleImageCount.value > 0)
const hasAnyChanges = computed(() => paragraphs.value.length > 0 || tables.value.length > 0 || hasImageChanges.value)
const hasVisibleTextChanges = computed(() => visibleParagraphs.value.length > 0)
const hasVisibleChanges = computed(() => hasVisibleTextChanges.value || visibleTables.value.length > 0 || hasVisibleImageChanges.value)
const showTextPanel = computed(() => hasVisibleTextChanges.value && ['all', 'text', 'insert', 'delete', 'modified', 'move', 'replace'].includes(activeFilter.value))
const remainingParagraphCount = computed(() => Math.max(0, visibleParagraphs.value.length - renderedParagraphs.value.length))
const hasMoreParagraphs = computed(() => remainingParagraphCount.value > 0)

watch(paragraphs, () => {
  flashingIndex.value = -1
})

watch([paragraphs, activeFilter, searchQuery], () => {
  paragraphRenderLimit.value = 300
  flashingIndex.value = -1
  currentChangeCursor.value = -1
})

function setFilter(filterId) {
  activeFilter.value = filterId
  flashingIndex.value = -1
}

function loadMoreParagraphs() {
  paragraphRenderLimit.value += 300
}

function textForSearch(value) {
  if (value === undefined || value === null) return ''
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value)
  try {
    return JSON.stringify(value)
  } catch {
    return ''
  }
}

function matchesSearch(value) {
  const query = normalizedSearch.value
  if (!query) return true
  return textForSearch(value).toLowerCase().includes(query)
}

function isSearchHit(value) {
  return Boolean(normalizedSearch.value) && matchesSearch(value)
}

function paragraphMatchesSearch(para) {
  return matchesSearch([
    para?.old_text,
    para?.new_text,
    para?.text,
    para?.metadata?.description,
    para?.char_diffs
  ])
}

function paragraphMatchesFilter(para) {
  const filter = activeFilter.value
  const op = getOp(para)
  if (filter === 'all' || filter === 'text') return true
  if (filter === 'replace') return op === 'modified'
  if (['insert', 'delete', 'modified', 'move'].includes(filter)) return op === filter
  return false
}

function tableMatchesSearch(table) {
  return matchesSearch(table)
}

function hasCellType(table, types) {
  return cellChanges(table).some((cell) => types.includes(String(cell?.change_type || 'replace').toLowerCase()))
}

function tableMatchesFilter(table) {
  const filter = activeFilter.value
  if (filter === 'all' || filter === 'table') return true
  if (filter === 'replace' || filter === 'modified') return hasCellType(table, ['replace', 'modified', 'change']) || cellChanges(table).length > 0
  if (filter === 'move') return Boolean(table?.row_moves?.length || table?.col_moves?.length)
  if (filter === 'insert') return Boolean(table?.added_rows?.length || table?.added_cols?.length) || hasCellType(table, ['insert', 'add', 'added'])
  if (filter === 'delete') return Boolean(table?.deleted_rows?.length || table?.deleted_cols?.length) || hasCellType(table, ['delete', 'deleted', 'remove', 'removed'])
  return false
}

function filterImageGroup(items, groupOp) {
  const filter = activeFilter.value
  const opMatch = filter === 'all' || filter === 'image' || filter === groupOp || (filter === 'modified' && (groupOp === 'replace' || groupOp === 'resize'))
  if (!opMatch) return []
  return (items || []).filter((item) => matchesSearch(item))
}

function syncScroll(source, target) {
  if (syncing || !source.value || !target.value) return
  syncing = true
  const sourceRange = Math.max(1, source.value.scrollHeight - source.value.clientHeight)
  const targetRange = Math.max(1, target.value.scrollHeight - target.value.clientHeight)
  const ratio = source.value.scrollTop / sourceRange
  target.value.scrollTop = ratio * targetRange
  nextTick(() => {
    syncing = false
  })
}

function onOldScroll() {
  syncScroll(oldPanelRef, newPanelRef)
}

function onNewScroll() {
  syncScroll(newPanelRef, oldPanelRef)
}

function getOp(para) {
  const value = String(para?.change_type || para?.op || '').toLowerCase()
  if (value === 'insert') return 'insert'
  if (value === 'delete') return 'delete'
  if (value === 'move' || value === 'moved') return 'move'
  if (value === 'replace' || value === 'modified' || value === 'modify') return 'modified'
  return 'equal'
}

function opLabel(para) {
  const op = getOp(para)
  return {
    insert: '新增',
    delete: '删除',
    modified: '修改',
    move: '移动',
    equal: '相同'
  }[op] || '变更'
}

function getOldClass(para) {
  const op = getOp(para)
  if (op === 'delete') return 'diff-deleted'
  if (op === 'move') return 'diff-moved'
  if (op === 'modified') return 'diff-modified-old'
  if (op === 'insert') return 'diff-placeholder'
  return 'diff-equal'
}

function getNewClass(para) {
  const op = getOp(para)
  if (op === 'insert') return 'diff-added'
  if (op === 'move') return 'diff-moved'
  if (op === 'modified') return 'diff-modified-new'
  if (op === 'delete') return 'diff-placeholder'
  return 'diff-equal'
}

function uniqueMoveCount(items) {
  const ids = new Set()
  for (const item of items || []) {
    if (getOp(item) !== 'move') continue
    const id = item?.metadata?.move_id ?? `${item?.metadata?.from}-${item?.metadata?.to}`
    ids.add(id)
  }
  return ids.size
}

function formatMoveFrom(para) {
  const value = para?.metadata?.from
  return Number.isFinite(Number(value)) ? `第 ${Number(value) + 1} 段` : '原位置'
}

function formatMoveTo(para) {
  const value = para?.metadata?.to
  return Number.isFinite(Number(value)) ? `第 ${Number(value) + 1} 段` : '新位置'
}

function moveDescription(para) {
  if (para?.metadata?.description) return para.metadata.description
  return `${formatMoveFrom(para)}移动到${formatMoveTo(para)}之后`
}

function formatBytes(value) {
  const bytes = Number(value || 0)
  if (!bytes) return '未知大小'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function tableRows(table, side) {
  return side === 'old' ? (table?.old_rows || []) : (table?.new_rows || [])
}

function cellChanges(table) {
  return Array.isArray(table?.cell_changes) ? table.cell_changes : []
}

function tableRowCount(table, side) {
  const shape = side === 'old' ? table?.old_shape : table?.new_shape
  return Math.max(Number(shape?.[0] || 0), tableRows(table, side).length, 1)
}

function tableColCount(table) {
  const rows = [...(table?.old_rows || []), ...(table?.new_rows || [])]
  const rowWidth = rows.reduce((max, row) => Math.max(max, Array.isArray(row) ? row.length : 0), 0)
  return Math.max(Number(table?.old_shape?.[1] || 0), Number(table?.new_shape?.[1] || 0), rowWidth, 1)
}

function tableShapeLabel(table, side) {
  const shape = side === 'old' ? table?.old_shape : table?.new_shape
  const rows = Math.max(Number(shape?.[0] || 0), tableRows(table, side).length)
  const rowWidth = tableRows(table, side).reduce((max, row) => Math.max(max, Array.isArray(row) ? row.length : 0), 0)
  const cols = Math.max(Number(shape?.[1] || 0), rowWidth)
  return `${rows} x ${cols}`
}

function cellValue(table, side, row, col) {
  const value = tableRows(table, side)?.[row]?.[col]
  return value === undefined || value === null || value === '' ? '·' : value
}

function cellChangeAt(table, row, col) {
  return cellChanges(table).find((cell) => Number(cell.row) === row && Number(cell.col) === col)
}

function cellClass(table, side, row, col) {
  const change = cellChangeAt(table, row, col)
  const type = String(change?.change_type || '').toLowerCase()
  return {
    'excel-cell--replace': type === 'replace' || type === 'modified',
    'excel-cell--insert': type === 'insert' && side === 'new',
    'excel-cell--delete': type === 'delete' && side === 'old',
    'excel-cell--muted': (type === 'insert' && side === 'old') || (type === 'delete' && side === 'new'),
    'excel-cell--row-move': (table?.row_moves || []).some((move) => Number(move.from) === row || Number(move.to) === row),
    'excel-cell--col-move': (table?.col_moves || []).some((move) => Number(move.from) === col || Number(move.to) === col)
  }
}

function colLabel(index) {
  let n = Number(index) + 1
  let label = ''
  while (n > 0) {
    const rem = (n - 1) % 26
    label = String.fromCharCode(65 + rem) + label
    n = Math.floor((n - 1) / 26)
  }
  return label || 'A'
}

function rowLabel(index) {
  const value = Number(index)
  return Number.isFinite(value) ? String(value + 1) : String(index || '?')
}

function rowMoveLabel(move) {
  return `行 ${Number(move.from) + 1} → ${Number(move.to) + 1}`
}

function colMoveLabel(move) {
  return `列 ${colLabel(move.from)} → ${colLabel(move.to)}`
}

function normalizeImageList(...sources) {
  for (const source of sources) {
    if (Array.isArray(source) && source.length) {
      return source.map((item) => (typeof item === 'string' ? { display_name: item } : item))
    }
  }
  for (const source of sources) {
    if (typeof source === 'number' && source > 0) {
      return Array.from({ length: source }, (_, index) => ({ display_name: `图片 ${index + 1}` }))
    }
  }
  return []
}

function imageName(image) {
  return image?.display_name || image?.filename || image?.rId || '未命名图片'
}

function imageKey(image) {
  return image?.position_key || image?.sha256 || image?.short_hash || imageName(image)
}

function shortHash(hash) {
  return hash ? String(hash).slice(0, 12) : ''
}

function imageSize(image) {
  return formatImageSizePair(image?.width_cm, image?.height_cm)
}

function formatImageSizePair(width, height) {
  const w = Number(width)
  const h = Number(height)
  if (!Number.isFinite(w) || !Number.isFinite(h) || (!w && !h)) return '未知尺寸'
  return `${w.toFixed(2)} × ${h.toFixed(2)} cm`
}

function imagePosition(image) {
  if (image?.paragraph_index !== undefined && image?.paragraph_index !== null) {
    return `第 ${Number(image.paragraph_index) + 1} 段`
  }
  return image?.position_key || '未知位置'
}

function renderCharDiffs(charDiffs, side) {
  if (!Array.isArray(charDiffs) || !charDiffs.length) return []

  return charDiffs
    .map((diff) => {
      const type = String(diff?.type || '').toLowerCase()
      const text = diff?.text || ''
      if (type === 'equal') return { text, class: '' }
      if (type === 'delete' && side === 'old') return { text, class: 'char-deleted' }
      if (type === 'insert' && side === 'new') return { text, class: 'char-added' }
      return null
    })
    .filter(Boolean)
}

async function jumpToNextChange() {
  const indexes = changedParagraphIndexes.value
  if (!indexes.length) return
  currentChangeCursor.value = (currentChangeCursor.value + 1) % indexes.length
  await scrollToHunk(indexes[currentChangeCursor.value])
}

async function scrollToHunk(index) {
  await nextTick()
  const shell = paragraphShellRef.value
  const oldContainer = oldPanelRef.value
  const newContainer = newPanelRef.value
  const oldLine = oldContainer?.querySelector(`[data-hunk="${index}"]`)
  const newLine = newContainer?.querySelector(`[data-hunk="${index}"]`)
  const mobileLine = shell?.querySelector(`.mobile-diff-card[data-hunk="${index}"]`)

  if (shell) {
    const para = renderedParagraphs.value[index]
    const op = getOp(para)
    const isMobile = typeof window !== 'undefined' && window.innerWidth <= 640
    const desktopLine = oldLine || newLine
    const targetLine = isMobile ? (mobileLine || desktopLine) : (desktopLine || mobileLine)

    if (targetLine) {
      const shellRect = shell.getBoundingClientRect()
      const targetRect = targetLine.getBoundingClientRect()
      const stickyHead = shell.querySelector('.paragraph-shell-head')
      const headHeight = stickyHead?.getBoundingClientRect?.().height || 56
      const offset = targetRect.top - shellRect.top
      shell.scrollTop = Math.max(0, shell.scrollTop + offset - headHeight - 12)
    }
  }

  if (flashTimer) clearTimeout(flashTimer)
  flashingIndex.value = index
  flashTimer = setTimeout(() => {
    flashingIndex.value = -1
  }, 1600)
}

defineExpose({ scrollToHunk })
</script>

<style scoped>
.docx-diff {
  width: 100%;
}

.diff-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
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

.toolbar-controls {
  flex: 1 1 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.filter-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.filter-chip {
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 999px;
  background: rgba(248, 250, 252, 0.86);
  color: #475569;
  padding: 6px 11px;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  transition: transform 0.16s ease, background-color 0.16s ease, border-color 0.16s ease, color 0.16s ease;
}

.filter-chip:hover {
  transform: translateY(-1px);
  border-color: rgba(59, 130, 246, 0.28);
  color: #1d4ed8;
}

.filter-chip--active {
  border-color: rgba(37, 99, 235, 0.36);
  background: rgba(219, 234, 254, 0.72);
  color: #1e40af;
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.08);
}

.search-box {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary, #64748b);
  font-size: 12px;
  white-space: nowrap;
}

.diff-search-input {
  width: min(280px, 44vw);
  height: 32px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: var(--text-primary, #1f2937);
  outline: none;
  padding: 0 12px;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.diff-search-input:focus {
  border-color: rgba(37, 99, 235, 0.46);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
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
  background: rgba(220, 252, 231, 0.62);
  color: #166534;
}

.stat-pill--del {
  background: rgba(254, 226, 226, 0.58);
  color: #991b1b;
}

.stat-pill--mod {
  background: rgba(254, 243, 199, 0.62);
  color: #92400e;
}

.stat-pill--move {
  background: rgba(224, 231, 255, 0.64);
  color: #3730a3;
}

.paragraph-diff-shell {
  display: grid;
  gap: 12px;
  min-width: 0;
  max-height: min(72vh, 820px);
  margin-bottom: 12px;
  padding: 12px;
  overflow-y: auto;
  overscroll-behavior: contain;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 16px;
  background:
    linear-gradient(135deg, rgba(248, 250, 252, 0.96), rgba(255, 255, 255, 0.92));
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
  scrollbar-gutter: stable;
}

.paragraph-shell-head {
  position: sticky;
  top: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 2px 0 10px;
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.98) 0%, rgba(248, 250, 252, 0.96) 74%, rgba(248, 250, 252, 0) 100%);
  backdrop-filter: blur(10px);
}

.paragraph-shell-head h4 {
  margin: 0;
  color: var(--text-primary, #1f2937);
  font-size: 15px;
  font-weight: 800;
}

.paragraph-shell-head p {
  margin: 3px 0 0;
  color: var(--text-secondary, #64748b);
  font-size: 12px;
}

.next-change-button {
  flex: 0 0 auto;
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid rgba(37, 99, 235, 0.22);
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.14s ease, background-color 0.14s ease, border-color 0.14s ease;
}

.next-change-button:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(37, 99, 235, 0.42);
  background: #dbeafe;
}

.next-change-button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.diff-container {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.mobile-diff-list {
  display: none;
}

.diff-panel {
  min-width: 0;
  border: 1px solid var(--border-color-light, #e5e7eb);
  border-radius: 8px;
  background: var(--bg-secondary, #fff);
  overflow: hidden;
  /* override global .diff-panel that sets max-height:70vh / padding:16px / flex:1 */
  max-height: none;
  padding: 0;
  flex: none;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-color-light, #e5e7eb);
  background: var(--bg-tertiary, #f8fafc);
  font-size: 13px;
  font-weight: 700;
}

.panel-meta {
  font-weight: 400;
  color: var(--text-secondary, #64748b);
}

.panel-body {
  max-height: none;
  overflow: visible;
  padding: 10px 0 16px;
}

.diff-line {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  min-height: 42px;
  padding: 8px 12px;
  scroll-margin-top: 64px;
  transition: background-color 0.2s ease, box-shadow 0.2s ease;
}

.line-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 24px;
  margin-top: 2px;
  border-radius: 999px;
  background: var(--bg-tertiary, #f8fafc);
  color: var(--text-tertiary, #94a3b8);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.line-content {
  min-width: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.75;
}

.diff-equal {
  color: var(--text-primary, #1f2937);
}

.diff-deleted {
  background: rgba(254, 226, 226, 0.5);
  color: #b91c1c;
}

.diff-added {
  background: rgba(220, 252, 231, 0.52);
  color: #166534;
}

.diff-modified-old,
.diff-modified-new {
  background: rgba(254, 243, 199, 0.52);
}

.diff-moved {
  background: rgba(224, 231, 255, 0.56);
  color: #3730a3;
}

.move-badge {
  display: inline-flex;
  align-items: center;
  margin-right: 8px;
  padding: 2px 7px;
  border-radius: 999px;
  background: #c7d2fe;
  color: #312e81;
  font-size: 11px;
  font-weight: 700;
}

.diff-placeholder {
  min-height: 18px;
}

.char-deleted {
  background: #fecaca;
  color: #7f1d1d;
  text-decoration: line-through;
  border-radius: 4px;
  padding: 0 2px;
}

.char-added {
  background: #bbf7d0;
  color: #14532d;
  border-radius: 4px;
  padding: 0 2px;
}

.hunk-flash {
  box-shadow: inset 0 0 0 2px rgba(59, 130, 246, 0.4);
  background: rgba(59, 130, 246, 0.06) !important;
}

.search-hit {
  box-shadow: inset 3px 0 0 rgba(37, 99, 235, 0.45);
}

.filter-empty {
  display: grid;
  place-items: center;
  min-height: 120px;
  margin: 12px 0;
  border: 1px dashed rgba(148, 163, 184, 0.35);
  border-radius: 10px;
  background: rgba(248, 250, 252, 0.72);
  color: var(--text-secondary, #64748b);
  font-size: 13px;
}

.load-more-row {
  display: flex;
  justify-content: center;
  margin: 12px 0 4px;
}

.load-more-button {
  border: 1px solid rgba(37, 99, 235, 0.22);
  border-radius: 999px;
  background: rgba(239, 246, 255, 0.76);
  color: #1d4ed8;
  cursor: pointer;
  font-size: 13px;
  padding: 8px 16px;
  transition: transform 0.16s ease, box-shadow 0.16s ease;
}

.load-more-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.1);
}

.section-block {
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

.diff-card {
  border: 1px solid var(--border-color-light, #e5e7eb);
  border-radius: 8px;
  background: var(--bg-secondary, #fff);
  padding: 14px;
}

.card-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.shape-row {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary, #64748b);
  font-size: 12px;
  margin-bottom: 10px;
}

.excel-compare {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.excel-pane {
  min-width: 0;
}

.excel-title {
  margin-bottom: 6px;
  color: var(--text-secondary, #64748b);
  font-size: 12px;
  font-weight: 700;
}

.excel-diff-table {
  overflow: auto;
  border: 1px solid var(--border-color-light, #e5e7eb);
  border-radius: 8px;
  background: #fff;
}

.excel-row {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(96px, 1fr);
  min-width: max-content;
}

.excel-corner,
.excel-row-head,
.excel-col-head,
.excel-cell {
  min-height: 32px;
  padding: 7px 9px;
  border-right: 1px solid rgba(226, 232, 240, 0.95);
  border-bottom: 1px solid rgba(226, 232, 240, 0.95);
  font-size: 12px;
  line-height: 1.45;
}

.excel-corner,
.excel-row-head,
.excel-col-head {
  background: #f8fafc;
  color: #64748b;
  font-weight: 700;
  text-align: center;
}

.excel-corner,
.excel-row-head {
  width: 42px;
  min-width: 42px;
}

.excel-cell--replace {
  background: #fffbeb;
  color: #92400e;
  box-shadow: inset 0 0 0 1px rgba(245, 158, 11, 0.25);
}

.excel-cell--insert {
  background: #f0fdf4;
  color: #166534;
}

.excel-cell--delete {
  background: #fff1f2;
  color: #b91c1c;
  text-decoration: line-through;
}

.excel-cell--muted {
  background: #f8fafc;
  color: #94a3b8;
}

.excel-cell--row-move,
.excel-cell--col-move {
  border-bottom-color: rgba(99, 102, 241, 0.32);
}

.cell-list {
  display: grid;
  gap: 6px;
}

.cell-item {
  display: grid;
  grid-template-columns: 70px minmax(0, 1fr) auto minmax(0, 1fr);
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

.cell-item--insert {
  background: #f0fdf4;
}

.cell-item--delete {
  background: #fff1f2;
}

.more-hint {
  margin-top: 4px;
  color: var(--text-tertiary, #94a3b8);
  font-size: 12px;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.image-item {
  display: grid;
  gap: 8px;
  padding: 12px;
  border-radius: 8px;
  font-size: 12px;
}

.image-item--add {
  background: #f0fdf4;
  color: #166534;
}

.image-item--del {
  background: #fff1f2;
  color: #b91c1c;
  text-decoration: line-through;
}

.image-item--replace {
  background: #fffbeb;
  color: #92400e;
}

.image-item--resize {
  background: #eef2ff;
  color: #3730a3;
}

.image-item strong {
  font-weight: 700;
}

.image-item small {
  color: currentColor;
  opacity: 0.75;
}

.image-card-head {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.image-card-head span:last-child {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.image-thumb {
  display: grid;
  place-items: center;
  min-height: 118px;
  border: 1px dashed rgba(100, 116, 139, 0.28);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
  color: #94a3b8;
  overflow: hidden;
}

.image-thumb img {
  display: block;
  width: 100%;
  max-height: 180px;
  object-fit: contain;
}

.image-thumb--deleted {
  background: repeating-linear-gradient(-45deg, #fff5f5, #fff5f5 10px, #ffe4e1 10px, #ffe4e1 20px);
  color: #b91c1c;
  font-weight: 700;
}

.image-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  color: currentColor;
  opacity: 0.86;
}

.image-meta span {
  padding: 3px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.58);
}

.image-meta--compact {
  margin-top: 6px;
}

.image-compare-card--replaced {
  grid-column: span 2;
}

.image-compare-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.compare-label {
  display: inline-flex;
  margin-bottom: 6px;
  padding: 3px 7px;
  border-radius: 999px;
  font-weight: 700;
}

.compare-label--old {
  background: #fee2e2;
  color: #991b1b;
}

.compare-label--new {
  background: #dcfce7;
  color: #166534;
}

.empty-state {
  padding: 42px 0;
  text-align: center;
}

@media (max-width: 960px) {
  .diff-container,
  .excel-compare,
  .image-grid,
  .image-compare-grid {
    grid-template-columns: 1fr;
  }

  .image-compare-card--replaced {
    grid-column: span 1;
  }
}

@media (max-width: 640px) {
  .diff-toolbar {
    flex-direction: column;
    position: sticky;
    top: 0;
    z-index: 5;
    gap: 10px;
    padding: 12px;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.94);
    backdrop-filter: blur(14px);
  }

  .toolbar-title {
    font-size: 14px;
  }

  .toolbar-subtitle {
    font-size: 12px;
    line-height: 1.45;
  }

  .toolbar-stats {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: nowrap;
    overflow-x: auto;
    padding-bottom: 2px;
    scrollbar-width: none;
  }

  .toolbar-stats::-webkit-scrollbar {
    display: none;
  }

  .toolbar-controls {
    align-items: stretch;
    flex-direction: column;
    gap: 8px;
  }

  .filter-strip {
    flex-wrap: nowrap;
    overflow-x: auto;
    padding-bottom: 2px;
    scrollbar-width: none;
  }

  .filter-strip::-webkit-scrollbar {
    display: none;
  }

  .filter-chip {
    min-height: 32px;
    padding: 0 11px;
  }

  .search-box {
    align-items: stretch;
    flex-direction: column;
    gap: 6px;
  }

  .diff-search-input {
    width: 100%;
  }

  .paragraph-diff-shell {
    max-height: calc(100dvh - 132px);
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: 10px;
    border-radius: 16px;
    -webkit-overflow-scrolling: touch;
  }

  .paragraph-shell-head {
    position: sticky;
    top: 0;
    z-index: 3;
    align-items: stretch;
    flex-direction: column;
    padding: 2px 0 10px;
    background:
      linear-gradient(180deg, rgba(248, 250, 252, 0.98) 0%, rgba(248, 250, 252, 0.94) 76%, rgba(248, 250, 252, 0) 100%);
    backdrop-filter: blur(10px);
  }

  .next-change-button {
    width: 100%;
    min-height: 42px;
  }

  .diff-container {
    display: none;
  }

  .mobile-diff-list {
    display: grid;
    gap: 10px;
  }

  .mobile-diff-card {
    min-width: 0;
    overflow: hidden;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.94);
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
  }

  .mobile-diff-card--insert {
    border-color: rgba(22, 163, 74, 0.24);
    background: #f0fdf4;
  }

  .mobile-diff-card--delete {
    border-color: rgba(220, 38, 38, 0.24);
    background: #fff5f5;
  }

  .mobile-diff-card--modified {
    border-color: rgba(217, 119, 6, 0.26);
    background: #fffbeb;
  }

  .mobile-diff-card--move {
    border-color: rgba(79, 70, 229, 0.24);
    background: #eef2ff;
  }

  .mobile-diff-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 9px 10px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }

  .mobile-line-index {
    color: #64748b;
    font-size: 12px;
    font-weight: 700;
  }

  .mobile-op-badge {
    padding: 3px 8px;
    border-radius: 999px;
    background: rgba(15, 23, 42, 0.06);
    color: #334155;
    font-size: 12px;
    font-weight: 800;
  }

  .mobile-side {
    display: grid;
    gap: 6px;
    padding: 10px;
  }

  .mobile-side + .mobile-side {
    border-top: 1px dashed rgba(148, 163, 184, 0.24);
  }

  .mobile-side-label {
    width: max-content;
    padding: 2px 7px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 800;
  }

  .mobile-side--old .mobile-side-label {
    background: #fee2e2;
    color: #991b1b;
  }

  .mobile-side--new .mobile-side-label {
    background: #dcfce7;
    color: #166534;
  }

  .mobile-side--same .mobile-side-label {
    background: #e2e8f0;
    color: #475569;
  }

  .mobile-side p {
    min-width: 0;
    margin: 0;
    color: #1f2937;
    font-size: 13px;
    line-height: 1.75;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
  }

  .diff-panel,
  .diff-card {
    border-radius: 12px;
  }

  .panel-header {
    padding: 10px 12px;
  }

  .panel-body {
    max-height: min(52vh, 480px);
    padding: 8px 0 12px;
  }

  .diff-line {
    grid-template-columns: 34px minmax(0, 1fr);
    gap: 8px;
    min-height: 36px;
    padding: 7px 8px;
  }

  .line-index {
    width: 24px;
    height: 22px;
    font-size: 10px;
  }

  .line-content {
    font-size: 12px;
    line-height: 1.65;
  }

  .diff-card {
    padding: 12px;
  }

  .excel-row {
    grid-auto-columns: minmax(0, 1fr);
  }

  .excel-compare {
    display: none;
  }

  .excel-corner,
  .excel-row-head,
  .excel-col-head,
  .excel-cell {
    min-height: 30px;
    padding: 6px 7px;
    font-size: 11px;
  }

  .cell-item {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .cell-value {
    white-space: normal;
    overflow-wrap: anywhere;
  }

  .image-thumb {
    min-height: 96px;
  }
}
</style>
