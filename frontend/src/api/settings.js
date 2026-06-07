import { get, put, post, upload } from './client'

/**
 * 获取用户设置
 * @returns {Promise<Object>} 用户设置数据
 */
export function getUserSettings() {
  return get('/settings')
}

/**
 * 更新用户设置
 * @param {Object} data - 设置数据
 * @param {Object} [data.profile] - 个人资料设置
 * @param {string} [data.profile.username] - 用户名
 * @param {string} [data.profile.avatar] - 头像URL
 * @param {Object} [data.notifications] - 通知设置
 * @param {boolean} [data.notifications.email] - 邮件通知
 * @param {boolean} [data.notifications.push] - 推送通知
 * @param {Object} [data.appearance] - 界面设置
 * @param {string} [data.appearance.theme] - 主题 (light/dark/system)
 * @param {number} [data.appearance.default_page_size] - 默认每页条数
 * @param {Object} [data.tracking] - 追踪设置
 * @param {boolean} [data.tracking.enabled] - 是否启用追踪
 * @param {boolean} [data.tracking.ip_tracking] - IP追踪
 * @param {boolean} [data.tracking.device_tracking] - 设备追踪
 * @param {boolean} [data.tracking.location_tracking] - 位置追踪
 * @returns {Promise<Object>} 更新后的设置数据
 */
export function updateUserSettings(data) {
  return put('/settings', data)
}

/**
 * 修改密码
 * @param {string} oldPassword - 旧密码
 * @param {string} newPassword - 新密码
 * @returns {Promise<void>}
 */
export function changePassword(oldPassword, newPassword) {
  return post('/settings/change-password', {
    old_password: oldPassword,
    new_password: newPassword
  })
}

/**
 * 获取登录设备列表
 * @returns {Promise<Array>} 登录设备列表
 */
export function getLoginDevices() {
  return get('/settings/devices')
}

/**
 * 退出指定设备登录
 * @param {string} deviceId - 设备ID
 * @returns {Promise<void>}
 */
export function logoutDevice(deviceId) {
  return post(`/settings/devices/${deviceId}/logout`)
}

/**
 * 退出所有设备登录
 * @returns {Promise<void>}
 */
export function logoutAllDevices() {
  return post('/settings/devices/logout-all')
}

/**
 * 上传用户头像
 * @param {File} file - 头像文件
 * @param {Function} [onProgress] - 进度回调函数
 * @returns {Promise<Object>} 包含头像URL的响应
 */
export function uploadAvatar(file, onProgress) {
  const formData = new FormData()
  formData.append('avatar', file)
  return upload('/settings/avatar', formData, onProgress)
}
