function versionNumber(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number : -1
}

export function getVersionPreviewCacheKey(version) {
  if (!version) return ''
  return String(version.preview_refresh_token || version.id || versionNumber(version.version) || '')
}

export function hasSameVersionPreviewRefresh(currentVersion, currentRefreshToken = '', version = null) {
  if (!version) return false

  const current = versionNumber(currentVersion)
  const next = versionNumber(version?.version)
  if (current < 0 || next < 0 || current !== next) return false

  const latestRefreshToken = version?.preview_refresh_token
  return Boolean(latestRefreshToken) && latestRefreshToken !== currentRefreshToken
}

export function normalizeVersionHistory(versions = []) {
  return [...versions].sort((a, b) => versionNumber(b?.version) - versionNumber(a?.version))
}

export function buildDiffByNewVersion(versions = [], diffs = []) {
  const map = {}

  for (const diff of diffs || []) {
    const newVersion = versionNumber(diff?.new_version)
    if (newVersion < 0) continue

    const version = versions.find((item) => versionNumber(item?.version) === newVersion)
    if (version?.id) map[version.id] = diff
  }

  return map
}

export function getVersionDiffStats(version, diffMap = {}) {
  const diff = diffMap?.[version?.id]
  if (!diff?.diff_data) return null

  try {
    const data = typeof diff.diff_data === 'string' ? JSON.parse(diff.diff_data) : diff.diff_data
    return data?.stats || null
  } catch {
    return null
  }
}

export function isLatestVersion(version, versions = []) {
  const highestVersion = Math.max(...versions.map((item) => versionNumber(item?.version)))
  return versionNumber(version?.version) === highestVersion
}

export function canCompareWithPreviousVersion(version) {
  return versionNumber(version?.version) > 1
}
