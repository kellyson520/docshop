function hasValue(value) {
  return value !== undefined && value !== null && value !== ''
}

export function normalizePath(value) {
  return String(value || '').replace(/\\/g, '/').trim()
}

export function isExternalUrl(value) {
  const normalized = normalizePath(value)
  return /^https?:\/\//i.test(normalized) || normalized.startsWith('data:') || normalized.startsWith('blob:')
}

function extractSegmentTail(value, segment) {
  const normalized = normalizePath(value)
  if (!normalized) return ''

  const lower = normalized.toLowerCase()
  const marker = `/${segment}/`
  const markerIndex = lower.lastIndexOf(marker)
  if (markerIndex !== -1) {
    return normalized.slice(markerIndex + 1)
  }

  const relativeMarker = `${segment}/`
  const relativeIndex = lower.lastIndexOf(relativeMarker)
  if (relativeIndex !== -1) {
    return normalized.slice(relativeIndex)
  }

  return ''
}

export function withQuery(path, params = {}) {
  if (!path) return ''

  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (hasValue(value)) {
      search.set(key, String(value))
    }
  })

  const query = search.toString()
  return query ? `${path}?${query}` : path
}

export function resolveApiAssetUrl(assetPath, segment) {
  const value = normalizePath(assetPath)
  if (!value) return ''
  if (isExternalUrl(value)) return value

  const apiPrefix = `/api/v1/${segment}/`
  if (value.startsWith(apiPrefix)) return value
  if (value.startsWith(apiPrefix.slice(1))) return `/${value}`
  if (value.startsWith(`/${segment}/`)) return `/api/v1${value}`
  if (value.startsWith(`${segment}/`)) return `/api/v1/${value}`
  if (value.startsWith('/api/')) return value

  const extracted = extractSegmentTail(value, segment)
  if (extracted) {
    return `/api/v1/${extracted}`
  }

  return value.startsWith('/') ? value : `/api/v1/${value}`
}

export function resolveAvatarUrl(avatarPath) {
  return resolveApiAssetUrl(avatarPath, 'avatars')
}

export function resolveCoverUrl(coverPath) {
  return resolveApiAssetUrl(coverPath, 'covers')
}

export function buildFilePreviewUrl(fileId, options = {}) {
  if (!fileId) return ''
  const { version, authToken, cacheKey } = options
  return withQuery(`/api/v1/files/${fileId}/preview`, {
    version,
    auth_token: authToken,
    _preview: cacheKey,
  })
}

export function buildFilePageUrl(fileId, pageNum, options = {}) {
  if (!fileId || !hasValue(pageNum)) return ''
  const { version, authToken } = options
  return withQuery(`/api/v1/files/${fileId}/pages/${pageNum}`, {
    version,
    auth_token: authToken,
  })
}

export function buildFilePreviewAssetUrl(fileId, assetId, options = {}) {
  if (!fileId || !assetId) return ''
  const { version, authToken } = options
  return withQuery(`/api/v1/files/${fileId}/preview-assets/${assetId}`, {
    version,
    auth_token: authToken,
  })
}

export function buildFileDownloadUrl(fileId, versionId, format) {
  if (!fileId) return ''
  if (!versionId) {
    return `/api/v1/files/${fileId}/download`
  }
  const baseUrl = `/api/v1/files/${fileId}/versions/${versionId}/download`
  return format ? `${baseUrl}/${format}` : baseUrl
}

export function buildFileHtmlUrl(fileId, options = {}) {
  if (!fileId) return ''
  const { version, authToken } = options
  return withQuery(`/api/v1/files/${fileId}/html`, {
    version,
    auth_token: authToken,
  })
}

export function buildFileTextUrl(fileId, options = {}) {
  if (!fileId) return ''
  const { version, authToken } = options
  return withQuery(`/api/v1/files/${fileId}/text`, {
    version,
    auth_token: authToken,
  })
}

export function buildSharePreviewUrl(token, fileId, options = {}) {
  if (!token || !fileId) return ''
  const { version, authToken, ticket, cacheKey } = options
  return withQuery(`/api/v1/share/${token}/files/${fileId}/preview`, {
    version,
    auth_token: authToken,
    ticket,
    _preview: cacheKey,
  })
}

export function buildSharePageUrl(token, fileId, pageNum, options = {}) {
  if (!token || !fileId || !hasValue(pageNum)) return ''
  const { version, authToken, ticket } = options
  return withQuery(`/api/v1/share/${token}/files/${fileId}/pages/${pageNum}`, {
    version,
    auth_token: authToken,
    ticket,
  })
}

export function buildSharePreviewAssetUrl(token, fileId, assetId, options = {}) {
  if (!token || !fileId || !assetId) return ''
  const { version, authToken, ticket } = options
  return withQuery(`/api/v1/share/${token}/files/${fileId}/preview-assets/${assetId}`, {
    version,
    auth_token: authToken,
    ticket,
  })
}

export function buildShareDownloadUrl(token, fileId, versionId, format, options = {}) {
  if (!token || !fileId || !versionId) return ''
  const baseUrl = `/api/v1/share/${token}/files/${fileId}/versions/${versionId}/download`
  return withQuery(format ? `${baseUrl}/${format}` : baseUrl, {
    ticket: options.ticket,
  })
}

export function buildShareFolderDownloadUrl(token, folderId, options = {}) {
  if (!token || !folderId) return ''
  return withQuery(`/api/v1/share/${token}/folders/${folderId}/download`, {
    ticket: options.ticket,
  })
}

export function buildAnnouncementAttachmentUrl(fileId) {
  return buildFileDownloadUrl(fileId)
}
