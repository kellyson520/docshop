<template>
  <div v-loading="loading" class="share-diff">
    <!-- 返回按钮 -->
    <el-button text @click="goBack" class="back-btn">
      <el-icon><ArrowLeft /></el-icon>
      返回文件详情
    </el-button>

    <!-- 版本选择 + 操作工具栏 -->
    <el-card shadow="never" class="selector-card">
      <div class="diff-controls">
        <div class="version-selectors">
          <div class="selector-item">
            <span class="selector-label">旧版本:</span>
            <el-select v-model="oldVersionId" placeholder="选择旧版本" class="version-select">
              <el-option v-for="v in versions" :key="v.id" :label="`v${v.version} - ${formatDate(v.created_at)}`" :value="v.id" />
            </el-select>
            <el-dropdown v-if="oldVersionId" trigger="click" @command="(fmt) => downloadVersion(oldVersionId, fmt)">
              <el-button text size="small" type="info"><el-icon><Download /></el-icon> 下载旧版</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="docx">Word 下载</el-dropdown-item>
                  <el-dropdown-item command="pdf">PDF 下载</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <div class="selector-item">
            <span class="selector-label">新版本:</span>
            <el-select v-model="newVersionId" placeholder="选择新版本" class="version-select">
              <el-option v-for="v in versions" :key="v.id" :label="`v${v.version} - ${formatDate(v.created_at)}`" :value="v.id" />
            </el-select>
            <el-dropdown v-if="newVersionId" trigger="click" @command="(fmt) => downloadVersion(newVersionId, fmt)">
              <el-button text size="small" type="success"><el-icon><Download /></el-icon> 下载新版</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="docx">Word 下载</el-dropdown-item>
                  <el-dropdown-item command="pdf">PDF 下载</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
        <el-button type="primary" :loading="diffLoading"
          :disabled="!oldVersionId || !newVersionId || oldVersionId === newVersionId"
          @click="fetchDiff" class="compare-btn">
          <el-icon><Sort /></el-icon> 对比差异
        </el-button>
      </div>
    </el-card>

    <!-- Diff 摘要 -->
    <DiffSummary v-if="diffData" :summary="diffData.summary" :stats="diffData.stats" :paragraphs="diffData.paragraphs" class="summary-card" @jump-to="onJumpTo" />

    <!-- Diff 视图 -->
    <template v-if="diffData">
      <DocxDiffView v-if="fileType === 'docx' || fileType === 'doc'" ref="docxDiffRef" :diff-data="diffData" />
      <XlsxDiffView v-else-if="fileType === 'xlsx' || fileType === 'xls'" :diff-data="diffData" />
      <PdfDiffView v-else-if="fileType === 'pdf'" :diff-data="diffData" />
      <el-empty v-else description="不支持该文件类型的 Diff 预览" />
    </template>

    <!-- 空状态 -->
    <el-card v-if="!loading && !diffData && versions.length > 0" shadow="never" class="empty-card">
      <el-empty description="请选择两个版本进行对比" />
    </el-card>

    <!-- 错误状态 -->
    <el-card v-if="error" shadow="never" class="error-card">
      <el-result icon="error" title="访问失败" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="goBack">返回</el-button>
        </template>
      </el-result>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getShareVersions, getShareDiffs } from '@/api/share'
import { formatDate, downloadViaIframe } from '@/utils'
import DiffSummary from '@/components/diff/DiffSummary.vue'
import DocxDiffView from '@/components/diff/DocxDiffView.vue'
import XlsxDiffView from '@/components/diff/XlsxDiffView.vue'
import PdfDiffView from '@/components/diff/PdfDiffView.vue'

const route = useRoute()
const router = useRouter()

const token = route.params.token
const fileId = route.params.fileId

const loading = ref(false)
const diffLoading = ref(false)
const versions = ref([])
const oldVersionId = ref(null)
const newVersionId = ref(null)
const diffData = ref(null)
const fileType = ref('')
const filename = ref('')
const error = ref('')

const docxDiffRef = ref(null)

function onJumpTo(index) {
  docxDiffRef.value?.scrollToHunk(index)
}

function goBack() {
  router.push(`/s/${token}/files/${fileId}`)
}

async function fetchVersions() {
  loading.value = true
  error.value = ''
  try {
    const data = await getShareVersions(token, fileId)
    versions.value = data.versions || data || []
    if (versions.value.length >= 2) {
      // versions 按 version DESC 排序（最新在前），取最新两个：index 1 = 次新, index 0 = 最新
      oldVersionId.value = versions.value[1]?.id
      newVersionId.value = versions.value[0]?.id
    } else if (versions.value.length === 1) {
      newVersionId.value = versions.value[0].id
    }
    if (versions.value.length > 0) {
      fileType.value = data.file_type || versions.value[0].file_type || ''
    }
    filename.value = data.filename || ''
  } catch {
    error.value = '文件不存在或无权访问'
  } finally {
    loading.value = false
  }
}

async function fetchDiff() {
  if (!oldVersionId.value || !newVersionId.value) {
    ElMessage.warning('请选择两个版本')
    return
  }
  if (oldVersionId.value === newVersionId.value) {
    ElMessage.warning('请选择不同的版本进行对比')
    return
  }
  diffLoading.value = true
  try {
    const data = await getShareDiffs(token, fileId, {
      old_version_id: oldVersionId.value,
      new_version_id: newVersionId.value
    })
    // 提取第一个 diff 并解析 diff_data JSON 字符串
    const firstDiff = data.diffs?.[0]
    if (firstDiff) {
      const parsed = typeof firstDiff.diff_data === 'string'
        ? JSON.parse(firstDiff.diff_data)
        : firstDiff.diff_data
      diffData.value = { ...parsed, summary: firstDiff.summary }
    }
  } finally {
    diffLoading.value = false
  }
}

function downloadVersion(versionId, format) {
  const url = `/api/v1/share/${token}/files/${fileId}/versions/${versionId}/download/${format}`
  downloadViaIframe(url)
}

onMounted(() => {
  fetchVersions()
})
</script>

<style scoped>
.share-diff {
  animation: fadeIn var(--transition-normal);
  padding-bottom: 24px;
}

.back-btn {
  margin-bottom: 16px;
  color: var(--text-secondary, #666666);
  transition: all var(--transition-fast);
}

.back-btn:hover {
  color: var(--color-primary, #1A5276);
  transform: translateX(-4px);
}

.selector-card {
  margin-bottom: 20px;
  border-radius: var(--radius-lg, 12px);
  background-color: var(--bg-secondary, #ffffff);
  border: 1px solid var(--border-color, #e4e7ed);
}

.diff-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.version-selectors {
  display: flex;
  gap: 24px;
  align-items: center;
  flex-wrap: wrap;
}

.selector-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.selector-label {
  color: var(--text-secondary, #666666);
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
}

.version-select {
  width: 220px;
}

.compare-btn {
  border-radius: var(--radius-md, 8px);
  transition: all var(--transition-fast);
}

.compare-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md, 0 4px 6px rgba(0, 0, 0, 0.07));
}

.summary-card {
  margin-bottom: 20px;
}

.empty-card,
.error-card {
  border-radius: var(--radius-lg, 12px);
  background-color: var(--bg-secondary, #ffffff);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式适配 */
@media (max-width: 768px) {
  .diff-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .version-selectors {
    flex-direction: column;
    gap: 12px;
  }

  .selector-item {
    width: 100%;
  }

  .version-select {
    width: 100%;
  }

  .compare-btn {
    width: 100%;
  }
}
</style>
