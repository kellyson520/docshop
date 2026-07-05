<template>
  <div class="share-file">
    <el-button text class="back-btn" @click="goBack">
      <el-icon><ArrowLeft /></el-icon>
      返回文件列表
    </el-button>

    <template v-if="loading && !error">
      <el-card shadow="never" class="file-info-card">
        <el-skeleton :rows="1" animated />
      </el-card>
      <el-card shadow="never" class="version-card">
        <el-skeleton :rows="4" animated />
      </el-card>
    </template>

    <el-card v-if="fileInfo" shadow="never" class="file-info-card">
      <div class="file-info">
        <div class="file-info-main">
          <h3 class="file-name">{{ fileDisplayName }}</h3>
          <div class="file-meta">
            <el-tag size="small" :type="getFileTypeTagType(fileInfo.file_type)" effect="light">
              {{ fileInfo.file_type?.toUpperCase() }}
            </el-tag>
            <span class="meta-item">{{ formatFileSize(fileInfo.file_size || 0) }}</span>
            <span class="meta-item">{{ formatDate(fileInfo.created_at) }}</span>
          </div>
        </div>
      </div>
    </el-card>

    <el-card v-if="fileInfo" shadow="never" class="version-card">
      <template #header>
        <span class="card-title">版本历史</span>
      </template>

      <el-timeline v-if="versions.length > 0">
        <el-timeline-item
          v-for="version in versions"
          :key="version.id"
          :timestamp="formatDate(version.created_at)"
          placement="top"
          :type="isLatestVersion(version, versions) ? 'primary' : 'info'"
        >
          <el-card shadow="never" class="version-item-card">
            <div class="version-header">
              <div class="version-info">
                <el-tag :type="isLatestVersion(version, versions) ? 'primary' : 'info'" size="small" effect="light">
                  v{{ version.version }}
                </el-tag>
                <span v-if="isLatestVersion(version, versions)" class="latest-badge">最新</span>
              </div>
              <div class="version-actions">
                <template v-if="allowDownload">
                  <el-button
                    v-if="hasSingleDownloadFormat(version)"
                    type="success"
                    size="small"
                    data-testid="share-file-download-original"
                    class="action-btn"
                    @click="handleDownload(version)"
                  >
                    <el-icon><Download /></el-icon>
                    下载
                  </el-button>
                  <el-dropdown v-else-if="hasMultipleDownloadFormats(version)" trigger="click" @command="(fmt) => handleDownload(version, fmt)">
                    <el-button type="success" size="small" class="action-btn" aria-label="选择下载格式">
                      <el-icon><Download /></el-icon>
                      下载
                      <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item
                          v-for="format in getDownloadFormats(version)"
                          :key="format"
                          :command="format"
                        >
                          <el-icon><Document /></el-icon>
                          {{ getDownloadFormatLabel(format) }}
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </template>
                <el-button v-else :disabled="true" size="small" class="action-btn">
                  <el-icon><Download /></el-icon>
                  禁止下载
                </el-button>
                <template v-if="canCompareWithPreviousVersion(version)">
                  <el-button
                    v-if="allowDiff"
                    type="warning"
                    size="small"
                    class="action-btn"
                    @click="goToDiff(version.id)"
                  >
                    <el-icon><Sort /></el-icon>
                    查看变更
                  </el-button>
                  <el-button v-else :disabled="true" size="small" class="action-btn">
                    <el-icon><Sort /></el-icon>
                    查看变更
                  </el-button>
                </template>
              </div>
            </div>

            <div v-if="versionDiff(version)" class="diff-mini">
              <span v-if="versionDiff(version).paragraphs_added" class="diff-stat add">+{{ versionDiff(version).paragraphs_added }} 新增</span>
              <span v-if="versionDiff(version).paragraphs_deleted" class="diff-stat del">-{{ versionDiff(version).paragraphs_deleted }} 删除</span>
              <span v-if="versionDiff(version).paragraphs_modified" class="diff-stat mod">~{{ versionDiff(version).paragraphs_modified }} 修改</span>
            </div>

            <p v-if="version.changelog" class="version-changelog">{{ version.changelog }}</p>
            <p v-else-if="!versionDiff(version)" class="version-changelog no-changelog">无变更说明</p>
          </el-card>
        </el-timeline-item>
      </el-timeline>

      <el-empty v-else description="暂无版本记录" />
    </el-card>

    <div v-if="unlockRequired" data-testid="share-unlock-card">
      <el-card shadow="never" class="unlock-card">
        <template #header>
          <span class="card-title">输入分享密码</span>
        </template>

        <div class="unlock-form">
          <p class="unlock-copy">该分享文件已启用访问密码，请先解锁。</p>
          <el-input
            v-model="unlockPassword"
            type="password"
            show-password
            clearable
            placeholder="请输入分享密码"
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
import {
  ArrowDown,
  ArrowLeft,
  Document,
  Download,
  Sort,
} from '@element-plus/icons-vue'
import { getShareDiffs, getShareFile, getShareVersions } from '@/api/share'
import { useShareSession } from '@/composables/useShareSession'
import { usePublicAccessSession } from '@/composables/usePublicAccessSession'
import { downloadViaIframe, formatDate, formatFileSize } from '@/utils'
import {
  getDownloadFormatLabel,
  hasMultipleDownloadFormats as resolveHasMultipleDownloadFormats,
  hasSingleDownloadFormat as resolveHasSingleDownloadFormat,
  isOriginalDownloadFormat as resolveIsOriginalDownloadFormat,
  resolveDownloadFormats,
} from '@/utils/downloadFormats'
import {
  buildDiffByNewVersion,
  canCompareWithPreviousVersion,
  getVersionDiffStats,
  isLatestVersion,
  normalizeVersionHistory,
} from '@/utils/versionHistory'
import { getShareResourceUrl } from '@/utils/shareResourceTickets'
import { buildShareDiffPath, buildShareHomePath } from '@/utils/shareRoute'

const route = useRoute()
const router = useRouter()

const DEFAULT_SHARE_PERMISSIONS = {
  allow_download: true,
  allow_preview: true,
  allow_diff: true,
  allow_versions: true,
}

const token = route.params.token
const fileId = route.params.fileId
const shareSession = useShareSession(token)
const publicAccessSession = usePublicAccessSession(token, 'file', fileId)

const fileInfo = ref(null)
const versions = ref([])
const diffMap = ref({})
const loading = ref(false)
const error = ref('')
const shareInfo = ref({ ...DEFAULT_SHARE_PERMISSIONS })
const unlockRequired = ref(false)
const unlockMode = ref('share')
const unlockPassword = ref('')
const unlocking = ref(false)
const unlockError = ref('')
let publicAccessHeartbeatTimer = null

const allowDownload = computed(() => shareInfo.value?.allow_download !== false)
const allowDiff = computed(() => shareInfo.value?.allow_diff !== false)
const fileDisplayName = computed(() => (
  fileInfo.value?.display_name || fileInfo.value?.original_filename || fileInfo.value?.filename || ''
))

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

function versionDiff(version) {
  return getVersionDiffStats(version, diffMap.value)
}

function getFileTypeTagType(type) {
  const map = { pdf: 'danger', docx: 'primary', doc: 'primary', xlsx: 'success', xls: 'success' }
  return map[type] || 'info'
}

function getDownloadFormats(version = null) {
  return resolveDownloadFormats(fileInfo.value, version)
}

function hasSingleDownloadFormat(version) {
  return resolveHasSingleDownloadFormat(fileInfo.value, version)
}

function hasMultipleDownloadFormats(version) {
  return resolveHasMultipleDownloadFormats(fileInfo.value, version)
}

function goBack() {
  const path = buildShareHomePath(token)
  router.push(path || '/')
}

function goToDiff(versionId) {
  const path = buildShareDiffPath(token, fileId, { version_id: versionId })
  if (path) {
    router.push(path)
  }
}

async function handleDownload(version, format) {
  const formats = getDownloadFormats(version)
  const selectedFormat = format || formats[0]
  if (!selectedFormat) {
    return
  }
  const isOriginal = resolveIsOriginalDownloadFormat(fileInfo.value, selectedFormat, version)
  const url = await getShareResourceUrl({
    token,
    session: shareSession,
    accessSession: publicAccessSession,
    kind: isOriginal ? 'download_original' : 'download_converted',
    fileId,
    versionId: version.id,
    format: isOriginal ? undefined : selectedFormat,
  })
  downloadViaIframe(url)
}

async function submitUnlock() {
  const password = String(unlockPassword.value || '')
  if (!password.trim()) {
    unlockError.value = '请输入分享密码'
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
    await fetchData()
  } catch (err) {
    unlockError.value = getUnlockErrorMessage(err)
  } finally {
    unlocking.value = false
  }
}

async function fetchData() {
  loading.value = true
  error.value = ''

  try {
    const headers = buildAccessHeaders()
    const fileData = await getShareFile(token, fileId, { headers })
    const [versionsData, diffsData] = await Promise.all([
      getShareVersions(token, fileId, { headers }),
      getShareDiffs(token, fileId, undefined, { headers }).catch(() => ({ diffs: [] })),
    ])

    unlockRequired.value = false
    unlockMode.value = 'share'
    unlockError.value = ''
    fileInfo.value = fileData
    shareInfo.value = { ...DEFAULT_SHARE_PERMISSIONS, ...(fileData.share || {}), ...(versionsData.share || {}) }
    versions.value = normalizeVersionHistory(versionsData.versions || versionsData || [])
    diffMap.value = buildDiffByNewVersion(versions.value, diffsData.diffs || [])
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
  fetchData()
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
.share-file {
  animation: fadeIn var(--transition-normal);
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

.file-info-card,
.version-card,
.error-card,
.unlock-card {
  border-radius: var(--radius-lg, 12px);
  background-color: var(--bg-secondary, #ffffff);
  border: 1px solid var(--border-color, #e4e7ed);
}

.file-info-card {
  margin-bottom: 20px;
}

.unlock-card {
  margin-bottom: 20px;
}

.file-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary, #333333);
  margin: 0 0 8px 0;
}

.file-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-secondary, #666666);
  font-size: 13px;
}

.meta-item {
  color: var(--text-tertiary, #999999);
}

.card-title {
  font-weight: 600;
  color: var(--text-primary, #333333);
}

.version-item-card {
  margin-bottom: 0;
  border-radius: var(--radius-md, 8px);
  background-color: var(--bg-tertiary, #fafafa);
  border: 1px solid var(--border-color-light, #ebeef5);
}

.version-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  flex-wrap: wrap;
  gap: 8px;
}

.version-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.latest-badge {
  color: var(--color-primary, #1A5276);
  font-size: 12px;
  font-weight: 600;
}

.version-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  transition:
    transform var(--transition-fast),
    box-shadow var(--transition-fast),
    border-color var(--transition-fast),
    background-color var(--transition-fast),
    color var(--transition-fast),
    opacity var(--transition-fast);
}

.action-btn:hover {
  transform: translateY(-1px);
}

.version-changelog {
  color: var(--text-secondary, #666666);
  font-size: 13px;
  margin: 0;
  line-height: 1.6;
}

.version-changelog.no-changelog {
  color: var(--text-placeholder, #c0c4cc);
  font-style: italic;
}

.diff-mini {
  display: flex;
  gap: 10px;
  margin-bottom: 6px;
}

.diff-stat {
  font-size: 12px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
}

.diff-stat.add {
  background: #dcfce7;
  color: #166534;
}

.diff-stat.del {
  background: #fee2e2;
  color: #991b1b;
}

.diff-stat.mod {
  background: #fef3c7;
  color: #92400e;
}

.unlock-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.unlock-copy {
  margin: 0;
  color: var(--text-secondary, #666666);
  line-height: 1.6;
}

.unlock-error {
  margin: 0;
  color: #dc2626;
  font-size: 13px;
}

.unlock-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
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
  .share-file {
    overflow-x: hidden;
  }

  .back-btn {
    width: 100%;
    justify-content: flex-start;
    margin-bottom: 10px;
  }

  .file-name {
    font-size: 16px;
    line-height: 1.35;
    overflow-wrap: anywhere;
  }

  .file-meta {
    align-items: flex-start;
    flex-direction: column;
    gap: 7px;
  }

  .version-card :deep(.el-card__body) {
    padding: 12px;
  }

  .version-card :deep(.el-timeline) {
    padding-left: 4px;
  }

  .version-card :deep(.el-timeline-item__wrapper) {
    padding-left: 18px;
  }

  .version-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .version-actions {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    justify-content: stretch;
    gap: 8px;
  }

  .version-actions :deep(.el-dropdown),
  .version-actions :deep(.el-button) {
    width: 100%;
  }

  .version-actions :deep(.el-button) {
    min-height: 40px;
    margin-left: 0;
  }

  .diff-mini {
    flex-wrap: wrap;
    gap: 6px;
  }

  .version-changelog {
    overflow-wrap: anywhere;
  }
}
</style>
