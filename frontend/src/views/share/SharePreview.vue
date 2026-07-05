<template>
  <div class="share-preview">
    <template v-if="loading && !error">
      <el-card shadow="never" class="file-info-card">
        <el-skeleton :rows="1" animated />
      </el-card>
      <el-card shadow="never" class="preview-card">
        <el-skeleton :rows="4" animated />
      </el-card>
    </template>

    <div
      v-if="fileInfo && showMobilePreviewShell"
      class="preview-mobile-shell"
      data-testid="share-preview-mobile-shell"
    >
      <div class="preview-mobile-toolbar" data-testid="share-preview-mobile-toolbar">
        <button type="button" class="preview-mobile-toolbar__button" @click="goBack">
          返回
        </button>
        <div class="preview-mobile-toolbar__title">{{ fileDisplayName }}</div>
        <button
          type="button"
          class="preview-mobile-toolbar__button preview-mobile-toolbar__button--info"
          data-testid="share-preview-mobile-info-toggle"
          @click="toggleMobileInfo"
        >
          {{ mobileInfoExpanded ? '收起' : '信息' }}
        </button>
      </div>

      <div
        v-if="mobileInfoExpanded"
        class="preview-mobile-info-panel"
        data-testid="share-preview-mobile-info-panel"
      >
        <span>{{ fileInfo.file_type?.toUpperCase() || 'FILE' }}</span>
        <span>{{ formatFileSize(fileInfo.file_size || 0) }}</span>
        <span>{{ formatDate(fileInfo.created_at) }}</span>
      </div>
    </div>

    <div
      v-if="showDesktopPreviewShell"
      ref="desktopTopSentinelRef"
      class="preview-desktop-shell__top-sentinel"
      aria-hidden="true"
    />

    <div
      v-if="showDesktopPreviewShell"
      class="preview-desktop-shell"
      data-testid="share-preview-desktop-shell"
    >
      <div class="preview-desktop-shell__main">
        <button
          type="button"
          class="preview-shell-action preview-shell-action--compact preview-desktop-shell__back"
          @click="goBack"
        >
          <span class="preview-shell-action__icon" aria-hidden="true">←</span>
          返回
        </button>
        <div class="preview-desktop-shell__copy">
          <h2 class="preview-desktop-shell__title">{{ desktopPreviewTitle }}</h2>
        </div>
        <div class="preview-desktop-shell__actions">
          <button type="button" class="preview-shell-action preview-shell-action--compact" @click="refreshPreview">
            刷新预览
          </button>
          <button
            type="button"
            class="preview-shell-action preview-shell-action--compact"
            data-testid="share-preview-desktop-toggle"
            @click="toggleDesktopShell"
          >
            {{ desktopShellExpanded ? '收起信息' : '展开信息' }}
          </button>
          <button
            type="button"
            :disabled="!showDesktopBackToTop"
            class="preview-shell-action preview-shell-action--compact"
            :class="{ 'preview-shell-action--primary': showDesktopBackToTop }"
            data-testid="share-preview-back-to-top"
            @click="scrollToTop()"
          >
            回到顶部
          </button>
        </div>
      </div>
      <div
        v-if="desktopShellExpanded"
        class="preview-desktop-shell__details"
        data-testid="share-preview-desktop-meta"
      >
        <div class="preview-desktop-shell__meta">
          <span>{{ fileInfo.file_type?.toUpperCase() || 'FILE' }}</span>
          <span>{{ formatFileSize(fileInfo.file_size || 0) }}</span>
          <span>{{ formatDate(fileInfo.created_at) }}</span>
        </div>
      </div>
    </div>

    <div
      v-if="fileInfo && previewUsesImmersive"
      :class="['share-preview__direct-stage', { 'share-preview__direct-stage--html-immersive': previewUsesBareHtmlStage }]"
      data-testid="share-preview-direct-stage"
    >
      <div v-if="embeddedPreviewLoading" class="preview-state">
        <el-skeleton :rows="4" animated />
      </div>

      <el-result
        v-else-if="embeddedPreviewError"
        icon="error"
        title="预览加载失败"
        :sub-title="embeddedPreviewError"
      >
        <template #extra>
          <el-button type="primary" @click="reloadEmbeddedPreview">重试</el-button>
        </template>
      </el-result>

      <div
        v-else-if="previewIsOffice"
        class="preview-mounted-host"
        data-testid="share-preview-office-mounted"
        v-html="officePreviewMarkup"
      />

      <iframe
        v-else-if="previewIsPdf"
        :src="resolvedPreviewUrl"
        class="preview-frame preview-frame--direct preview-frame--scaled"
        data-testid="share-preview-pdf-frame"
        referrerpolicy="no-referrer"
      />

      <iframe
        v-else-if="previewIsHtml"
        :src="resolvedPreviewUrl"
        :class="['preview-frame preview-frame--direct', { 'preview-frame--html-immersive': previewUsesBareHtmlStage }]"
        data-testid="share-preview-html-frame"
        sandbox="allow-scripts allow-forms allow-modals allow-downloads"
        referrerpolicy="no-referrer"
      />

      <img
        v-else-if="previewIsImage"
        :src="resolvedPreviewUrl"
        :alt="fileDisplayName || '图片预览'"
        class="preview-image"
        data-testid="share-preview-image"
      />

      <FileViewer
        v-else
        :file="fileInfo"
        :manifest="effectivePreviewManifest"
        :analysis-summary="previewAnalysisSummary"
      />
    </div>

    <el-card v-else-if="fileInfo && previewIsVideo" shadow="never" class="preview-card">
      <template #header>
        <span class="card-title">文件预览</span>
      </template>

      <div v-if="embeddedPreviewLoading" class="preview-state">
        <el-skeleton :rows="4" animated />
      </div>

      <el-result
        v-else-if="embeddedPreviewError"
        icon="error"
        title="预览加载失败"
        :sub-title="embeddedPreviewError"
      >
        <template #extra>
          <el-button type="primary" @click="reloadEmbeddedPreview">重试</el-button>
        </template>
      </el-result>

      <FileViewer
        v-else
        :file="fileInfo"
        :manifest="effectivePreviewManifest"
        :analysis-summary="previewAnalysisSummary"
      />
    </el-card>

    <div v-if="unlockRequired" data-testid="share-unlock-card">
      <el-card shadow="never" class="unlock-card">
        <template #header>
          <span class="card-title">输入分享密码</span>
        </template>

        <div class="unlock-form">
          <p class="unlock-copy">该分享预览已启用访问密码，请先解锁。</p>
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

    <div
      v-if="fileInfo && showMobilePreviewShell"
      class="preview-mobile-actions"
      data-testid="share-preview-mobile-actions"
    >
      <button type="button" class="preview-mobile-actions__button" @click="scrollToTop()">
        回到顶部
      </button>
      <button
        type="button"
        class="preview-mobile-actions__button preview-mobile-actions__button--primary"
        @click="refreshPreview"
      >
        刷新预览
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import client from '@/api/client'
import { getShareFile } from '@/api/share'
import FileViewer from '@/components/file-viewer/FileViewer.vue'
import { useResponsive } from '@/composables/useResponsive'
import { useShareSession } from '@/composables/useShareSession'
import { usePublicAccessSession } from '@/composables/usePublicAccessSession'
import { getAccessDeniedRedirect } from '@/router/accessGate'
import { useScroll } from '@/composables/useScroll'
import { getShareResourceUrl } from '@/utils/shareResourceTickets'
import { formatDate, formatFileSize } from '@/utils'
import { buildSharePreviewUrl } from '@/utils/resourceUrl'
import { buildShareHomePath } from '@/utils/shareRoute'

const route = useRoute()
const router = useRouter()

const token = route.params.token
const fileId = route.params.fileId
const shareSession = useShareSession(token)
const publicAccessSession = usePublicAccessSession(token, 'file', fileId)

const fileInfo = ref(null)
const loading = ref(false)
const error = ref('')
const unlockRequired = ref(false)
const unlockMode = ref('share')
const unlockPassword = ref('')
const unlocking = ref(false)
const unlockError = ref('')
const embeddedPreviewLoading = ref(false)
const embeddedPreviewError = ref('')
const officePreviewHtml = ref('')
const officePreviewMarkup = ref('')
const browserPreviewUrl = ref('')
const resolvedPreviewManifest = ref(null)
const mobileInfoExpanded = ref(false)
const desktopShellExpanded = ref(false)
const desktopTopSentinelRef = ref(null)
const desktopTopSentinelVisible = ref(true)
const { isMobile } = useResponsive()
const { isScrolled, scrollToTop } = useScroll({ threshold: 160 })
let desktopTopObserver = null
let publicAccessHeartbeatTimer = null

const fileDisplayName = computed(() => (
  fileInfo.value?.display_name || fileInfo.value?.original_filename || fileInfo.value?.filename || ''
))
const currentPreviewVersion = computed(() => Number(fileInfo.value?.current_version || 1) || 1)
const previewVersionSuffix = computed(() => ` · v${currentPreviewVersion.value}`)
const desktopPreviewTitle = computed(() => (
  fileDisplayName.value ? `${fileDisplayName.value}${previewVersionSuffix.value}` : ''
))
const previewAnalysisSummary = computed(() => fileInfo.value?.analysis_summary || {})
const previewManifest = computed(() => {
  const backendManifest = fileInfo.value?.preview_manifest || null
  if (isRenderablePreviewManifest(backendManifest)) {
    return backendManifest
  }
  return buildPreviewManifest(fileInfo.value, previewAnalysisSummary.value)
})
const effectivePreviewManifest = computed(() => resolvedPreviewManifest.value || previewManifest.value)
const resolvedPreviewUrl = computed(() => {
  if (browserPreviewUrl.value) {
    return browserPreviewUrl.value
  }
  const manifestUrl = effectivePreviewManifest.value?.primary_asset?.url
  return typeof manifestUrl === 'string' && manifestUrl.length > 0
    ? manifestUrl
    : buildSharePreviewUrl(token, fileId)
})
const previewType = computed(() => effectivePreviewManifest.value?.type || '')
const previewIsVideo = computed(() => previewType.value === 'video_native')
const previewIsHtml = computed(() => ['html_native', 'html_runtime'].includes(previewType.value))
const previewIsOffice = computed(() => previewType.value === 'office_pdf')
const previewIsPdf = computed(() => previewType.value === 'pdf_native')
const previewIsImage = computed(() => previewType.value === 'image_native')
const previewUsesBareHtmlStage = computed(() => previewIsHtml.value)
const previewUsesImmersive = computed(() => !previewIsVideo.value)
const previewNeedsEmbeddedHtml = computed(() => previewIsOffice.value)
const showMobilePreviewShell = computed(() => (
  !previewUsesBareHtmlStage.value && isMobile.value && !!fileInfo.value
))
const showDesktopPreviewShell = computed(() => (
  !previewUsesBareHtmlStage.value && !showMobilePreviewShell.value && !!fileInfo.value
))
const showDesktopBackToTop = computed(() => (
  !!fileInfo.value && (isScrolled.value || !desktopTopSentinelVisible.value)
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

function getFileTypeTagType(type) {
  const map = { pdf: 'danger', docx: 'primary', doc: 'primary', xlsx: 'success', xls: 'success' }
  return map[type] || 'info'
}

function isRenderablePreviewManifest(manifest) {
  if (!manifest || typeof manifest !== 'object') return false

  const assetType = manifest?.primary_asset?.asset_type
  const assetUrl = manifest?.primary_asset?.url

  switch (manifest.type) {
    case 'video_native':
      return ['video', 'preview_video'].includes(assetType) && typeof assetUrl === 'string' && assetUrl.length > 0
    case 'image_native':
      return ['image', 'original'].includes(assetType) && typeof assetUrl === 'string' && assetUrl.length > 0
    case 'pdf_native':
      return assetType === 'pdf' && typeof assetUrl === 'string' && assetUrl.length > 0
    case 'html_runtime':
      return assetType === 'html_runtime_entry' && typeof assetUrl === 'string' && assetUrl.length > 0
    case 'html_native':
      return ['html', 'html_runtime_entry'].includes(assetType) && typeof assetUrl === 'string' && assetUrl.length > 0
    case 'office_pdf':
      return assetType === 'pdf' && typeof assetUrl === 'string' && assetUrl.length > 0
    case 'archive_structure':
      return true
    default:
      return false
  }
}

function buildPreviewManifest(file, analysisSummary = {}) {
  const fileType = String(file?.file_type || '').toLowerCase()
  const previewUrl = buildSharePreviewUrl(token, fileId)

  if (['mp4', 'webm', 'mov'].includes(fileType)) {
    return {
      type: 'video_native',
      status: 'ready',
      primary_asset: { asset_type: 'video', url: previewUrl },
      summary: analysisSummary,
    }
  }
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'].includes(fileType)) {
    return {
      type: 'image_native',
      status: 'ready',
      primary_asset: { asset_type: 'image', url: previewUrl },
      summary: analysisSummary,
    }
  }
  if (fileType === 'pdf') {
    return {
      type: 'pdf_native',
      status: 'ready',
      primary_asset: { asset_type: 'pdf', url: previewUrl },
      summary: analysisSummary,
    }
  }
  if (fileType === 'html') {
    return {
      type: 'html_runtime',
      status: 'ready',
      primary_asset: { asset_type: 'html_runtime_entry', url: previewUrl },
      summary: analysisSummary,
    }
  }
  if (['doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'].includes(fileType)) {
    return {
      type: 'office_pdf',
      status: 'ready',
      primary_asset: { asset_type: 'pdf', url: previewUrl },
      summary: analysisSummary,
    }
  }
  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(fileType)) {
    return { type: 'archive_structure', status: 'ready', summary: analysisSummary }
  }

  return { type: 'fallback', status: 'not_supported', summary: analysisSummary }
}

function cloneManifestAsset(asset) {
  if (!asset || typeof asset !== 'object') {
    return asset || null
  }
  return { ...asset }
}

function clonePreviewManifest(manifest) {
  if (!manifest || typeof manifest !== 'object') {
    return manifest || null
  }

  return {
    ...manifest,
    primary_asset: cloneManifestAsset(manifest.primary_asset),
    poster_asset: cloneManifestAsset(manifest.poster_asset),
    original_asset: cloneManifestAsset(manifest.original_asset),
    thumbnails: Array.isArray(manifest.thumbnails)
      ? manifest.thumbnails.map((thumbnail) => ({ ...thumbnail }))
      : [],
    summary: manifest.summary && typeof manifest.summary === 'object'
      ? { ...manifest.summary }
      : manifest.summary,
  }
}

function createShareResourceResolver() {
  const cache = new Map()

  return async ({ kind, pageNum, assetId, versionId, folderId, format }) => {
    const cacheKey = JSON.stringify([
      kind,
      fileId,
      currentPreviewVersion.value,
      pageNum || null,
      assetId || null,
      versionId || null,
      folderId || null,
      format || null,
    ])

    if (!cache.has(cacheKey)) {
      cache.set(cacheKey, getShareResourceUrl({
        token,
        session: shareSession,
        accessSession: publicAccessSession,
        kind,
        fileId,
        version: currentPreviewVersion.value,
        pageNum,
        assetId,
        versionId,
        folderId,
        format,
      }))
    }

    return cache.get(cacheKey)
  }
}

async function resolveManifestAssetUrl(manifestType, asset, resolveResourceUrl) {
  if (!asset?.asset_type) {
    return asset || null
  }

  switch (manifestType) {
    case 'video_native':
      if (['preview_video', 'poster'].includes(asset.asset_type) && asset.asset_id) {
        return {
          ...asset,
          url: await resolveResourceUrl({
            kind: 'preview_asset',
            assetId: asset.asset_id,
          }),
        }
      }

      if (asset.asset_type === 'video') {
        return {
          ...asset,
          url: await resolveResourceUrl({ kind: 'preview' }),
        }
      }
      return asset

    case 'image_native':
    case 'pdf_native':
    case 'office_pdf':
    case 'html_runtime':
    case 'html_native':
      return {
        ...asset,
        url: await resolveResourceUrl({ kind: 'preview' }),
      }

    default:
      return asset
  }
}

async function resolveSharePreviewManifest(manifest, resolveResourceUrl) {
  if (!manifest || typeof manifest !== 'object') {
    return manifest || null
  }

  const nextManifest = clonePreviewManifest(manifest)

  nextManifest.primary_asset = await resolveManifestAssetUrl(
    nextManifest.type,
    nextManifest.primary_asset,
    resolveResourceUrl,
  )
  nextManifest.poster_asset = await resolveManifestAssetUrl(
    nextManifest.type,
    nextManifest.poster_asset,
    resolveResourceUrl,
  )
  nextManifest.original_asset = await resolveManifestAssetUrl(
    nextManifest.type,
    nextManifest.original_asset,
    resolveResourceUrl,
  )

  if (nextManifest.type === 'office_pdf' && Array.isArray(nextManifest.thumbnails)) {
    nextManifest.thumbnails = await Promise.all(nextManifest.thumbnails.map(async (thumbnail) => {
      if (!thumbnail?.page) {
        return thumbnail
      }
      return {
        ...thumbnail,
        url: await resolveResourceUrl({
          kind: 'page',
          pageNum: thumbnail.page,
        }),
      }
    }))
  }

  return nextManifest
}

function absolutizeUrl(rawUrl) {
  const value = String(rawUrl || '').trim()
  if (!value || value.startsWith('#') || value.startsWith('data:') || value.startsWith('javascript:')) {
    return value
  }
  try {
    return new URL(value, resolvedPreviewUrl.value).toString()
  } catch {
    return value
  }
}

function rewriteElementResourceUrls(root) {
  if (!root?.querySelectorAll) return
  root.querySelectorAll('[src],[href],[poster],[action]').forEach((element) => {
    ;['src', 'href', 'poster', 'action'].forEach((attr) => {
      if (!element.hasAttribute(attr)) return
      element.setAttribute(attr, absolutizeUrl(element.getAttribute(attr)))
    })
  })
}

function buildMountedPreviewMarkup(html) {
  if (typeof html !== 'string' || !html.trim()) return ''

  const parser = new DOMParser()
  const doc = parser.parseFromString(html, 'text/html')
  const headMarkup = Array.from(doc.head.querySelectorAll('style, link[rel="stylesheet"]'))
    .map((node) => {
      const clone = node.cloneNode(true)
      if (clone.getAttribute?.('href')) {
        clone.setAttribute('href', absolutizeUrl(clone.getAttribute('href')))
      }
      return clone.outerHTML
    })
    .join('')

  const bodyContainer = document.createElement('div')
  Array.from(doc.body.childNodes).forEach((node) => {
    if (node.nodeType === Node.ELEMENT_NODE && node.nodeName.toLowerCase() === 'script') {
      return
    }
    bodyContainer.appendChild(node.cloneNode(true))
  })
  rewriteElementResourceUrls(bodyContainer)

  return [
    '<div class="preview-mounted-head">',
    headMarkup,
    '</div>',
    '<div class="preview-mounted-body">',
    bodyContainer.innerHTML,
    '</div>',
  ].join('')
}

function normalizeEmbeddedPreviewRequestUrl(rawUrl) {
  const value = String(rawUrl || '').trim()
  if (!value) return value

  if (value.startsWith('/api/v1/')) {
    return value.slice('/api/v1'.length)
  }

  if (/^https?:\/\//i.test(value) && typeof window !== 'undefined') {
    try {
      const parsed = new URL(value, window.location.origin)
      if (parsed.origin === window.location.origin && parsed.pathname.startsWith('/api/v1/')) {
        return `${parsed.pathname.slice('/api/v1'.length)}${parsed.search}${parsed.hash}`
      }
    } catch {
      return value
    }
  }

  return value
}

async function loadEmbeddedPreview() {
  officePreviewHtml.value = ''
  officePreviewMarkup.value = ''
  embeddedPreviewError.value = ''

  if (!previewNeedsEmbeddedHtml.value) return

  embeddedPreviewLoading.value = true
  try {
    const body = await client.get(normalizeEmbeddedPreviewRequestUrl(resolvedPreviewUrl.value), {
      responseType: 'text',
      transformResponse: [(data) => data],
      timeout: 120000,
      cancelable: false,
    })

    if (typeof body === 'string' && body.trim().startsWith('<')) {
      officePreviewHtml.value = body
      officePreviewMarkup.value = buildMountedPreviewMarkup(body)
    }
  } catch (err) {
    embeddedPreviewError.value = err?.message || '文档预览加载失败'
  } finally {
    embeddedPreviewLoading.value = false
  }
}

function reloadEmbeddedPreview() {
  loadEmbeddedPreview()
}

function toggleMobileInfo() {
  mobileInfoExpanded.value = !mobileInfoExpanded.value
}

function toggleDesktopShell() {
  desktopShellExpanded.value = !desktopShellExpanded.value
}

function teardownDesktopTopObserver() {
  desktopTopObserver?.disconnect?.()
  desktopTopObserver = null
}

function setupDesktopTopObserver() {
  teardownDesktopTopObserver()
  desktopTopSentinelVisible.value = true

  if (typeof window === 'undefined' || !('IntersectionObserver' in window) || !desktopTopSentinelRef.value) {
    return
  }

  desktopTopObserver = new IntersectionObserver((entries) => {
    desktopTopSentinelVisible.value = entries[0]?.isIntersecting ?? true
  }, {
    threshold: 0,
  })

  desktopTopObserver.observe(desktopTopSentinelRef.value)
}

function goBack() {
  const path = buildShareHomePath(token)
  router.push(path || '/')
}

function refreshPreview() {
  fetchData()
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
  browserPreviewUrl.value = ''
  resolvedPreviewManifest.value = null
  mobileInfoExpanded.value = false
  desktopShellExpanded.value = false

  try {
    fileInfo.value = await getShareFile(token, fileId, {
      headers: buildAccessHeaders(),
    })
    unlockRequired.value = false
    unlockMode.value = 'share'
    unlockError.value = ''
    const resolveResourceUrl = createShareResourceResolver()
    resolvedPreviewManifest.value = await resolveSharePreviewManifest(
      previewManifest.value,
      resolveResourceUrl,
    )
    browserPreviewUrl.value = resolvedPreviewManifest.value?.primary_asset?.url || ''
    await loadEmbeddedPreview()
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
    if (err?.response?.status === 401) {
      router.push(getAccessDeniedRedirect(route, 'invalid_token'))
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

watch(showDesktopPreviewShell, async (visible) => {
  if (!visible) {
    teardownDesktopTopObserver()
    desktopTopSentinelVisible.value = true
    return
  }

  await nextTick()
  setupDesktopTopObserver()
}, { immediate: true })

onBeforeUnmount(() => {
  teardownDesktopTopObserver()
  clearPublicAccessHeartbeat()
  if (typeof window !== 'undefined') {
    window.removeEventListener('pagehide', releasePublicAccessOnPageHide)
    window.removeEventListener('beforeunload', releasePublicAccessOnPageHide)
  }
})
</script>

<style scoped>
.share-preview {
  --share-preview-scale: 0.88;
  --share-preview-shell-offset: 172px;
  min-height: 100vh;
  animation: fadeIn var(--transition-normal);
}

.file-info-card,
.preview-card,
.error-card,
.unlock-card {
  border-radius: var(--radius-lg, 12px);
  background-color: var(--bg-secondary, #ffffff);
  border: 1px solid var(--border-color, #e4e7ed);
}

.file-info-card,
.preview-card {
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

.preview-state {
  min-height: 320px;
}

.preview-state--redirecting {
  padding-top: 16px;
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

.preview-desktop-shell {
  position: sticky;
  top: 16px;
  z-index: 11;
  inline-size: fit-content;
  max-inline-size: min(100%, 920px);
  margin: 0 auto 16px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(14px);
}

.preview-desktop-shell__top-sentinel {
  width: 1px;
  height: 1px;
  pointer-events: none;
}

.preview-desktop-shell__main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
}

.preview-desktop-shell__copy {
  min-width: 0;
  text-align: center;
  justify-self: center;
  width: min(100%, 480px);
}

.preview-desktop-shell__eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 9px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.preview-desktop-shell__title {
  margin: 0;
  color: #0f172a;
  font-size: 16px;
  font-weight: 800;
  line-height: 1.25;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preview-desktop-shell__details {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 14px 10px;
  border-top: 1px solid rgba(226, 232, 240, 0.82);
}

.preview-desktop-shell__meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.preview-desktop-shell__meta span {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 11px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.12);
  color: #475569;
  font-size: 11px;
  font-weight: 600;
}

.preview-desktop-shell__actions {
  display: flex;
  flex-wrap: nowrap;
  justify-content: flex-end;
  justify-self: end;
  gap: 8px;
  flex: 0 0 auto;
}

.preview-desktop-shell__back {
  justify-self: start;
}

.preview-shell-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 999px;
  background: #ffffff;
  color: #334155;
  font-size: 13px;
  font-weight: 700;
}

.preview-shell-action--compact {
  min-height: 32px;
  padding: 0 10px;
  font-size: 12px;
  white-space: nowrap;
}

.preview-shell-action__icon {
  font-size: 14px;
  line-height: 1;
}

.preview-shell-action--primary {
  border-color: #2563eb;
  background: #2563eb;
  color: #ffffff;
}

.preview-shell-action:disabled {
  cursor: not-allowed;
  border-color: rgba(203, 213, 225, 0.9);
  background: rgba(248, 250, 252, 0.92);
  color: #94a3b8;
  box-shadow: none;
}

.preview-mobile-shell {
  position: sticky;
  top: calc(8px + env(safe-area-inset-top));
  z-index: 12;
  margin-bottom: 12px;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 18px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
}

.preview-mobile-toolbar {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 10px max(12px, env(safe-area-inset-right)) 10px max(12px, env(safe-area-inset-left));
}

.preview-mobile-toolbar__button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 0 14px;
  border: none;
  border-radius: 999px;
  background: rgba(226, 232, 240, 0.7);
  color: #334155;
  font-size: 13px;
  font-weight: 600;
}

.preview-mobile-toolbar__button--info {
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
}

.preview-mobile-toolbar__title {
  min-width: 0;
  text-align: center;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preview-mobile-info-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 max(12px, env(safe-area-inset-right)) 12px max(12px, env(safe-area-inset-left));
  border-top: 1px solid rgba(226, 232, 240, 0.82);
}

.preview-mobile-info-panel span {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.12);
  color: #475569;
  font-size: 12px;
}

.share-preview__direct-stage {
  width: 100%;
  min-height: calc(100vh - var(--share-preview-shell-offset));
  background: transparent;
}

.share-preview__direct-stage--html-immersive {
  position: fixed;
  inset: 0;
  z-index: 20;
  min-height: 100dvh;
  background: #ffffff;
  overflow: hidden;
}

.preview-mounted-host {
  width: 100%;
  min-height: calc(100vh - var(--share-preview-shell-offset));
}

.preview-mounted-host :deep(.preview-mounted-head) {
  display: contents;
}

.preview-mounted-host :deep(.preview-mounted-body) {
  width: 100%;
  min-height: calc(100vh - var(--share-preview-shell-offset));
  zoom: var(--share-preview-scale);
  transform-origin: top center;
}

.preview-frame {
  display: block;
  width: 100%;
  min-height: 72vh;
  border: none;
  background: #ffffff;
}

.preview-frame--direct {
  min-height: calc(100vh - var(--share-preview-shell-offset));
  border-radius: 0;
  box-shadow: none;
}

.preview-frame--html-immersive {
  width: 100vw;
  height: 100dvh;
  min-height: 100dvh;
  background: #ffffff;
}

.preview-frame--scaled {
  zoom: var(--share-preview-scale);
  transform-origin: top center;
}

.preview-image {
  display: block;
  max-width: calc(100% * var(--share-preview-scale));
  max-height: calc((100vh - var(--share-preview-shell-offset)) * var(--share-preview-scale));
  margin: 0 auto;
}

.preview-mobile-actions {
  position: sticky;
  bottom: 0;
  z-index: 11;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 12px max(12px, env(safe-area-inset-right)) calc(12px + env(safe-area-inset-bottom)) max(12px, env(safe-area-inset-left));
  margin-top: 12px;
  background: linear-gradient(180deg, rgba(247, 250, 252, 0.72), rgba(247, 250, 252, 0.98));
  backdrop-filter: blur(14px);
}

.preview-mobile-actions__button {
  min-height: 42px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 14px;
  background: #ffffff;
  color: #334155;
  font-size: 14px;
  font-weight: 600;
}

.preview-mobile-actions__button--primary {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
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

@media (min-width: 768px) {
  .preview-mobile-shell,
  .preview-mobile-actions {
    display: none;
  }
}

@media (max-width: 767px) {
  .share-preview {
    --share-preview-shell-offset: 152px;
    padding-bottom: calc(72px + env(safe-area-inset-bottom));
  }

  .preview-desktop-shell {
    display: none;
  }

  .preview-card {
    margin-bottom: 12px;
  }
}
</style>
