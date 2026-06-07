<template>
  <div class="page-container diff-page">
    <section class="diff-hero">
      <div>
        <el-button text class="back-button" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回项目详情
        </el-button>
        <h1>版本差异</h1>
        <p>{{ filename || '文档版本对比' }}</p>
      </div>
      <div class="hero-meta">
        <el-tag effect="plain">{{ fileTypeLabel }}</el-tag>
        <el-tag type="info" effect="plain">{{ versions.length }} 个版本</el-tag>
      </div>
    </section>

    <div v-loading="loading" class="diff-workbench">
      <el-card v-if="!loading && loadError" shadow="never" class="diff-error-card">
        <el-result icon="warning" title="版本加载失败" :sub-title="loadError">
          <template #extra>
            <el-button type="primary" @click="fetchVersions">重新加载</el-button>
            <el-button @click="goBack">返回项目详情</el-button>
          </template>
        </el-result>
      </el-card>

      <template v-else>
        <el-card shadow="never" class="diff-control-card">
        <div class="version-grid">
          <label class="selector-item">
            <span class="selector-label">旧版本</span>
            <el-select
              v-model="oldVersionId"
              placeholder="选择旧版本"
              filterable
              @change="handleVersionChange"
            >
              <el-option
                v-for="v in versions"
                :key="v.id"
                :label="`v${v.version} - ${formatDate(v.created_at)}`"
                :value="v.id"
              />
            </el-select>
          </label>

          <el-button class="swap-button" :disabled="!hasComparableVersions" @click="swapVersions">
            <el-icon><Sort /></el-icon>
          </el-button>

          <label class="selector-item">
            <span class="selector-label">新版本</span>
            <el-select
              v-model="newVersionId"
              placeholder="选择新版本"
              filterable
              @change="handleVersionChange"
            >
              <el-option
                v-for="v in versions"
                :key="v.id"
                :label="`v${v.version} - ${formatDate(v.created_at)}`"
                :value="v.id"
              />
            </el-select>
          </label>
        </div>

        <div class="control-footer">
          <div class="selection-summary">
            <span>{{ selectedOldVersion ? `v${selectedOldVersion.version}` : '-' }}</span>
            <el-icon><ArrowRight /></el-icon>
            <span>{{ selectedNewVersion ? `v${selectedNewVersion.version}` : '-' }}</span>
          </div>
          <el-button
            type="primary"
            :loading="diffLoading"
            :disabled="!hasComparableVersions"
            @click="fetchDiff"
          >
            <el-icon><Sort /></el-icon>
            对比差异
          </el-button>
        </div>
        </el-card>

      <DiffSummary
        v-if="diffData"
        :summary="diffData.summary"
        :stats="diffData.stats"
        :status="diffData.status"
        :metadata="diffData.metadata"
        :paragraphs="diffData.paragraphs"
        :tables="diffData.tables"
        :images="diffData.images"
        class="diff-summary-card"
        @jump-to="onJumpTo"
      />

      <el-card v-if="diffData" shadow="never" class="diff-result-card">
        <template #header>
          <div class="card-header">
            <div>
              <span>差异对比</span>
              <small>{{ changeCount }} 处变更</small>
            </div>
            <el-button text type="primary" :disabled="!newVersionId" @click="handleDownload">
              <el-icon><Download /></el-icon>
              下载新版本
            </el-button>
          </div>
        </template>

        <DocxDiffView
          v-if="fileType === 'docx' || fileType === 'doc'"
          ref="docxDiffRef"
          :diff-data="diffData"
        />
        <XlsxDiffView
          v-else-if="fileType === 'xlsx' || fileType === 'xls'"
          :diff-data="diffData"
        />
        <PdfDiffView
          v-else-if="fileType === 'pdf'"
          :diff-data="diffData"
        />
        <el-empty v-else description="不支持该文件类型的 Diff 预览" />
      </el-card>

      <el-card v-if="!loading && !diffData && versions.length > 0" shadow="never" class="empty-card">
        <el-empty description="请选择两个版本进行对比" />
      </el-card>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ArrowRight, Download, Sort } from '@element-plus/icons-vue'
import { getFileVersions, downloadVersion } from '@/api/file'
import { getDiffs } from '@/api/diff'
import { formatDate } from '@/utils'
import DiffSummary from '@/components/diff/DiffSummary.vue'
import DocxDiffView from '@/components/diff/DocxDiffView.vue'
import XlsxDiffView from '@/components/diff/XlsxDiffView.vue'
import PdfDiffView from '@/components/diff/PdfDiffView.vue'

const route = useRoute()
const router = useRouter()

const fileId = route.params.fileId
const projectId = route.params.id

const loading = ref(false)
const diffLoading = ref(false)
const versions = ref([])
const oldVersionId = ref(null)
const newVersionId = ref(null)
const diffData = ref(null)
const fileType = ref('')
const filename = ref('')
const loadError = ref('')

const docxDiffRef = ref(null)

const selectedOldVersion = computed(() =>
  versions.value.find((v) => v.id === oldVersionId.value) || null
)

const selectedNewVersion = computed(() =>
  versions.value.find((v) => v.id === newVersionId.value) || null
)

const hasComparableVersions = computed(() =>
  Boolean(oldVersionId.value && newVersionId.value && oldVersionId.value !== newVersionId.value)
)

const fileTypeLabel = computed(() => {
  const map = {
    docx: 'DOCX',
    doc: 'DOC',
    xlsx: 'XLSX',
    xls: 'XLS',
    pdf: 'PDF'
  }
  return map[fileType.value] || '文件'
})

const changeCount = computed(() => {
  if (!diffData.value) return 0
  if (fileType.value === 'xlsx' || fileType.value === 'xls') {
    return diffData.value.stats?.total_cells_modified || 0
  }
  if (fileType.value === 'pdf') {
    const stats = diffData.value.stats || {}
    return (stats.pages_added || 0) + (stats.pages_deleted || 0) + (stats.pages_modified || 0)
  }
  return countDocxChanges(diffData.value)
})

function onJumpTo(index) {
  docxDiffRef.value?.scrollToHunk(index)
}

function goBack() {
  router.push(`/admin/projects/${projectId}`)
}

function handleVersionChange() {
  diffData.value = null
}

function sortVersions(list) {
  return [...list].sort((a, b) => {
    const versionA = Number(a?.version ?? 0)
    const versionB = Number(b?.version ?? 0)
    if (versionA !== versionB) return versionA - versionB

    const timeA = Date.parse(a?.created_at || '') || 0
    const timeB = Date.parse(b?.created_at || '') || 0
    if (timeA !== timeB) return timeA - timeB

    return String(a?.id || '').localeCompare(String(b?.id || ''))
  })
}

function swapVersions() {
  ;[oldVersionId.value, newVersionId.value] = [newVersionId.value, oldVersionId.value]
  diffData.value = null
}

function positiveNumber(value) {
  const number = Number(value)
  return Number.isFinite(number) && number > 0 ? number : 0
}

function countByStats(stats, keys) {
  return keys.reduce((total, key) => total + positiveNumber(stats?.[key]), 0)
}

function fallbackParagraphCount(paragraphs = []) {
  const moveIds = new Set()
  let count = 0
  for (const item of paragraphs || []) {
    const type = String(item?.change_type || item?.op || '').toLowerCase()
    if (['insert', 'delete', 'replace', 'modified'].includes(type)) {
      count += 1
    } else if (type === 'move' || type === 'moved') {
      const id = item?.metadata?.move_id ?? `${item?.metadata?.from}-${item?.metadata?.to}`
      moveIds.add(id)
    }
  }
  return count + moveIds.size
}

function countImageChanges(data) {
  const stats = data?.stats || {}
  const images = data?.images || {}
  const fromStats = countByStats(stats, [
    'image_added',
    'image_deleted',
    'image_replaced',
    'image_resized',
    'images_added',
    'images_deleted',
    'images_replaced',
    'images_resized'
  ])
  if (fromStats > 0) return fromStats
  return ['added', 'deleted', 'replaced', 'resized'].reduce((total, key) => {
    const value = images?.[key]
    if (Array.isArray(value)) return total + value.length
    return total + positiveNumber(value)
  }, 0)
}

function countDocxChanges(data) {
  const stats = data?.stats || {}
  if (positiveNumber(stats.total_changes) > 0) return positiveNumber(stats.total_changes)
  const paragraphStats = countByStats(stats, [
    'text_added',
    'text_deleted',
    'text_modified',
    'text_moves',
    'paragraphs_added',
    'paragraphs_deleted',
    'paragraphs_modified',
    'paragraphs_moved'
  ])
  const paragraphCount = paragraphStats > 0
    ? paragraphStats
    : fallbackParagraphCount(data?.paragraphs || data?.text || [])
  const tableCount = positiveNumber(stats.tables_changed) || (data?.tables || []).length

  return paragraphCount + tableCount + countImageChanges(data)
}

function normalizeDiffPayload(parsed, firstDiff) {
  const payload = parsed || {}
  const changes = payload.changes || {}
  const text = payload.text || changes.text || []
  const paragraphs = payload.paragraphs || text
  const tables = payload.tables || changes.tables || []
  const images = payload.images || changes.images || {}
  const metadata = payload.metadata || changes.metadata || {}
  const stats = payload.stats || changes.stats || {}
  const summary = firstDiff.summary || payload.summary || changes.summary || ''

  return {
    ...payload,
    text,
    paragraphs,
    tables,
    images,
    metadata,
    stats,
    summary,
    diff_type: firstDiff.diff_type || payload.diff_type
  }
}

function getErrorMessage(error, fallback = '操作失败') {
  const data = error?.response?.data
  if (data?.message) return data.message
  if (data?.detail) return data.detail
  if (error?.response?.status) return `请求失败 (${error.response.status})`
  return error?.message || fallback
}

async function fetchVersions() {
  loading.value = true
  loadError.value = ''
  diffData.value = null
  try {
    const data = await getFileVersions(fileId)
    versions.value = sortVersions(data.versions || data || [])
    if (versions.value.length >= 2) {
      oldVersionId.value = versions.value[versions.value.length - 2].id
      newVersionId.value = versions.value[versions.value.length - 1].id
    } else if (versions.value.length === 1) {
      newVersionId.value = versions.value[0].id
    }
    fileType.value = data.file_type || ''
    filename.value = data.filename || ''
    if (hasComparableVersions.value) {
      await fetchDiff()
    }
  } catch (error) {
    versions.value = []
    oldVersionId.value = null
    newVersionId.value = null
    fileType.value = ''
    filename.value = ''
    loadError.value = getErrorMessage(error, '无法加载文件版本')
    ElMessage.error(loadError.value)
  } finally {
    loading.value = false
  }
}

async function fetchDiff() {
  if (!hasComparableVersions.value) {
    ElMessage.warning('请选择两个不同版本')
    return
  }

  diffLoading.value = true
  try {
    const data = await getDiffs(fileId, {
      old_version: oldVersionId.value,
      new_version: newVersionId.value
    })
    const firstDiff = data.diffs?.[0]
    if (!firstDiff) {
      diffData.value = null
      ElMessage.info('未找到对应的差异记录')
      return
    }

    const parsed = typeof firstDiff.diff_data === 'string'
      ? JSON.parse(firstDiff.diff_data)
      : firstDiff.diff_data

    diffData.value = normalizeDiffPayload(parsed, firstDiff)
  } catch (error) {
    diffData.value = null
    ElMessage.error(error?.response?.data?.message || '获取差异失败')
  } finally {
    diffLoading.value = false
  }
}

async function handleDownload() {
  try {
    const blob = await downloadVersion(fileId, newVersionId.value)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename.value || 'download'
    a.click()
    window.URL.revokeObjectURL(url)
  } catch {
    ElMessage.error('下载失败')
  }
}

onMounted(() => {
  fetchVersions()
})
</script>

<style scoped>
.diff-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 24px;
}

.diff-hero {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 16px;
  padding: 18px 20px;
  border: 1px solid var(--border-color-light);
  border-radius: 8px;
  background: linear-gradient(135deg, var(--bg-secondary), var(--surface-muted));
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.diff-hero h1 {
  margin: 8px 0 4px;
  font-size: 22px;
  line-height: 1.2;
}

.diff-hero p {
  margin: 0;
  color: var(--text-secondary);
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.back-button {
  padding: 0;
  height: auto;
  color: var(--text-secondary);
}

.diff-workbench {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.diff-control-card,
.diff-result-card,
.diff-error-card,
.empty-card {
  border-radius: 8px;
}

.diff-error-card {
  border-color: rgba(239, 68, 68, 0.18);
  background:
    linear-gradient(135deg, rgba(254, 242, 242, 0.88), rgba(255, 255, 255, 0.96));
}

.diff-error-card :deep(.el-result) {
  padding: 28px 16px;
}

.version-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 12px;
  align-items: end;
}

.selector-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.selector-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.control-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
}

.selection-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
}

.swap-button {
  align-self: center;
  min-width: 40px;
  padding-inline: 10px;
}

.diff-summary-card {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-weight: 600;
}

.card-header small {
  display: block;
  margin-top: 2px;
  color: var(--text-tertiary);
  font-weight: 400;
}

@media (max-width: 860px) {
  .diff-hero,
  .control-footer {
    align-items: start;
    flex-direction: column;
  }

  .version-grid {
    grid-template-columns: 1fr;
  }

  .swap-button {
    justify-self: center;
  }
}
</style>
