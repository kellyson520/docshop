/**
 * 错误处理系统
 * 提供统一的错误分类、错误码映射和错误处理功能
 */

import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

/**
 * 错误类型枚举
 * 用于对错误进行分类，便于采取不同的处理策略
 */
export const ErrorTypes = {
  NETWORK: 'network',      // 网络错误（连接失败、超时等）
  AUTH: 'auth',            // 认证错误（登录失败、Token过期等）
  VALIDATION: 'validation', // 校验错误（参数校验失败等）
  SERVER: 'server',        // 服务器错误（500错误等）
  BUSINESS: 'business',    // 业务错误（业务逻辑错误）
  UNKNOWN: 'unknown'       // 未知错误
}

/**
 * 错误码映射表
 * 将后端返回的错误码映射为前端可处理的错误信息
 * @property {string} type - 错误类型
 * @property {string} message - 错误提示消息
 * @property {string} [action] - 特殊处理动作（如 logout 表示需要登出）
 */
export const ErrorCodeMap = {
  // 参数校验类错误 (10000-19999) — 预留给前端校验
  10001: { type: ErrorTypes.VALIDATION, message: '参数错误' },
  10002: { type: ErrorTypes.VALIDATION, message: '请求数据格式错误' },

  // 认证授权类错误 (20000-29999) — 对齐后端 exceptions.py
  20001: { type: ErrorTypes.AUTH, message: '用户名或密码错误', action: 'none' },
  20004: { type: ErrorTypes.AUTH, message: '权限不足，无法访问该资源', action: 'none' },

  // 业务逻辑类错误 (30000-39999)
  30001: { type: ErrorTypes.BUSINESS, message: '资源不存在或已被删除' },

  // 文件/请求相关错误 (40000-49999) — 对齐后端
  40001: { type: ErrorTypes.VALIDATION, message: '参数校验失败' },
  40002: { type: ErrorTypes.VALIDATION, message: '文件校验失败' },
  40003: { type: ErrorTypes.VALIDATION, message: '请求过于频繁，请稍后再试' },
  40004: { type: ErrorTypes.VALIDATION, message: '资源冲突，数据已存在' },

  // 差异计算/服务错误 (50000-59999)
  50001: { type: ErrorTypes.SERVER, message: '差异计算失败' },
  50002: { type: ErrorTypes.SERVER, message: '数据库操作失败' },
  50003: { type: ErrorTypes.SERVER, message: '文件存储失败' },
  50004: { type: ErrorTypes.SERVER, message: '外部服务调用失败' },

  // 服务器内部错误 (90000-99999)
  99999: { type: ErrorTypes.SERVER, message: '服务器内部错误' }
}

/**
 * 错误处理器类
 * 提供统一的错误处理、解析和反馈功能
 */
export class ErrorHandler {
  /**
   * 处理错误的主入口方法
   * @param {Error|Object} error - 错误对象
   * @param {Object} options - 处理选项
   * @param {boolean} [options.silent=false] - 是否静默处理（不显示提示）
   * @param {string} [options.fallbackMessage='操作失败'] - 默认错误消息
   * @param {Function} [options.onHandled] - 错误处理完成后的回调
   * @returns {Object} 解析后的错误信息对象
   */
  static handle(error, options = {}) {
    const { 
      silent = false, 
      fallbackMessage = '操作失败，请稍后重试',
      onHandled 
    } = options
    
    // 解析错误信息
    const errorInfo = this.parseError(error)
    
    // 记录错误日志（开发调试使用）
    if (process.env.NODE_ENV === 'development') {
      console.error('[ErrorHandler]', errorInfo)
    }
    
    // 根据错误类型执行对应的处理策略
    this.executeStrategy(errorInfo)
    
    // 显示错误消息（非静默模式下）
    if (!silent) {
      this.showErrorMessage(errorInfo.message || fallbackMessage)
    }
    
    // 执行回调
    if (typeof onHandled === 'function') {
      onHandled(errorInfo)
    }
    
    return errorInfo
  }
  
  /**
   * 根据错误类型执行对应的处理策略
   * @param {Object} errorInfo - 解析后的错误信息
   */
  static executeStrategy(errorInfo) {
    switch (errorInfo.type) {
      case ErrorTypes.AUTH:
        this.handleAuthError(errorInfo)
        break
      case ErrorTypes.NETWORK:
        this.handleNetworkError(errorInfo)
        break
      case ErrorTypes.VALIDATION:
        // 表单校验错误通常在表单组件内处理，这里不做全局提示
        break
      case ErrorTypes.SERVER:
        this.handleServerError(errorInfo)
        break
      case ErrorTypes.BUSINESS:
        // 业务错误通常需要具体场景具体处理
        break
      default:
        // 未知错误
        break
    }
  }
  
  /**
   * 处理认证类错误
   * @param {Object} errorInfo - 错误信息
   */
  static handleAuthError(errorInfo) {
    if (errorInfo.action === 'logout') {
      // 清除登录状态并跳转至登录页
      try {
        const authStore = useAuthStore()
        authStore.logout()
      } catch (e) {
        // 如果 store 未初始化，手动清除
        localStorage.removeItem('access_token')
        window.location.href = '/login?expired=1'
      }
    }
  }
  
  /**
   * 处理网络类错误
   * @param {Object} errorInfo - 错误信息
   */
  static handleNetworkError(errorInfo) {
    // 网络错误提示用户检查网络或重试
    // 具体重试逻辑由调用方实现
    console.warn('[Network Error]', errorInfo.message)
  }
  
  /**
   * 处理服务器类错误
   * @param {Object} errorInfo - 错误信息
   */
  static handleServerError(errorInfo) {
    // 服务器错误通常需要记录并提示用户稍后重试
    console.error('[Server Error]', errorInfo)
  }
  
  /**
   * 显示错误消息
   * @param {string} message - 错误消息
   */
  static showErrorMessage(message) {
    ElMessage.error(message)
  }
  
  /**
   * 解析错误对象，提取有用的错误信息
   * @param {Error|Object} error - 错误对象
   * @returns {Object} 标准化的错误信息对象
   */
  static parseError(error) {
    // 处理 axios 错误响应（包含 response.data.code 的情况）
    if (error.response?.data?.code) {
      const code = error.response.data.code
      const mapped = ErrorCodeMap[code]
      return {
        type: mapped?.type || ErrorTypes.BUSINESS,
        code,
        message: error.response.data.message || mapped?.message || '未知错误',
        action: mapped?.action,
        data: error.response.data,
        raw: error
      }
    }
    
    // 处理 HTTP 状态码错误（无业务错误码时）
    if (error.response) {
      const status = error.response.status
      const message = error.response.data?.message || error.response.data?.detail
      
      // 根据 HTTP 状态码判断错误类型
      if (status === 401) {
        return {
          type: ErrorTypes.AUTH,
          code: 20002,
          message: message || '登录已过期，请重新登录',
          action: 'logout',
          raw: error
        }
      }
      
      if (status === 403) {
        return {
          type: ErrorTypes.AUTH,
          code: 20004,
          message: message || '权限不足',
          raw: error
        }
      }
      
      if (status === 422) {
        return {
          type: ErrorTypes.VALIDATION,
          code: 10001,
          message: message || '参数校验失败',
          raw: error
        }
      }
      
      if (status >= 500) {
        return {
          type: ErrorTypes.SERVER,
          code: 99999,
          message: message || '服务器内部错误',
          raw: error
        }
      }
      
      return {
        type: ErrorTypes.BUSINESS,
        code: status,
        message: message || `请求失败 (${status})`,
        raw: error
      }
    }
    
    // 处理网络错误（无响应）
    if (error.request) {
      return {
        type: ErrorTypes.NETWORK,
        code: 0,
        message: '网络连接失败，请检查网络设置',
        raw: error
      }
    }
    
    // 处理请求配置错误
    if (error.message?.includes('timeout')) {
      return {
        type: ErrorTypes.NETWORK,
        code: -2,
        message: '请求超时，请稍后重试',
        raw: error
      }
    }
    
    // 默认未知错误
    return {
      type: ErrorTypes.UNKNOWN,
      code: -1,
      message: error.message || '发生未知错误',
      raw: error
    }
  }
  
  /**
   * 判断错误是否为特定类型
   * @param {Object} errorInfo - 解析后的错误信息
   * @param {string} type - 错误类型
   * @returns {boolean}
   */
  static isType(errorInfo, type) {
    return errorInfo.type === type
  }
  
  /**
   * 判断错误是否需要重试
   * @param {Object} errorInfo - 解析后的错误信息
   * @returns {boolean}
   */
  static isRetryable(errorInfo) {
    return errorInfo.type === ErrorTypes.NETWORK || 
           errorInfo.type === ErrorTypes.SERVER
  }
}

export default ErrorHandler