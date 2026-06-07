/**
 * 分享相关 API
 * 使用封装的 get/post/download 方法
 */

import { get, download } from './client'

export function getShareProject(token) {
  return get(`/share/${token}`)
}

export function getShareFile(token, fileId) {
  return get(`/share/${token}/files/${fileId}`)
}

export function getShareVersions(token, fileId) {
  return get(`/share/${token}/files/${fileId}/versions`)
}

export function getShareDiffs(token, fileId, params) {
  return get(`/share/${token}/files/${fileId}/diffs`, params)
}

export function downloadShareVersion(token, fileId, versionId) {
  return download(`/share/${token}/files/${fileId}/versions/${versionId}/download`)
}

/**
 * 以指定格式下载分享文件版本
 * @param {string} token - 分享令牌
 * @param {string} fileId - 文件 ID
 * @param {string} versionId - 版本 ID
 * @param {string} format - 下载格式: 'docx' | 'pdf'
 * @returns {Promise<Blob>} 文件 Blob
 */
export function downloadShareVersionAs(token, fileId, versionId, format) {
  return download(`/share/${token}/files/${fileId}/versions/${versionId}/download/${format}`)
}
