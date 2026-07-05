import { get, post, put, del } from './client'

/**
 * 获取考试列表
 * @param {Object} [params] - 查询参数
 * @param {number} [params.page] - 页码
 * @param {number} [params.page_size] - 每页数量
 * @param {string} [params.status] - 状态筛选 (upcoming/ongoing/expired)
 * @param {string} [params.keyword] - 搜索关键词
 * @returns {Promise<Object>}
 */
export function getExams(params) {
  return get('/exams', params)
}

/**
 * 获取考试详情
 * @param {number} id - 考试ID
 * @returns {Promise<Object>}
 */
export function getExam(id) {
  return get(`/exams/${id}`)
}

/**
 * 创建考试
 * @param {Object} data - 考试数据
 * @param {string} data.name - 考试名称
 * @param {string} [data.description] - 考试描述
 * @param {string} data.start_time - 开始时间 (ISO格式)
 * @param {string} data.end_time - 结束时间 (ISO格式)
 * @param {number} [data.project_id] - 关联项目ID
 * @param {Object} [data.reminder_settings] - 提醒设置
 * @param {boolean} [data.reminder_settings.enabled] - 是否启用提醒
 * @param {number[]} [data.reminder_settings.minutes_before] - 提前提醒分钟数数组
 * @returns {Promise<Object>}
 */
export function createExam(data) {
  return post('/exams', data)
}

/**
 * 更新考试
 * @param {number} id - 考试ID
 * @param {Object} data - 考试数据
 * @returns {Promise<Object>}
 */
export function updateExam(id, data) {
  return put(`/exams/${id}`, data)
}

/**
 * 删除考试
 * @param {number} id - 考试ID
 * @returns {Promise<void>}
 */
export function deleteExam(id) {
  return del(`/exams/${id}`)
}

/**
 * 获取即将开始的考试
 * @param {number} [minutes] - 查询未来多少分钟内的考试，默认60分钟
 * @returns {Promise<Object[]>}
 */
export function getUpcomingExams(minutes = 60) {
  return get('/exams/upcoming', { minutes })
}

/**
 * 关闭考试提醒
 * @param {number} examId - 考试ID
 * @param {string} reminderType - 提醒类型 (15min/5min/start)
 * @returns {Promise<void>}
 */
export function dismissReminder(examId, reminderType) {
  return post(`/exams/${examId}/dismiss`, { reminder_type: reminderType })
}
