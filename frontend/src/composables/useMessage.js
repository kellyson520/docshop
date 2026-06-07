/**
 * 消息提示组合式函数
 * 提供统一的消息提示封装，简化 ElMessage 和 ElNotification 的使用
 */

import { ElMessage, ElNotification } from 'element-plus'

/**
 * 消息选项
 * @typedef {Object} MessageOptions
 * @property {string} message - 消息内容
 * @property {number} [duration=3000] - 显示时长（毫秒），0 表示不自动关闭
 * @property {boolean} [showClose=true] - 是否显示关闭按钮
 * @property {boolean} [grouping=false] - 是否合并相同内容的消息
 * @property {Function} [onClose] - 关闭时的回调函数
 */

/**
 * 通知选项
 * @typedef {Object} NotificationOptions
 * @property {string} title - 通知标题
 * @property {string} message - 通知内容
 * @property {string} [type='info'] - 通知类型 (success/warning/info/error)
 * @property {number} [duration=4500] - 显示时长（毫秒），0 表示不自动关闭
 * @property {boolean} [showClose=true] - 是否显示关闭按钮
 * @property {string} [position='top-right'] - 通知位置
 * @property {Function} [onClose] - 关闭时的回调函数
 * @property {Function} [onClick] - 点击时的回调函数
 */

/**
 * 使用消息提示
 * @returns {Object} 消息提示方法
 */
export function useMessage() {
  /**
   * 显示成功消息
   * @param {string|MessageOptions} options - 消息内容或选项
   */
  const success = (options) => {
    if (typeof options === 'string') {
      ElMessage.success({
        message: options,
        showClose: true
      })
    } else {
      ElMessage.success({
        showClose: true,
        ...options
      })
    }
  }

  /**
   * 显示错误消息
   * @param {string|MessageOptions} options - 消息内容或选项
   */
  const error = (options) => {
    if (typeof options === 'string') {
      ElMessage.error({
        message: options,
        showClose: true,
        duration: 5000
      })
    } else {
      ElMessage.error({
        showClose: true,
        duration: 5000,
        ...options
      })
    }
  }

  /**
   * 显示警告消息
   * @param {string|MessageOptions} options - 消息内容或选项
   */
  const warning = (options) => {
    if (typeof options === 'string') {
      ElMessage.warning({
        message: options,
        showClose: true
      })
    } else {
      ElMessage.warning({
        showClose: true,
        ...options
      })
    }
  }

  /**
   * 显示信息消息
   * @param {string|MessageOptions} options - 消息内容或选项
   */
  const info = (options) => {
    if (typeof options === 'string') {
      ElMessage.info({
        message: options,
        showClose: true
      })
    } else {
      ElMessage.info({
        showClose: true,
        ...options
      })
    }
  }

  /**
   * 显示加载消息
   * @param {string} message - 加载提示文本
   * @returns {Function} 关闭加载消息的函数
   */
  const loading = (message = '加载中...') => {
    const instance = ElMessage({
      message,
      type: 'info',
      duration: 0,
      icon: 'Loading',
      showClose: false
    })
    
    return () => {
      instance.close()
    }
  }

  /**
   * 显示通知
   * @param {NotificationOptions} options - 通知选项
   */
  const notify = (options) => {
    ElNotification({
      position: 'top-right',
      showClose: true,
      ...options
    })
  }

  /**
   * 显示成功通知
   * @param {string} title - 通知标题
   * @param {string} [message=''] - 通知内容
   */
  const notifySuccess = (title, message = '') => {
    notify({
      title,
      message,
      type: 'success'
    })
  }

  /**
   * 显示错误通知
   * @param {string} title - 通知标题
   * @param {string} [message=''] - 通知内容
   */
  const notifyError = (title, message = '') => {
    notify({
      title,
      message,
      type: 'error',
      duration: 0
    })
  }

  /**
   * 显示警告通知
   * @param {string} title - 通知标题
   * @param {string} [message=''] - 通知内容
   */
  const notifyWarning = (title, message = '') => {
    notify({
      title,
      message,
      type: 'warning'
    })
  }

  /**
   * 显示信息通知
   * @param {string} title - 通知标题
   * @param {string} [message=''] - 通知内容
   */
  const notifyInfo = (title, message = '') => {
    notify({
      title,
      message,
      type: 'info'
    })
  }

  /**
   * 关闭所有消息
   */
  const closeAll = () => {
    ElMessage.closeAll()
  }

  /**
   * 关闭所有通知
   */
  const closeAllNotifications = () => {
    ElNotification.closeAll()
  }

  return {
    // 消息方法
    success,
    error,
    warning,
    info,
    loading,
    closeAll,
    
    // 通知方法
    notify,
    notifySuccess,
    notifyError,
    notifyWarning,
    notifyInfo,
    closeAllNotifications
  }
}

export default useMessage