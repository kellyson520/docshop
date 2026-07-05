import { buildShareAbsoluteUrl, buildShareHomePath } from '@/utils/shareRoute'

const PREVIEWABLE_TYPES = new Set(['docx', 'doc', 'pdf'])
const ACTIVE_STATUSES = new Set(['queued', 'pdf_generating', 'pdf_ready', 'images_generating'])
const KNOWN_STATUSES = new Set([
  'missing',
  'queued',
  'pdf_generating',
  'pdf_ready',
  'images_generating',
  'ready',
  'failed',
  'interrupted',
  'unsupported',
])

export function shareResourceKey(resourceType, resourceId) {
  return `${resourceType || 'project'}:${resourceId || ''}`
}

export function buildShareUrl(token, origin = '') {
  return buildShareAbsoluteUrl(token, origin)
}

function shareTokenRecencyValue(token) {
  return String(token?.updated_at || token?.created_at || '')
}

export function indexLatestShareTokensByResource(tokens = []) {
  return (tokens || []).reduce((accumulator, token) => {
    const key = shareResourceKey(token?.resource_type, token?.resource_id)
    const current = accumulator[key]
    if (!current || shareTokenRecencyValue(token) >= shareTokenRecencyValue(current)) {
      accumulator[key] = token
    }
    return accumulator
  }, {})
}

export function mergeCreatedShareToken({ project, files, shareTokensByResource, tokenPayload }) {
  const resourceType = tokenPayload?.resource_type || 'project'
  const resourceId = tokenPayload?.resource_id || ''
  const key = shareResourceKey(resourceType, resourceId)
  const token = tokenPayload?.token || ''
  const trackedToken = {
    ...tokenPayload,
    token,
    share_url: tokenPayload?.share_url || buildShareHomePath(token),
  }

  const nextShareTokensByResource = {
    ...(shareTokensByResource || {}),
    [key]: trackedToken,
  }

  let nextProject = project
  let nextFiles = files || []
  if (resourceType === 'project' && project?.id === resourceId) {
    nextProject = { ...project, share_token: token, latest_share_token: trackedToken }
  }
  if (resourceType === 'file') {
    nextFiles = nextFiles.map((file) => (
      file.id === resourceId
        ? { ...file, share_token: token, latest_share_token: trackedToken }
        : file
    ))
  }

  return {
    project: nextProject,
    files: nextFiles,
    shareTokensByResource: nextShareTokensByResource,
  }
}

export function normalizePreviewStatusRow(file, row = null) {
  const fallbackStatus = PREVIEWABLE_TYPES.has((file?.file_type || '').toLowerCase()) ? 'missing' : 'unsupported'
  const source = row || {}
  let status = source.status || fallbackStatus
  if (!KNOWN_STATUSES.has(status)) {
    status = fallbackStatus === 'unsupported' ? 'unsupported' : 'missing'
  }
  const normalized = {
    ...source,
    file_id: source.file_id || file?.id,
    file_type: source.file_type || file?.file_type,
    status,
    progress: Number(source.progress || 0),
    storage_bytes: Number(source.storage_bytes || 0),
    pdf_bytes: Number(source.pdf_bytes || 0),
    image_bytes: Number(source.image_bytes || 0),
  }
  if (!source.status || !KNOWN_STATUSES.has(source.status)) {
    normalized.stage = normalized.status === 'missing' ? '预览状态未知，需重新生成' : '该类型暂不支持预览缓存'
  }
  return normalized
}

export function isPreviewActiveStatus(status) {
  return ACTIVE_STATUSES.has(status)
}

export function previewStatusLabel(status) {
  const map = {
    missing: '缺失',
    queued: '排队中',
    pdf_generating: 'PDF生成',
    pdf_ready: 'PDF就绪',
    images_generating: '图片生成',
    ready: '已就绪',
    failed: '失败',
    interrupted: '已中断',
    unsupported: '不支持',
  }
  return map[status] || '缺失'
}
