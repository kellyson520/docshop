/**
 * 确认对话框组合式函数
 * 提供统一的确认对话框封装，简化删除确认、操作确认等场景的使用
 */

import { ElMessageBox } from 'element-plus'

/**
 * 确认对话框选项
 * @typedef {Object} ConfirmOptions
 * @property {string} [title='确认'] - 对话框标题
 * @property {string} [message=''] - 对话框消息内容
 * @property {string} [confirmButtonText='确认'] - 确认按钮文本
 * @property {string} [cancelButtonText='取消'] - 取消按钮文本
 * @property {string} [type='info'] - 对话框类型 (success/warning/info/error)
 * @property {string} [confirmButtonClass=''] - 确认按钮自定义类名
 * @property {boolean} [closeOnClickModal=true] - 点击遮罩是否关闭
 * @property {boolean} [showClose=true] - 是否显示关闭按钮
 */

/**
 * 使用确认对话框
 * @returns {Object} 确认对话框方法
 */
export function useConfirm() {
  /**
   * 显示确认对话框
   * @param {ConfirmOptions} options - 对话框选项
   * @returns {Promise} 用户点击确认时 resolve，点击取消时 reject
   */
  const confirm = (options = {}) => {
    const {
      title = '确认',
      message = '',
      confirmButtonText = '确认',
      cancelButtonText = '取消',
      type = 'info',
      confirmButtonClass = '',
      closeOnClickModal = true,
      showClose = true
    } = options

    return ElMessageBox.confirm(message, title, {
      confirmButtonText,
      cancelButtonText,
      type,
      confirmButtonClass,
      closeOnClickModal,
      showClose,
      dangerouslyUseHTMLString: false
    })
  }

  /**
   * 删除确认对话框
   * @param {ConfirmOptions} options - 对话框选项
   * @returns {Promise} 用户点击确认时 resolve，点击取消时 reject
   */
  const confirmDelete = (options = {}) => {
    const {
      title = '确认删除',
      message = '此操作不可恢复，是否继续？',
      confirmButtonText = '删除',
      cancelButtonText = '取消',
      type = 'warning'
    } = options

    return confirm({
      title,
      message,
      confirmButtonText,
      cancelButtonText,
      type,
      confirmButtonClass: 'el-button--danger'
    })
  }

  /**
   * 危险操作确认对话框
   * @param {ConfirmOptions} options - 对话框选项
   * @returns {Promise} 用户点击确认时 resolve，点击取消时 reject
   */
  const confirmDanger = (options = {}) => {
    const {
      title = '危险操作',
      message = '此操作具有风险，请确认是否继续？',
      confirmButtonText = '确认执行',
      cancelButtonText = '取消',
      type = 'error'
    } = options

    return confirm({
      title,
      message,
      confirmButtonText,
      cancelButtonText,
      type,
      confirmButtonClass: 'el-button--danger'
    })
  }

  /**
   * 保存确认对话框
   * @param {ConfirmOptions} options - 对话框选项
   * @returns {Promise} 用户点击确认时 resolve，点击取消时 reject
   */
  const confirmSave = (options = {}) => {
    const {
      title = '保存确认',
      message = '是否保存当前更改？',
      confirmButtonText = '保存',
      cancelButtonText = '不保存',
      type = 'info'
    } = options

    return confirm({
      title,
      message,
      confirmButtonText,
      cancelButtonText,
      type,
      confirmButtonClass: 'el-button--primary'
    })
  }

  /**
   * 离开确认对话框（用于未保存更改时）
   * @param {ConfirmOptions} options - 对话框选项
   * @returns {Promise} 用户点击确认时 resolve，点击取消时 reject
   */
  const confirmLeave = (options = {}) => {
    const {
      title = '确认离开',
      message = '您有未保存的更改，确定要离开吗？',
      confirmButtonText = '离开',
      cancelButtonText = '留在当前页',
      type = 'warning'
    } = options

    return confirm({
      title,
      message,
      confirmButtonText,
      cancelButtonText,
      type
    })
  }

  /**
   * 自定义确认对话框
   * @param {string} title - 对话框标题
   * @param {string} message - 对话框消息
   * @param {string} [type='info'] - 对话框类型
   * @returns {Promise} 用户点击确认时 resolve，点击取消时 reject
   */
  const confirmAction = (title, message, type = 'info') => {
    return confirm({
      title,
      message,
      type
    })
  }

  return {
    confirm,
    confirmDelete,
    confirmDanger,
    confirmSave,
    confirmLeave,
    confirmAction
  }
}

export default useConfirm