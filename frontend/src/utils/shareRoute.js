import { withQuery } from '@/utils/resourceUrl'

function normalizeSegment(value) {
  return encodeURIComponent(String(value || '').trim())
}

export function buildShareHomePath(token) {
  const normalizedToken = normalizeSegment(token)
  return normalizedToken ? `/s/${normalizedToken}` : ''
}

export function buildShareFilePath(token, fileId) {
  const basePath = buildShareHomePath(token)
  const normalizedFileId = normalizeSegment(fileId)
  if (!basePath || !normalizedFileId) return ''
  return `${basePath}/files/${normalizedFileId}`
}

export function buildShareDiffPath(token, fileId, query = {}) {
  const basePath = buildShareHomePath(token)
  const normalizedFileId = normalizeSegment(fileId)
  if (!basePath || !normalizedFileId) return ''
  return withQuery(`${basePath}/diff/${normalizedFileId}`, query)
}

export function buildSharePreviewPath(token, fileId) {
  const basePath = buildShareHomePath(token)
  const normalizedFileId = normalizeSegment(fileId)
  if (!basePath || !normalizedFileId) return ''
  return `${basePath}/preview/${normalizedFileId}`
}

export function buildShareAbsoluteUrl(token, origin = '') {
  const path = buildShareHomePath(token)
  if (!path) return ''
  const base = origin || (typeof window !== 'undefined' ? window.location.origin : '')
  return `${base}${path}`
}
