/**
 * 分享相关 API
 * 使用封装的 get/post/download 方法
 */

import { get, post, put, del, download } from './client'

export function getShareProject(token, config = {}) {
  return get(`/share/${token}`, undefined, config)
}

export function unlockShareAccess(token, password, config = {}) {
  return post(`/share/${token}/unlock`, { password }, config)
}

export function heartbeatShareAccess(token, config = {}) {
  return post(`/share/${token}/grant/heartbeat`, {}, config)
}

export function releaseShareAccess(token, config = {}) {
  return post(`/share/${token}/grant/release`, {}, config)
}

export function issueShareResourceTicket(token, data, config = {}) {
  return post(`/share/${token}/resource-ticket`, data, config)
}

export function getShareFile(token, fileId, config = {}) {
  return get(`/share/${token}/files/${fileId}`, undefined, config)
}

export function getShareVersions(token, fileId, config = {}) {
  return get(`/share/${token}/files/${fileId}/versions`, undefined, config)
}

export function getShareDiffs(token, fileId, params, config = {}) {
  return get(`/share/${token}/files/${fileId}/diffs`, params, config)
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


export function listShareTokens() {
  return get('/share-tokens')
}

export function createShareToken(data) {
  return post('/share-tokens', data)
}

export function updateShareToken(id, data) {
  return put(`/share-tokens/${id}`, data)
}

export function regenerateShareToken(id) {
  return post(`/share-tokens/${id}/regenerate`, {})
}

export function deleteShareToken(id) {
  return del(`/share-tokens/${id}`)
}

export function getSharePolicy() {
  return get('/share-tokens/policy')
}

export function updateSharePolicy(data) {
  return put('/share-tokens/policy', data)
}
