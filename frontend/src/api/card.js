/**
 * 卡片管理 API
 * 提供卡片列表、详情、版本管理、多版本对比等接口
 */

import client, { get, post, put, del, upload, download } from './client'

export const cardApi = {
  /**
   * 获取卡片列表
   * @param {Object} params - 查询参数
   * @param {string} [params.keyword] - 搜索关键词
   * @param {string} [params.file_type] - 文件类型 (pdf/docx/xlsx)
   * @param {string} [params.category] - 分类
   * @param {string[]} [params.tags] - 标签
   * @param {number} [params.page] - 页码
   * @param {number} [params.page_size] - 每页数量
   * @returns {Promise} 卡片列表
   */
  getList: (params) => get('/cards', params),

  /**
   * 获取卡片详情
   * @param {string|number} id - 卡片 ID
   * @returns {Promise} 卡片详情
   */
  getDetail: (id) => get(`/cards/${id}`),

  /**
   * 创建卡片
   * @param {Object} data - 卡片数据
   * @returns {Promise} 创建结果
   */
  create: (data) => post('/cards', data),

  /**
   * 更新卡片信息
   * @param {string|number} id - 卡片 ID
   * @param {Object} data - 更新数据
   * @param {string} [data.display_name] - 显示名称
   * @param {string} [data.description] - 描述
   * @param {string[]} [data.tags] - 标签
   * @param {string} [data.category] - 分类
   * @returns {Promise} 更新结果
   */
  updateInfo: (id, data) => put(`/cards/${id}/info`, data),

  /**
   * 删除卡片
   * @param {string|number} id - 卡片 ID
   * @returns {Promise} 删除结果
   */
  delete: (id) => del(`/cards/${id}`),

  /**
   * 上传封面图片
   * @param {string|number} id - 卡片 ID
   * @param {File} file - 封面图片文件
   * @param {Function} [onProgress] - 上传进度回调
   * @returns {Promise} 上传结果
   */
  uploadCover: (id, file, onProgress) => {
    const formData = new FormData()
    formData.append('cover', file)
    return upload(`/cards/${id}/cover`, formData, onProgress)
  },

  /**
   * 上传文件（创建新版本）
   * @param {string|number} cardId - 卡片 ID
   * @param {File} file - 文件
   * @param {Object} [options] - 上传选项
   * @param {string} [options.changelog] - 变更说明
   * @param {Function} [options.onProgress] - 上传进度回调
   * @returns {Promise} 上传结果
   */
  uploadFile: (cardId, file, options = {}) => {
    const formData = new FormData()
    formData.append('file', file)
    if (options.changelog) {
      formData.append('changelog', options.changelog)
    }
    return upload(`/cards/${cardId}/versions`, formData, options.onProgress)
  },

  /**
   * 获取版本列表
   * @param {string|number} cardId - 卡片 ID
   * @returns {Promise} 版本列表
   */
  getVersions: (cardId) => get(`/cards/${cardId}/versions`),

  /**
   * 获取版本详情
   * @param {string|number} cardId - 卡片 ID
   * @param {string|number} versionId - 版本 ID
   * @returns {Promise} 版本详情
   */
  getVersionDetail: (cardId, versionId) => get(`/cards/${cardId}/versions/${versionId}`),

  /**
   * 多版本对比
   * @param {string|number} cardId - 卡片 ID
   * @param {number[]} versionIds - 要对比的版本 ID 列表
   * @returns {Promise} 对比结果
   */
  compareVersions: (cardId, versionIds) =>
    post(`/cards/${cardId}/versions/compare`, { version_ids: versionIds }),

  /**
   * 两版本对比
   * @param {string|number} cardId - 卡片 ID
   * @param {number} versionId1 - 版本 1 ID
   * @param {number} versionId2 - 版本 2 ID
   * @returns {Promise} 对比结果
   */
  compareTwoVersions: (cardId, versionId1, versionId2) =>
    post(`/cards/${cardId}/versions/compare-two`, { version_id_1: versionId1, version_id_2: versionId2 }),

  /**
   * 下载最新版本
   * @param {string|number} cardId - 卡片 ID
   * @returns {Promise<Blob>} 文件 Blob
   */
  downloadLatest: (cardId) => download(`/cards/${cardId}/download`),

  /**
   * 下载指定版本
   * @param {string|number} cardId - 卡片 ID
   * @param {string|number} versionId - 版本 ID
   * @returns {Promise<Blob>} 文件 Blob
   */
  downloadVersion: (cardId, versionId) =>
    download(`/cards/${cardId}/versions/${versionId}/download`),

  /**
   * 获取下载排行榜
   * @param {Object} [params] - 查询参数
   * @param {number} [params.limit] - 数量限制
   * @param {string} [params.period] - 时间范围 (day/week/month/all)
   * @returns {Promise} 排行榜数据
   */
  getDownloadRank: (params) => get('/cards/rank/download', params),

  /**
   * 获取访问排行榜
   * @param {Object} [params] - 查询参数
   * @param {number} [params.limit] - 数量限制
   * @param {string} [params.period] - 时间范围 (day/week/month/all)
   * @returns {Promise} 排行榜数据
   */
  getVisitRank: (params) => get('/cards/rank/visit', params),

  /**
   * 获取分类列表
   * @returns {Promise} 分类列表
   */
  getCategories: () => get('/cards/categories'),

  /**
   * 获取标签列表
   * @param {Object} [params] - 查询参数
   * @param {string} [params.keyword] - 搜索关键词
   * @returns {Promise} 标签列表
   */
  getTags: (params) => get('/cards/tags', params),

  /**
   * 记录访问
   * @param {string|number} cardId - 卡片 ID
   * @returns {Promise} 记录结果
   */
  recordVisit: (cardId) => post(`/cards/${cardId}/visit`),

  /**
   * 获取通知列表
   * @param {Object} [params] - 查询参数
   * @param {boolean} [params.unread_only] - 仅未读
   * @returns {Promise} 通知列表
   */
  getNotices: (params) => get('/notices', params),

  /**
   * 标记通知已读
   * @param {string|number} noticeId - 通知 ID
   * @returns {Promise} 标记结果
   */
  markNoticeRead: (noticeId) => put(`/notices/${noticeId}/read`),

  /**
   * 标记所有通知已读
   * @returns {Promise} 标记结果
   */
  markAllNoticesRead: () => put('/notices/read-all')
}

export default cardApi
