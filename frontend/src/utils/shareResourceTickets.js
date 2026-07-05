import { issueShareResourceTicket } from '@/api/share'
import {
  buildShareDownloadUrl,
  buildShareFolderDownloadUrl,
  buildSharePageUrl,
  buildSharePreviewAssetUrl,
  buildSharePreviewUrl,
} from '@/utils/resourceUrl'

function hasActiveShareGrant(session) {
  return Boolean(session?.grantToken?.value)
}

function hasActivePublicAccessGrant(session) {
  return Boolean(session?.grantToken?.value)
}

function buildDirectShareResourceUrl({
  token,
  kind,
  fileId,
  version,
  versionId,
  pageNum,
  assetId,
  folderId,
  format,
  ticket,
  cacheKey,
}) {
  switch (kind) {
    case 'preview':
      return buildSharePreviewUrl(token, fileId, { version, ticket, cacheKey })
    case 'page':
      return buildSharePageUrl(token, fileId, pageNum, { version, ticket })
    case 'preview_asset':
      return buildSharePreviewAssetUrl(token, fileId, assetId, { version, ticket })
    case 'download_original':
      return buildShareDownloadUrl(token, fileId, versionId, undefined, { ticket })
    case 'download_converted':
      return buildShareDownloadUrl(token, fileId, versionId, format, { ticket })
    case 'folder_download':
      return buildShareFolderDownloadUrl(token, folderId, { ticket })
    default:
      throw new Error(`Unsupported share resource kind: ${kind}`)
  }
}

export async function getShareResourceUrl(options) {
  const {
    token,
    session,
    accessSession,
    kind,
    fileId,
    version,
    versionId,
    pageNum,
    assetId,
    folderId,
    format,
    cacheKey,
  } = options || {}

  const activeSession = hasActivePublicAccessGrant(accessSession)
    ? {
        headers: typeof accessSession?.withAccessHeaders === 'function'
          ? accessSession.withAccessHeaders()
          : {},
      }
    : hasActiveShareGrant(session)
      ? {
          headers: typeof session?.withShareHeaders === 'function'
            ? session.withShareHeaders()
            : {},
        }
      : null

  if (!activeSession) {
    return buildDirectShareResourceUrl({
      token,
      kind,
      fileId,
      version,
      versionId,
      pageNum,
      assetId,
      folderId,
      format,
      cacheKey,
    })
  }

  const payload = await issueShareResourceTicket(
    token,
    {
      kind,
      file_id: fileId,
      version_id: versionId,
      page_num: pageNum,
      asset_id: assetId,
      folder_id: folderId,
      format,
    },
    activeSession,
  )

  return buildDirectShareResourceUrl({
    token,
    kind,
    fileId,
    version,
    versionId,
    pageNum,
    assetId,
    folderId,
    format,
    ticket: payload?.ticket,
    cacheKey,
  })
}
