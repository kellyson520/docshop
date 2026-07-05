import { get, post, del, upload, download } from './client'

/**
 * 上传文件到项目
 * @param {number} projectId - 项目ID
 * @param {File} file - 文件对象
 * @param {string} [changelog] - 变更说明
 * @param {Function} [onProgress] - 进度回调函数
 * @returns {Promise<Object>}
 */
export function uploadFile(projectId, file, changelog, onProgress, options = {}) {
  const formData = new FormData()
  formData.append('file', file)
  if (changelog) {
    formData.append('changelog', changelog)
  }
  if (options?.folder_id) {
    formData.append('folder_id', options.folder_id)
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
  return download(`/files/${fileId}/versions/${versionId}/download`)
}

/**
 * 删除文件
 * @param {number} fileId - 文件ID
 * @returns {Promise<void>}
 */
export function deleteFile(fileId) {
  return del(`/files/${fileId}`)
}

/**
 * 获取管理员预览生成状态列表
 * @param {Object} filters - project_id/status/file_type filters
 * @returns {Promise<Object>}
 */
export function getPreviewStatuses(filters = {}) {
  const params = {}
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params[key] = value
    }
  })
  return get('/admin/files/previews', params)
}

/**
 * 入队生成或重建预览
 * @param {Array<string>} fileIds - empty means bulk missing/failed/interrupted
 * @param {Object} options - { force }
 * @returns {Promise<Object>}
 */
export function enqueuePreviewGeneration(fileIds = [], options = {}) {
  return post('/admin/files/preconvert', {
    file_ids: fileIds,
    force: Boolean(options.force),
  })
}

/**
 * 清理单个文件的生成型预览缓存
 * @param {string} fileId
 * @returns {Promise<Object>}
 */
export function clearPreviewCache(fileId) {
  return del(`/admin/files/${fileId}/preview-cache`)
}

/**
 * 批量清理指定状态的预览缓存
 * @param {Object} payload
 * @returns {Promise<Object>}
 */
export function cleanupPreviewCaches(payload = {}) {
  return post('/admin/files/preview-cache/cleanup', payload)
}
