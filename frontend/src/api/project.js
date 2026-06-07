import { get, post, put, del } from './client'

/**
 * 获取项目列表
 * @param {Object} [params] - 查询参数
 * @param {number} [params.page] - 页码
 * @param {number} [params.page_size] - 每页数量
 * @returns {Promise<Object>}
 */
export function getProjects(params) {
  return get('/projects', params)
}

/**
 * 获取项目详情
 * @param {number} id - 项目ID
 * @returns {Promise<Object>}
 */
export function getProject(id) {
  return get(`/projects/${id}`)
}

/**
 * 创建项目
 * @param {Object} data - 项目数据
 * @param {string} data.name - 项目名称
 * @param {string} [data.description] - 项目描述
 * @param {boolean} [data.is_public] - 是否公开
 * @returns {Promise<Object>}
 */
export function createProject(data) {
  return post('/projects', data)
}

/**
 * 更新项目
 * @param {number} id - 项目ID
 * @param {Object} data - 项目数据
 * @returns {Promise<Object>}
 */
export function updateProject(id, data) {
  return put(`/projects/${id}`, data)
}

/**
 * 删除项目
 * @param {number} id - 项目ID
 * @returns {Promise<void>}
 */
export function deleteProject(id) {
  return del(`/projects/${id}`)
}

/**
 * 重新生成项目分享令牌
 * @param {number} id - 项目ID
 * @returns {Promise<Object>}
 */
export function regenerateToken(id) {
  return post(`/projects/${id}/regenerate-token`)
}
