/**
 * 验证器函数单元测试
 * 测试表单字段验证功能
 */

import { describe, it, expect } from 'vitest'
import {
  validateUsername,
  validatePassword,
  validateProjectName,
  validateFile,
  validateConfirmPassword,
  validateProjectDescription,
  validateFileList,
  validateChangelog,
  validateEmail,
  validatePhone,
  validateRequired,
  validateLength,
  createRules,
  createDependentRules,
  Rules
} from '../validators.js'

describe('验证器函数', () => {
  /**
   * 用户名校验测试
   */
  describe('validateUsername', () => {
    it('空用户名应该返回错误', () => {
      expect(validateUsername('')).toBe('用户名不能为空')
    })

    it('null 用户名应该返回错误', () => {
      expect(validateUsername(null)).toBe('用户名不能为空')
    })

    it('undefined 用户名应该返回错误', () => {
      expect(validateUsername(undefined)).toBe('用户名不能为空')
    })

    it('纯空格用户名应该返回错误', () => {
      expect(validateUsername('   ')).toBe('用户名不能为空')
    })

    it('少于 3 个字符的用户名应该返回错误', () => {
      expect(validateUsername('ab')).toBe('用户名至少 3 个字符')
    })

    it('正好 3 个字符的用户名应该通过', () => {
      expect(validateUsername('abc')).toBe(true)
    })

    it('超过 20 个字符的用户名应该返回错误', () => {
      expect(validateUsername('a'.repeat(21))).toBe('用户名最多 20 个字符')
    })

    it('正好 20 个字符的用户名应该通过', () => {
      expect(validateUsername('a'.repeat(20))).toBe(true)
    })

    it('包含特殊字符的用户名应该返回错误', () => {
      expect(validateUsername('user@name')).toBe('用户名只能包含字母、数字、下划线')
    })

    it('包含空格的用户名应该返回错误', () => {
      expect(validateUsername('user name')).toBe('用户名只能包含字母、数字、下划线')
    })

    it('包含中文字符的用户名应该返回错误', () => {
      expect(validateUsername('用户名')).toBe('用户名只能包含字母、数字、下划线')
    })

    it('有效的用户名应该通过', () => {
      expect(validateUsername('user_name')).toBe(true)
      expect(validateUsername('UserName123')).toBe(true)
      expect(validateUsername('test_user_2024')).toBe(true)
    })

    it('应该去除首尾空格后验证', () => {
      expect(validateUsername('  user_name  ')).toBe(true)
      expect(validateUsername('  ab  ')).toBe('用户名至少 3 个字符')
    })
  })

  /**
   * 密码校验测试
   */
  describe('validatePassword', () => {
    it('空密码应该返回错误', () => {
      expect(validatePassword('')).toBe('密码不能为空')
    })

    it('null 密码应该返回错误', () => {
      expect(validatePassword(null)).toBe('密码不能为空')
    })

    it('undefined 密码应该返回错误', () => {
      expect(validatePassword(undefined)).toBe('密码不能为空')
    })

    it('少于 6 个字符的密码应该返回错误', () => {
      expect(validatePassword('12345')).toBe('密码至少 6 个字符')
    })

    it('正好 6 个字符的密码应该通过', () => {
      expect(validatePassword('123456')).toBe(true)
    })

    it('超过 50 个字符的密码应该返回错误', () => {
      expect(validatePassword('a'.repeat(51))).toBe('密码最多 50 个字符')
    })

    it('正好 50 个字符的密码应该通过', () => {
      expect(validatePassword('a'.repeat(50))).toBe(true)
    })

    it('有效的密码应该通过', () => {
      expect(validatePassword('password123')).toBe(true)
      expect(validatePassword('MyP@ssw0rd!')).toBe(true)
      expect(validatePassword('123456')).toBe(true)
    })

    it('包含空格的密码应该通过（当前实现）', () => {
      expect(validatePassword('pass word')).toBe(true)
    })
  })

  /**
   * 确认密码校验测试
   */
  describe('validateConfirmPassword', () => {
    it('空确认密码应该返回错误', () => {
      expect(validateConfirmPassword('', 'password')).toBe('请确认密码')
    })

    it('null 确认密码应该返回错误', () => {
      expect(validateConfirmPassword(null, 'password')).toBe('请确认密码')
    })

    it('undefined 确认密码应该返回错误', () => {
      expect(validateConfirmPassword(undefined, 'password')).toBe('请确认密码')
    })

    it('与原始密码不匹配应该返回错误', () => {
      expect(validateConfirmPassword('password1', 'password2')).toBe('两次输入的密码不一致')
    })

    it('与原始密码匹配应该通过', () => {
      expect(validateConfirmPassword('password123', 'password123')).toBe(true)
    })

    it('区分大小写', () => {
      expect(validateConfirmPassword('Password', 'password')).toBe('两次输入的密码不一致')
    })
  })

  /**
   * 项目名称校验测试
   */
  describe('validateProjectName', () => {
    it('空项目名称应该返回错误', () => {
      expect(validateProjectName('')).toBe('项目名称不能为空')
    })

    it('null 项目名称应该返回错误', () => {
      expect(validateProjectName(null)).toBe('项目名称不能为空')
    })

    it('undefined 项目名称应该返回错误', () => {
      expect(validateProjectName(undefined)).toBe('项目名称不能为空')
    })

    it('纯空格项目名称应该返回错误', () => {
      expect(validateProjectName('   ')).toBe('项目名称不能为空')
    })

    it('少于 2 个字符的项目名称应该返回错误', () => {
      expect(validateProjectName('a')).toBe('项目名称至少 2 个字符')
    })

    it('正好 2 个字符的项目名称应该通过', () => {
      expect(validateProjectName('ab')).toBe(true)
    })

    it('超过 100 个字符的项目名称应该返回错误', () => {
      expect(validateProjectName('a'.repeat(101))).toBe('项目名称最多 100 个字符')
    })

    it('正好 100 个字符的项目名称应该通过', () => {
      expect(validateProjectName('a'.repeat(100))).toBe(true)
    })

    it('有效的项目名称应该通过', () => {
      expect(validateProjectName('我的项目')).toBe(true)
      expect(validateProjectName('Project Name')).toBe(true)
      expect(validateProjectName('项目-2024_v1')).toBe(true)
    })

    it('应该去除首尾空格后验证', () => {
      expect(validateProjectName('  我的项目  ')).toBe(true)
      expect(validateProjectName('  a  ')).toBe('项目名称至少 2 个字符')
    })
  })

  /**
   * 项目描述校验测试
   */
  describe('validateProjectDescription', () => {
    it('空描述应该通过（可选字段）', () => {
      expect(validateProjectDescription('')).toBe(true)
    })

    it('null 描述应该通过', () => {
      expect(validateProjectDescription(null)).toBe(true)
    })

    it('undefined 描述应该通过', () => {
      expect(validateProjectDescription(undefined)).toBe(true)
    })

    it('超过 500 个字符的描述应该返回错误', () => {
      expect(validateProjectDescription('a'.repeat(501))).toBe('项目描述最多 500 个字符')
    })

    it('正好 500 个字符的描述应该通过', () => {
      expect(validateProjectDescription('a'.repeat(500))).toBe(true)
    })

    it('有效的描述应该通过', () => {
      expect(validateProjectDescription('这是一个项目描述')).toBe(true)
    })
  })

  /**
   * 文件校验测试
   */
  describe('validateFile', () => {
    it('null 文件应该返回错误', () => {
      expect(validateFile(null)).toBe('请选择文件')
    })

    it('undefined 文件应该返回错误', () => {
      expect(validateFile(undefined)).toBe('请选择文件')
    })

    it('超过默认大小限制的文件应该返回错误', () => {
      const file = { name: 'test.pdf', size: 50 * 1024 * 1024 + 1 }
      expect(validateFile(file)).toBe('文件大小不能超过 50MB')
    })

    it('正好 50MB 的文件应该通过', () => {
      const file = { name: 'test.pdf', size: 50 * 1024 * 1024 }
      expect(validateFile(file)).toBe(true)
    })

    it('不支持的文件类型应该返回错误', () => {
      const file = { name: 'test.txt', size: 1024 }
      expect(validateFile(file)).toBe('不支持的文件类型: .txt，仅支持 .pdf, .docx, .xlsx')
    })

    it('大写的文件扩展名应该通过', () => {
      const file = { name: 'test.PDF', size: 1024 }
      expect(validateFile(file)).toBe(true)
    })

    it('有效的 PDF 文件应该通过', () => {
      const file = { name: 'document.pdf', size: 1024 * 1024 }
      expect(validateFile(file)).toBe(true)
    })

    it('有效的 DOCX 文件应该通过', () => {
      const file = { name: 'document.docx', size: 1024 * 1024 }
      expect(validateFile(file)).toBe(true)
    })

    it('有效的 XLSX 文件应该通过', () => {
      const file = { name: 'spreadsheet.xlsx', size: 1024 * 1024 }
      expect(validateFile(file)).toBe(true)
    })

    it('应该支持自定义大小限制', () => {
      const file = { name: 'test.pdf', size: 10 * 1024 * 1024 }
      const options = { maxSize: 5 * 1024 * 1024 }
      expect(validateFile(file, options)).toBe('文件大小不能超过 5MB')
    })

    it('应该支持自定义允许类型', () => {
      const file = { name: 'test.txt', size: 1024 }
      const options = { allowedTypes: ['.txt', '.pdf'] }
      expect(validateFile(file, options)).toBe(true)
    })

    it('没有扩展名的文件应该返回错误', () => {
      const file = { name: 'testfile', size: 1024 }
      expect(validateFile(file)).toBe('不支持的文件类型: .testfile，仅支持 .pdf, .docx, .xlsx')
    })
  })

  /**
   * 文件列表校验测试
   */
  describe('validateFileList', () => {
    it('空数组应该返回错误', () => {
      expect(validateFileList([])).toBe('请至少选择一个文件')
    })

    it('null 文件列表应该返回错误', () => {
      expect(validateFileList(null)).toBe('请至少选择一个文件')
    })

    it('undefined 文件列表应该返回错误', () => {
      expect(validateFileList(undefined)).toBe('请至少选择一个文件')
    })

    it('超过最大数量限制应该返回错误', () => {
      const files = [
        { name: 'file1.pdf', size: 1024 },
        { name: 'file2.pdf', size: 1024 },
        { name: 'file3.pdf', size: 1024 }
      ]
      expect(validateFileList(files, { maxCount: 2 })).toBe('最多只能选择 2 个文件')
    })

    it('正好达到最大数量应该通过', () => {
      const files = [
        { name: 'file1.pdf', size: 1024 },
        { name: 'file2.pdf', size: 1024 }
      ]
      expect(validateFileList(files, { maxCount: 2 })).toBe(true)
    })

    it('超过总大小限制应该返回错误', () => {
      const files = [
        { name: 'file1.pdf', size: 30 * 1024 * 1024 },
        { name: 'file2.pdf', size: 30 * 1024 * 1024 }
      ]
      expect(validateFileList(files, { maxCount: 5, maxTotalSize: 50 * 1024 * 1024 })).toBe('文件总大小不能超过 50MB')
    })

    it('有效的文件列表应该通过', () => {
      const files = [
        { name: 'file1.pdf', size: 1024 * 1024 },
        { name: 'file2.pdf', size: 1024 * 1024 }
      ]
      expect(validateFileList(files, { maxCount: 5 })).toBe(true)
    })
  })

  /**
   * 变更说明校验测试
   */
  describe('validateChangelog', () => {
    it('空变更说明应该通过（可选字段）', () => {
      expect(validateChangelog('')).toBe(true)
    })

    it('null 变更说明应该通过', () => {
      expect(validateChangelog(null)).toBe(true)
    })

    it('undefined 变更说明应该通过', () => {
      expect(validateChangelog(undefined)).toBe(true)
    })

    it('超过 1000 个字符的变更说明应该返回错误', () => {
      expect(validateChangelog('a'.repeat(1001))).toBe('变更说明最多 1000 个字符')
    })

    it('正好 1000 个字符的变更说明应该通过', () => {
      expect(validateChangelog('a'.repeat(1000))).toBe(true)
    })

    it('有效的变更说明应该通过', () => {
      expect(validateChangelog('修复了若干 bug')).toBe(true)
    })
  })

  /**
   * 邮箱校验测试
   */
  describe('validateEmail', () => {
    it('空邮箱应该返回错误', () => {
      expect(validateEmail('')).toBe('邮箱不能为空')
    })

    it('null 邮箱应该返回错误', () => {
      expect(validateEmail(null)).toBe('邮箱不能为空')
    })

    it('undefined 邮箱应该返回错误', () => {
      expect(validateEmail(undefined)).toBe('邮箱不能为空')
    })

    it('纯空格邮箱应该返回错误', () => {
      expect(validateEmail('   ')).toBe('邮箱不能为空')
    })

    it('无效格式的邮箱应该返回错误', () => {
      expect(validateEmail('invalid')).toBe('请输入有效的邮箱地址')
      expect(validateEmail('invalid@')).toBe('请输入有效的邮箱地址')
      expect(validateEmail('@example.com')).toBe('请输入有效的邮箱地址')
      expect(validateEmail('invalid@example')).toBe('请输入有效的邮箱地址')
    })

    it('有效的邮箱应该通过', () => {
      expect(validateEmail('test@example.com')).toBe(true)
      expect(validateEmail('user.name@example.co.uk')).toBe(true)
      expect(validateEmail('user+tag@example.com')).toBe(true)
    })

    it('应该去除首尾空格后验证', () => {
      expect(validateEmail('  test@example.com  ')).toBe(true)
    })
  })

  /**
   * 手机号校验测试
   */
  describe('validatePhone', () => {
    it('空手机号应该返回错误', () => {
      expect(validatePhone('')).toBe('手机号不能为空')
    })

    it('null 手机号应该返回错误', () => {
      expect(validatePhone(null)).toBe('手机号不能为空')
    })

    it('undefined 手机号应该返回错误', () => {
      expect(validatePhone(undefined)).toBe('手机号不能为空')
    })

    it('纯空格手机号应该返回错误', () => {
      expect(validatePhone('   ')).toBe('手机号不能为空')
    })

    it('非 11 位手机号应该返回错误', () => {
      expect(validatePhone('1380013800')).toBe('请输入有效的手机号')
    })

    it('不以 1 开头的手机号应该返回错误', () => {
      expect(validatePhone('23800138000')).toBe('请输入有效的手机号')
    })

    it('第二位不在 3-9 范围的手机号应该返回错误', () => {
      expect(validatePhone('10800138000')).toBe('请输入有效的手机号')
      expect(validatePhone('12800138000')).toBe('请输入有效的手机号')
    })

    it('包含非数字字符的手机号应该返回错误', () => {
      expect(validatePhone('138-0013-8000')).toBe('请输入有效的手机号')
      expect(validatePhone('1380013800a')).toBe('请输入有效的手机号')
    })

    it('有效的手机号应该通过', () => {
      expect(validatePhone('13800138000')).toBe(true)
      expect(validatePhone('15912345678')).toBe(true)
      expect(validatePhone('18812345678')).toBe(true)
    })

    it('应该去除首尾空格后验证', () => {
      expect(validatePhone('  13800138000  ')).toBe(true)
    })
  })

  /**
   * 必填字段校验测试
   */
  describe('validateRequired', () => {
    it('空字符串应该返回错误', () => {
      expect(validateRequired('')).toBe('该字段不能为空')
    })

    it('纯空格字符串应该返回错误', () => {
      expect(validateRequired('   ')).toBe('该字段不能为空')
    })

    it('null 应该返回错误', () => {
      expect(validateRequired(null)).toBe('该字段不能为空')
    })

    it('undefined 应该返回错误', () => {
      expect(validateRequired(undefined)).toBe('该字段不能为空')
    })

    it('0 应该通过', () => {
      expect(validateRequired(0)).toBe(true)
    })

    it('false 应该通过', () => {
      expect(validateRequired(false)).toBe(true)
    })

    it('有效值应该通过', () => {
      expect(validateRequired('value')).toBe(true)
      expect(validateRequired(123)).toBe(true)
      expect(validateRequired([])).toBe(true)
      expect(validateRequired({})).toBe(true)
    })

    it('应该支持自定义字段名', () => {
      expect(validateRequired('', '用户名')).toBe('用户名不能为空')
      expect(validateRequired(null, '邮箱')).toBe('邮箱不能为空')
    })
  })

  /**
   * 长度范围校验测试
   */
  describe('validateLength', () => {
    it('小于最小长度应该返回错误', () => {
      expect(validateLength('ab', { min: 3 })).toBe('该字段至少 3 个字符')
    })

    it('正好最小长度应该通过', () => {
      expect(validateLength('abc', { min: 3 })).toBe(true)
    })

    it('超过最大长度应该返回错误', () => {
      expect(validateLength('abcd', { max: 3 })).toBe('该字段最多 3 个字符')
    })

    it('正好最大长度应该通过', () => {
      expect(validateLength('abc', { max: 3 })).toBe(true)
    })

    it('在范围内应该通过', () => {
      expect(validateLength('abc', { min: 2, max: 5 })).toBe(true)
    })

    it('null 值应该按 0 长度处理', () => {
      expect(validateLength(null, { min: 1 })).toBe('该字段至少 1 个字符')
    })

    it('undefined 值应该按 0 长度处理', () => {
      expect(validateLength(undefined, { min: 1 })).toBe('该字段至少 1 个字符')
    })

    it('应该支持自定义字段名', () => {
      expect(validateLength('ab', { min: 3, fieldName: '用户名' })).toBe('用户名至少 3 个字符')
      expect(validateLength('abcd', { max: 3, fieldName: '密码' })).toBe('密码最多 3 个字符')
    })
  })

  /**
   * 创建规则测试
   */
  describe('createRules', () => {
    it('应该创建单个验证规则', () => {
      const rules = createRules(validateUsername)

      expect(Array.isArray(rules)).toBe(true)
      expect(rules.length).toBe(1)
      expect(rules[0]).toHaveProperty('validator')
      expect(rules[0]).toHaveProperty('trigger', 'blur')
    })

    it('应该创建多个验证规则', () => {
      const rules = createRules([validateUsername, validatePassword])

      expect(Array.isArray(rules)).toBe(true)
      expect(rules.length).toBe(2)
    })

    it('应该支持自定义触发时机', () => {
      const rules = createRules(validateUsername, 'change')

      expect(rules[0].trigger).toBe('change')
    })

    it('验证器应该正确工作', () => {
      const rules = createRules(validateUsername)
      const callback = vi.fn()

      rules[0].validator({}, 'test', callback)
      expect(callback).toHaveBeenCalled()
    })
  })

  /**
   * 创建依赖规则测试
   */
  describe('createDependentRules', () => {
    it('应该创建依赖验证规则', () => {
      const getPassword = () => 'password123'
      const rules = createDependentRules(validateConfirmPassword, getPassword)

      expect(Array.isArray(rules)).toBe(true)
      expect(rules.length).toBe(1)
      expect(rules[0]).toHaveProperty('validator')
      expect(rules[0]).toHaveProperty('trigger', 'blur')
    })

    it('应该支持自定义触发时机', () => {
      const getPassword = () => 'password123'
      const rules = createDependentRules(validateConfirmPassword, getPassword, 'change')

      expect(rules[0].trigger).toBe('change')
    })

    it('验证器应该正确获取依赖值', () => {
      const getPassword = () => 'password123'
      const rules = createDependentRules(validateConfirmPassword, getPassword)
      const callback = vi.fn()

      rules[0].validator({}, 'password123', callback)
      expect(callback).toHaveBeenCalledWith()
    })
  })

  /**
   * 预定义规则测试
   */
  describe('Rules', () => {
    it('应该包含 username 规则', () => {
      expect(Rules.username).toBeDefined()
      expect(Array.isArray(Rules.username)).toBe(true)
    })

    it('应该包含 password 规则', () => {
      expect(Rules.password).toBeDefined()
      expect(Array.isArray(Rules.password)).toBe(true)
    })

    it('应该包含 projectName 规则', () => {
      expect(Rules.projectName).toBeDefined()
      expect(Array.isArray(Rules.projectName)).toBe(true)
    })

    it('应该包含 projectDescription 规则', () => {
      expect(Rules.projectDescription).toBeDefined()
      expect(Array.isArray(Rules.projectDescription)).toBe(true)
    })

    it('应该包含 email 规则', () => {
      expect(Rules.email).toBeDefined()
      expect(Array.isArray(Rules.email)).toBe(true)
    })

    it('应该包含 phone 规则', () => {
      expect(Rules.phone).toBeDefined()
      expect(Array.isArray(Rules.phone)).toBe(true)
    })

    it('应该包含 changelog 规则', () => {
      expect(Rules.changelog).toBeDefined()
      expect(Array.isArray(Rules.changelog)).toBe(true)
    })

    it('预定义规则应该可以正常使用', () => {
      const callback = vi.fn()
      Rules.username[0].validator({}, 'testuser', callback)
      expect(callback).toHaveBeenCalled()
    })
  })
})
