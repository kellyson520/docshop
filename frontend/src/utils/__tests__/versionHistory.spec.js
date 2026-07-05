
import { describe, it, expect } from 'vitest'
import {
  normalizeVersionHistory,
  buildDiffByNewVersion,
  getVersionDiffStats,
  getVersionPreviewCacheKey,
  hasSameVersionPreviewRefresh,
} from '../versionHistory.js'

describe('version history diff ownership', () => {
  const versions = [
    { id: 'v1-id', version: 1 },
    { id: 'v2-id', version: 2 }
  ]
  const diffs = [
    {
      id: 'diff-1-2',
      old_version: 1,
      new_version: 2,
      diff_data: { stats: { paragraphs_modified: 1 } }
    }
  ]

  it('sorts newest version first regardless of API order', () => {
    expect(normalizeVersionHistory(versions).map((item) => item.version)).toEqual([2, 1])
  })

  it('assigns v1 to v2 changes to v2 only', () => {
    const map = buildDiffByNewVersion(versions, diffs)

    expect(getVersionDiffStats(versions[0], map)).toBeNull()
    expect(getVersionDiffStats(versions[1], map)).toEqual({ paragraphs_modified: 1 })
  })

  it('matches numeric and string version numbers consistently', () => {
    const map = buildDiffByNewVersion(versions, [{ ...diffs[0], new_version: '2' }])

    expect(getVersionDiffStats(versions[1], map)).toEqual({ paragraphs_modified: 1 })
  })

  it('prefers preview refresh token when building preview cache keys', () => {
    expect(getVersionPreviewCacheKey({
      id: 'version-id',
      version: 2,
      preview_refresh_token: 'refresh-token-2',
    })).toBe('refresh-token-2')
    expect(getVersionPreviewCacheKey({ id: 'version-id', version: 2 })).toBe('version-id')
  })

  it('detects same-version rebuilds when refresh token changes', () => {
    expect(hasSameVersionPreviewRefresh(2, 'old-token', {
      id: 'version-id',
      version: 2,
      preview_refresh_token: 'new-token',
    })).toBe(true)
    expect(hasSameVersionPreviewRefresh(2, 'same-token', {
      id: 'version-id',
      version: 2,
      preview_refresh_token: 'same-token',
    })).toBe(false)
    expect(hasSameVersionPreviewRefresh(1, 'old-token', {
      id: 'version-id',
      version: 2,
      preview_refresh_token: 'new-token',
    })).toBe(false)
  })
})
