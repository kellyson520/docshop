import { get, del, upload } from './client'

/**
 * 上传文件到项目
 * @param {number} projectId - 项目ID
 * @param {File} file - 文件对象
 * @param {string} [changelog] - 变更说明
 * @param {Function} [onProgress] - 进度回调函数
 * @returns {Promise<Object>}
 */
export function uploadFile(projectId, file, changelog, onProgress) {
  const formData = new FormData()
  formData.append('file', file)
  if (changelog) {
    formData.append('changelog', changelog)
  }
  return upload(`/projects/${projectId}/files`, formData, onProgress)
}

/**
 * 上传文件新版本
 * @param {number} fileId - 文件ID
 * @param {File} file - 文件对象
 * @param {string} [changelog] - 变更说明
 * @param {Function} [onProgress] - 进度回调函数
 * @returns {Promise<Object>}
 */
export function uploadVersion(fileId, file, changelog, onProgress) {
  const formData = new FormData()
  formData.append('file', file)
  if (changelog) {
    formData.append('changelog', changelog)
  }
  return upload(`/files/${fileId}/versions`, formData, onProgress)
}

/**
 * 获取文件版本列表
 * @param {number} fileId - 文件ID
 * @returns {Promise<Array>}
 */
export function getFileVersions(fileId) {
  return get(`/files/${fileId}/versions`)
}

/**
 * 下载指定版本文件
 * @param {number} fileId - 文件ID
 * @param {number} versionId - 版本ID
 * @returns {Promise<Blob>}
 */
export function downloadVersion(fileId, versionId) {
  return get(`/files/${fileId}/versions/${versionId}/download`, null, {
    responseType: 'blob'
  })
}

/**
 * 删除文件
 * @param {number} fileId - 文件ID
 * @returns {Promise<void>}
 */
export function deleteFile(fileId) {
  return del(`/files/${fileId}`)
}
