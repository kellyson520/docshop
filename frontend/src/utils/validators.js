/**
 * 表单校验工具库
 * 提供常用的表单字段校验函数和校验规则生成器
 */

/**
 * 用户名校验
 * @param {string} value - 用户名
 * @returns {true|string} 校验通过返回 true，否则返回错误信息
 */
export const validateUsername = (value) => {
  if (!value || value.trim() === '') {
    return '用户名不能为空'
  }
  const trimmed = value.trim()
  if (trimmed.length < 3) {
    return '用户名至少 3 个字符'
  }
  if (trimmed.length > 20) {
    return '用户名最多 20 个字符'
  }
  if (!/^[a-zA-Z0-9_]+$/.test(trimmed)) {
    return '用户名只能包含字母、数字、下划线'
  }
  return true
}

/**
 * 密码校验
 * @param {string} value - 密码
 * @returns {true|string} 校验通过返回 true，否则返回错误信息
 */
export const validatePassword = (value) => {
  if (!value) {
    return '密码不能为空'
  }
  if (value.length < 6) {
    return '密码至少 6 个字符'
  }
  if (value.length > 50) {
    return '密码最多 50 个字符'
  }
  // 可选：增加密码强度校验
  // if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(value)) {
  //   return '密码需包含大小写字母和数字'
  // }
  return true
}

/**
 * 确认密码校验
 * @param {string} value - 确认密码
 * @param {string} originalPassword - 原始密码
 * @returns {true|string} 校验通过返回 true，否则返回错误信息
 */
export const validateConfirmPassword = (value, originalPassword) => {
  if (!value) {
    return '请确认密码'
  }
  if (value !== originalPassword) {
    return '两次输入的密码不一致'
  }
  return true
}

/**
 * 项目名称校验
 * @param {string} value - 项目名称
 * @returns {true|string} 校验通过返回 true，否则返回错误信息
 */
export const validateProjectName = (value) => {
  if (!value || value.trim() === '') {
    return '项目名称不能为空'
  }
  const trimmed = value.trim()
  if (trimmed.length < 2) {
    return '项目名称至少 2 个字符'
  }
  if (trimmed.length > 100) {
    return '项目名称最多 100 个字符'
  }
  return true
}

/**
 * 项目描述校验
 * @param {string} value - 项目描述
 * @returns {true|string} 校验通过返回 true，否则返回错误信息
 */
export const validateProjectDescription = (value) => {
  // 描述是可选字段
  if (!value) {
    return true
  }
  if (value.length > 500) {
    return '项目描述最多 500 个字符'
  }
  return true
}

/**
 * 文件校验
 * @param {File} file - 文件对象
 * @param {Object} [options={}] - 校验选项
 * @param {number} [options.maxSize=52428800] - 最大文件大小（字节），默认 50MB
 * @param {string[]} [options.allowedTypes=['.pdf', '.docx', '.xlsx']] - 允许的文件类型
 * @returns {true|string} 校验通过返回 true，否则返回错误信息
 */
export const validateFile = (file, options = {}) => {
  const { 
    maxSize = 50 * 1024 * 1024, 
    allowedTypes = ['.pdf', '.docx', '.xlsx'] 
  } = options
  
  if (!file) {
    return '请选择文件'
  }
  
  // 大小检查
  if (file.size > maxSize) {
    const maxMB = (maxSize / 1024 / 1024).toFixed(0)
    return `文件大小不能超过 ${maxMB}MB`
  }
  
  // 类型检查
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!allowedTypes.includes(ext)) {
    return `不支持的文件类型: ${ext}，仅支持 ${allowedTypes.join(', ')}`
  }
  
  return true
}

/**
 * 文件列表校验
 * @param {File[]} files - 文件列表
 * @param {Object} [options={}] - 校验选项
 * @param {number} [options.maxCount=1] - 最大文件数量
 * @param {number} [options.maxTotalSize=52428800] - 最大总大小（字节）
 * @returns {true|string} 校验通过返回 true，否则返回错误信息
 */
export const validateFileList = (files, options = {}) => {
  const { 
    maxCount = 1, 
    maxTotalSize = 50 * 1024 * 1024 
  } = options
  
  if (!files || files.length === 0) {
    return '请至少选择一个文件'
  }
  
  if (files.length > maxCount) {
    return `最多只能选择 ${maxCount} 个文件`
  }
  
  const totalSize = files.reduce((sum, file) => sum + file.size, 0)
  if (totalSize > maxTotalSize) {
    const maxMB = (maxTotalSize / 1024 / 1024).toFixed(0)
    return `文件总大小不能超过 ${maxMB}MB`
  }
  
  return true
}

/**
 * 变更说明校验
 * @param {string} value - 变更说明
 * @returns {true|string} 校验通过返回 true，否则返回错误信息
 */
export const validateChangelog = (value) => {
  // 变更说明是可选字段
  if (!value) {
    return true
  }
  if (value.length > 1000) {
    return '变更说明最多 1000 个字符'
  }
  return true
}

/**
 * 邮箱校验
 * @param {string} value - 邮箱地址
 * @returns {true|string} 校验通过返回 true，否则返回错误信息
 */
export const validateEmail = (value) => {
  if (!value || value.trim() === '') {
    return '邮箱不能为空'
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(value.trim())) {
    return '请输入有效的邮箱地址'
  }
  return true
}

/**
 * 手机号校验（中国大陆）
 * @param {string} value - 手机号
 * @returns {true|string} 校验通过返回 true，否则返回错误信息
 */
export const validatePhone = (value) => {
  if (!value || value.trim() === '') {
    return '手机号不能为空'
  }
  const phoneRegex = /^1[3-9]\d{9}$/
  if (!phoneRegex.test(value.trim())) {
    return '请输入有效的手机号'
  }
  return true
}

/**
 * 必填字段校验
 * @param {string} value - 字段值
 * @param {string} [fieldName='该字段'] - 字段名称
 * @returns {true|string} 校验通过返回 true，否则返回错误信息
 */
export const validateRequired = (value, fieldName = '该字段') => {
  if (value === undefined || value === null || value === '' || 
      (typeof value === 'string' && value.trim() === '')) {
    return `${fieldName}不能为空`
  }
  return true
}

/**
 * 长度范围校验
 * @param {string} value - 字段值
 * @param {Object} options - 校验选项
 * @param {number} [options.min] - 最小长度
 * @param {number} [options.max] - 最大长度
 * @param {string} [fieldName='该字段'] - 字段名称
 * @returns {true|string} 校验通过返回 true，否则返回错误信息
 */
export const validateLength = (value, options = {}) => {
  const { min, max, fieldName = '该字段' } = options
  const length = value ? value.length : 0
  
  if (min !== undefined && length < min) {
    return `${fieldName}至少 ${min} 个字符`
  }
  if (max !== undefined && length > max) {
    return `${fieldName}最多 ${max} 个字符`
  }
  return true
}

/**
 * 创建 Element Plus 表单校验规则
 * @param {Function|Function[]} validators - 校验函数或校验函数数组
 * @param {string} [trigger='blur'] - 触发时机
 * @returns {Object[]} Element Plus 表单规则数组
 */
export const createRules = (validators, trigger = 'blur') => {
  const validatorList = Array.isArray(validators) ? validators : [validators]
  
  return validatorList.map(fn => ({
    validator: (rule, value, callback) => {
      const result = fn(value)
      if (result === true) {
        callback()
      } else {
        callback(new Error(result))
      }
    },
    trigger
  }))
}

/**
 * 创建带依赖的校验规则（如确认密码）
 * @param {Function} validator - 校验函数，接收 value 和依赖值作为参数
 * @param {Function} getDependency - 获取依赖值的函数
 * @param {string} [trigger='blur'] - 触发时机
 * @returns {Object[]} Element Plus 表单规则数组
 */
export const createDependentRules = (validator, getDependency, trigger = 'blur') => {
  return [{
    validator: (rule, value, callback) => {
      const dependency = getDependency()
      const result = validator(value, dependency)
      if (result === true) {
        callback()
      } else {
        callback(new Error(result))
      }
    },
    trigger
  }]
}

/**
 * 预定义的常用校验规则组合
 */
export const Rules = {
  /**
   * 用户名规则
   */
  username: createRules(validateUsername),
  
  /**
   * 密码规则
   */
  password: createRules(validatePassword),
  
  /**
   * 项目名称规则
   */
  projectName: createRules(validateProjectName),
  
  /**
   * 项目描述规则
   */
  projectDescription: createRules(validateProjectDescription),
  
  /**
   * 邮箱规则
   */
  email: createRules(validateEmail),
  
  /**
   * 手机号规则
   */
  phone: createRules(validatePhone),
  
  /**
   * 变更说明规则
   */
  changelog: createRules(validateChangelog)
}

export default {
  validateUsername,
  validatePassword,
  validateConfirmPassword,
  validateProjectName,
  validateProjectDescription,
  validateFile,
  validateFileList,
  validateChangelog,
  validateEmail,
  validatePhone,
  validateRequired,
  validateLength,
  createRules,
  createDependentRules,
  Rules
}