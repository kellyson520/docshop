<template>
  <div v-loading="loading" class="share-diff">
    <el-button text @click="goBack" class="back-btn">
      <el-icon><ArrowLeft /></el-icon>
      返回文件详情
    </el-button>

    <el-card shadow="never" class="selector-card">
      <div class="diff-controls">
        <div class="version-selectors">
          <div class="selector-item">
            <span class="selector-label">旧版本</span>
            <el-select v-model="oldVersionId" placeholder="选择旧版本" class="version-select">
              <el-option
                v-for="v in versions"
                :key="v.id"
                :label="`v${v.version} - ${formatDate(v.created_at)}`"
                :value="v.id"
              />
            </el-select>
            <el-button
              v-if="allowDownload && oldVersionId && hasSingleDownloadFormat(selectedOldVersion)"
              text
              size="small"
              type="info"
              @click="downloadVersion(oldVersionId)"
            >
              <el-icon><Download /></el-icon>
              {{ getDownloadFormatLabel(getDownloadFormats(selectedOldVersion)[0]) }}
            </el-button>
            <el-dropdown
              v-else-if="allowDownload && oldVersionId && hasMultipleDownloadFormats(selectedOldVersion)"
              trigger="click"
              @command="(fmt) => downloadVersion(oldVersionId, fmt)"
            >
              <el-button text size="small" type="info" aria-label="选择旧版下载格式">
                <el-icon><Download /></el-icon>
                下载旧版
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="format in getDownloadFormats(selectedOldVersion)"
                    :key="format"
                    :command="format"
                  >
                    {{ getDownloadFormatLabel(format) }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button
              v-else-if="oldVersionId && !allowDownload"
              text
              size="small"
              type="info"
              :disabled="true"
            >
              <el-icon><Download /></el-icon>
              禁止下载
            </el-button>
          </div>

          <div class="selector-item">
            <span class="selector-label">新版本</span>
            <el-select v-model="newVersionId" placeholder="选择新版本" class="version-select">
              <el-option
                v-for="v in versions"
                :key="v.id"
                :label="`v${v.version} - ${formatDate(v.created_at)}`"
                :value="v.id"
              />
            </el-select>
            <el-button
              v-if="allowDownload && newVersionId && hasSingleDownloadFormat(selectedNewVersion)"
              text
              size="small"
              type="success"
              @click="downloadVersion(newVersionId)"
            >
              <el-icon><Download /></el-icon>
              {{ getDownloadFormatLabel(getDownloadFormats(selectedNewVersion)[0]) }}
            </el-button>
            <el-dropdown
              v-else-if="allowDownload && newVersionId && hasMultipleDownloadFormats(selectedNewVersion)"
              trigger="click"
              @command="(fmt) => downloadVersion(newVersionId, fmt)"
            >
              <el-button text size="small" type="success" aria-label="选择新版下载格式">
                <el-icon><Download /></el-icon>
                下载新版
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="format in getDownloadFormats(selectedNewVersion)"
                    :key="format"
                    :command="format"
                  >
                    {{ getDownloadFormatLabel(format) }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button
              v-else-if="newVersionId && !allowDownload"
              text
              size="small"
              type="success"
              :disabled="true"
            >
              <el-icon><Download /></el-icon>
              禁止下载
            </el-button>
          </div>
        </div>

        <el-button
          type="primary"
          :loading="diffLoading"
          :disabled="!oldVersionId || !newVersionId || oldVersionId === newVersionId"
          @click="fetchDiff"
          class="compare-btn"
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
      :paragraphs="diffData.paragraphs"
      class="summary-card"
      @jump-to="onJumpTo"
    />

    <template v-if="diffData">
      <DocxDiffView
        v-if="fileType === 'docx' || fileType === 'doc'"
        ref="docxDiffRef"
        :diff-data="diffData"
      />
      <XlsxDiffView v-else-if="fileType === 'xlsx' || fileType === 'xls'" :diff-data="diffData" />
      <PdfDiffView v-else-if="fileType === 'pdf'" :diff-data="diffData" />
      <el-empty v-else description="暂不支持该文件类型的 Diff 预览" />
    </template>

    <el-card v-if="!loading && !diffData && versions.length > 0" shadow="never" class="empty-card">
      <el-empty description="请选择两个版本进行对比" />
    </el-card>

    <div v-if="unlockRequired" data-testid="share-unlock-card">
      <el-card shadow="never" class="unlock-card">
        <template #header>
          <span class="card-title">输入访问密码</span>
        </template>

        <div class="unlock-form">
          <p class="unlock-copy">当前变更对比已启用访问密码，请先解锁后继续。</p>
          <el-input
            v-model="unlockPassword"
            type="password"
            show-password
            clearable
            placeholder="请输入访问密码"
            data-testid="share-unlock-password"
          />
          <p v-if="unlockError" class="unlock-error">{{ unlockError }}</p>
          <div class="unlock-actions">
            <el-button
              type="primary"
              :loading="unlocking"
              data-testid="share-unlock-submit"
              @click="submitUnlock"
            >
              解锁访问
            </el-button>
            <el-button :disabled="unlocking" @click="goBack">返回</el-button>
          </div>
        </div>
      </el-card>
    </div>

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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getShareVersions, getShareDiffs } from '@/api/share'
import { useShareSession } from '@/composables/useShareSession'
import { usePublicAccessSession } from '@/composables/usePublicAccessSession'
import { formatDate, downloadViaIframe } from '@/utils'
import {
  getDownloadFormatLabel,
  hasMultipleDownloadFormats as resolveHasMultipleDownloadFormats,
  hasSingleDownloadFormat as resolveHasSingleDownloadFormat,
  isOriginalDownloadFormat as resolveIsOriginalDownloadFormat,
  resolveDownloadFormats,
} from '@/utils/downloadFormats'
import { getShareResourceUrl } from '@/utils/shareResourceTickets'
import { buildShareFilePath } from '@/utils/shareRoute'
import DiffSummary from '@/components/diff/DiffSummary.vue'
import DocxDiffView from '@/components/diff/DocxDiffView.vue'
import XlsxDiffView from '@/components/diff/XlsxDiffView.vue'
import PdfDiffView from '@/components/diff/PdfDiffView.vue'

const route = useRoute()
const router = useRouter()

const token = route.params.token
const fileId = route.params.fileId
const shareSession = useShareSession(token)
const publicAccessSession = usePublicAccessSession(token, 'file', fileId)

const DEFAULT_SHARE_PERMISSIONS = {
  allow_download: true,
  allow_preview: true,
  allow_diff: true,
  allow_versions: true,
}

const loading = ref(false)
const diffLoading = ref(false)
const versions = ref([])
const oldVersionId = ref(null)
const newVersionId = ref(null)
const diffData = ref(null)
const fileType = ref('')
const filename = ref('')
const error = ref('')
const shareInfo = ref({ ...DEFAULT_SHARE_PERMISSIONS })
const unlockRequired = ref(false)
const unlockMode = ref('share')
const unlockPassword = ref('')
const unlocking = ref(false)
const unlockError = ref('')
let publicAccessHeartbeatTimer = null

const docxDiffRef = ref(null)
const allowDownload = computed(() => shareInfo.value?.allow_download !== false)
const selectedOldVersion = computed(() => versions.value.find((version) => version?.id === oldVersionId.value) || null)
const selectedNewVersion = computed(() => versions.value.find((version) => version?.id === newVersionId.value) || null)

function isSharePasswordRequiredError(err) {
  return shareSession.isPasswordRequiredError(err)
}

function isResourcePasswordRequiredError(err) {
  return publicAccessSession.isResourcePasswordRequiredError(err)
}

function getUnlockErrorMessage(err) {
  return unlockMode.value === 'resource'
    ? publicAccessSession.getUnlockErrorMessage(err)
    : shareSession.getUnlockErrorMessage(err)
}

function buildAccessHeaders() {
  return shareSession.withShareHeaders(publicAccessSession.withAccessHeaders())
}

function onJumpTo(index) {
  docxDiffRef.value?.scrollToHunk(index)
}

function getFileDownloadContext() {
  return {
    file_type: fileType.value,
    filename: filename.value,
  }
}

function getDownloadFormats(version = null) {
  return resolveDownloadFormats(getFileDownloadContext(), version)
}

function hasSingleDownloadFormat(version = null) {
  return resolveHasSingleDownloadFormat(getFileDownloadContext(), version)
}

function hasMultipleDownloadFormats(version = null) {
  return resolveHasMultipleDownloadFormats(getFileDownloadContext(), version)
}

function goBack() {
  const path = buildShareFilePath(token, fileId)
  router.push(path || '/')
}

async function fetchVersions() {
  loading.value = true
  error.value = ''
  try {
    const data = await getShareVersions(token, fileId, {
      headers: buildAccessHeaders(),
    })
    unlockRequired.value = false
    unlockMode.value = 'share'
    unlockError.value = ''
    shareInfo.value = { ...DEFAULT_SHARE_PERMISSIONS, ...(data.share || {}) }
    versions.value = data.versions || data || []
    if (versions.value.length >= 2) {
      oldVersionId.value = versions.value[1]?.id
      newVersionId.value = versions.value[0]?.id
    } else if (versions.value.length === 1) {
      newVersionId.value = versions.value[0].id
    }
    if (versions.value.length > 0) {
      fileType.value = data.file_type || versions.value[0].file_type || ''
    }
    filename.value = data.filename || ''
  } catch (err) {
    if (isSharePasswordRequiredError(err)) {
      unlockRequired.value = true
      unlockMode.value = 'share'
      error.value = ''
      return
    }
    if (isResourcePasswordRequiredError(err)) {
      unlockRequired.value = true
      unlockMode.value = 'resource'
      error.value = ''
      return
    }
    const detail = err?.response?.data?.detail
    if (detail === 'login_required') {
      error.value = '请先登录后访问该公开资源'
    } else if (detail === 'group_required') {
      error.value = '当前账号不在允许访问的用户组中'
    } else {
      error.value = '文件不存在或无权访问'
    }
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
      old_version: oldVersionId.value,
      new_version: newVersionId.value,
    }, {
      headers: buildAccessHeaders(),
    })
    const firstDiff = data.diffs?.[0]
    if (firstDiff) {
      const parsed = typeof firstDiff.diff_data === 'string'
        ? JSON.parse(firstDiff.diff_data)
        : firstDiff.diff_data
      diffData.value = { ...parsed, summary: firstDiff.summary }
    }
  } catch (err) {
    if (isSharePasswordRequiredError(err)) {
      unlockRequired.value = true
      unlockMode.value = 'share'
      error.value = ''
      return
    }
    if (isResourcePasswordRequiredError(err)) {
      unlockRequired.value = true
      unlockMode.value = 'resource'
      error.value = ''
      return
    }
    ElMessage.warning(err?.message || '变更对比加载失败')
  } finally {
    diffLoading.value = false
  }
}

async function downloadVersion(versionId, format) {
  const version = versions.value.find((item) => item?.id === versionId) || null
  const formats = getDownloadFormats(version)
  const selectedFormat = format || formats[0]
  if (!selectedFormat) {
    ElMessage.warning('暂无可用下载格式')
    return
  }

  const isOriginal = resolveIsOriginalDownloadFormat(getFileDownloadContext(), selectedFormat, version)
  const url = await getShareResourceUrl({
    token,
    session: shareSession,
    accessSession: publicAccessSession,
    kind: isOriginal ? 'download_original' : 'download_converted',
    fileId,
    versionId,
    format: isOriginal ? undefined : selectedFormat,
  })
  downloadViaIframe(url)
}

async function submitUnlock() {
  const password = String(unlockPassword.value || '')
  if (!password.trim()) {
    unlockError.value = '请输入访问密码'
    return
  }

  unlocking.value = true
  unlockError.value = ''
  try {
    if (unlockMode.value === 'resource') {
      await publicAccessSession.unlock(password)
    } else {
      await shareSession.unlock(password)
    }
    unlockRequired.value = false
    unlockPassword.value = ''
    await fetchVersions()
  } catch (err) {
    unlockError.value = getUnlockErrorMessage(err)
  } finally {
    unlocking.value = false
  }
}

function clearPublicAccessHeartbeat() {
  if (publicAccessHeartbeatTimer) {
    clearInterval(publicAccessHeartbeatTimer)
    publicAccessHeartbeatTimer = null
  }
}

function startPublicAccessHeartbeat() {
  clearPublicAccessHeartbeat()
  if (typeof window === 'undefined') return
  if (!publicAccessSession.grantToken.value) return
  publicAccessHeartbeatTimer = window.setInterval(() => {
    publicAccessSession.heartbeat().catch(() => {})
  }, 30000)
}

function releasePublicAccessOnPageHide() {
  publicAccessSession.releaseOnPageHide?.()
}

onMounted(() => {
  fetchVersions()
  if (typeof window !== 'undefined') {
    window.addEventListener('pagehide', releasePublicAccessOnPageHide)
    window.addEventListener('beforeunload', releasePublicAccessOnPageHide)
  }
})

watch(() => publicAccessSession.grantToken.value, () => {
  startPublicAccessHeartbeat()
}, { immediate: true })

onBeforeUnmount(() => {
  clearPublicAccessHeartbeat()
  if (typeof window !== 'undefined') {
    window.removeEventListener('pagehide', releasePublicAccessOnPageHide)
    window.removeEventListener('beforeunload', releasePublicAccessOnPageHide)
  }
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
  transition:
    transform var(--transition-fast),
    box-shadow var(--transition-fast),
    border-color var(--transition-fast),
    background-color var(--transition-fast),
    color var(--transition-fast),
    opacity var(--transition-fast);
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
  transition:
    transform var(--transition-fast),
    box-shadow var(--transition-fast),
    border-color var(--transition-fast),
    background-color var(--transition-fast),
    color var(--transition-fast),
    opacity var(--transition-fast);
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

@media (max-width: 768px) {
  .share-diff {
    overflow-x: hidden;
    padding-bottom: 12px;
  }

  .selector-card {
    margin-bottom: 12px;
  }

  .diff-controls {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .version-selectors {
    flex-direction: column;
    gap: 12px;
  }

  .selector-item {
    align-items: stretch;
    flex-direction: column;
    gap: 6px;
    width: 100%;
  }

  .version-select {
    width: 100%;
  }

  .selector-item :deep(.el-dropdown),
  .selector-item :deep(.el-button) {
    width: 100%;
  }

  .compare-btn {
    width: 100%;
    min-height: 42px;
  }
}
</style>
