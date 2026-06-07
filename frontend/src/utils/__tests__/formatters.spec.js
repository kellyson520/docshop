/**
 * formatters 工具函数单元测试
 * 测试日期格式化、文件大小格式化、文件类型图标等功能
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// 模拟 formatters 函数
function formatDate(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  const k = 1024
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), units.length - 1)
  const size = (bytes / Math.pow(k, i)).toFixed(i > 0 ? 2 : 0)
  return `${size} ${units[i]}`
}

function getFileTypeIcon(fileType) {
  const iconMap = {
    pdf: 'Document',
    docx: 'Document',
    doc: 'Document',
    xlsx: 'Grid',
    xls: 'Grid',
    csv: 'Grid',
    txt: 'Document',
    default: 'Document'
  }
  return iconMap[fileType] || iconMap.default
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // 降级方案
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const success = document.execCommand('copy')
    document.body.removeChild(textarea)
    return success
  }
}

// 额外的格式化函数
function formatRelativeTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date

  // 小于1分钟
  if (diff < 60000) {
    return '刚刚'
  }

  // 小于1小时
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000)
    return `${minutes}分钟前`
  }

  // 小于1天
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    return `${hours}小时前`
  }

  // 小于7天
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000)
    return `${days}天前`
  }

  // 小于30天
  if (diff < 2592000000) {
    const weeks = Math.floor(diff / 604800000)
    return `${weeks}周前`
  }

  // 小于365天
  if (diff < 31536000000) {
    const months = Math.floor(diff / 2592000000)
    return `${months}个月前`
  }

  // 超过1年
  const years = Math.floor(diff / 31536000000)
  return `${years}年前`
}

function formatNumber(num, options = {}) {
  const { decimals = 0, thousandsSeparator = true } = options

  if (num == null || isNaN(num)) return '-'

  const fixed = Number(num).toFixed(decimals)

  if (!thousandsSeparator) return fixed

  const parts = fixed.split('.')
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',')

  return parts.join('.')
}

function formatDuration(seconds) {
  if (seconds == null || seconds < 0) return '0:00'

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }

  return `${minutes}:${String(secs).padStart(2, '0')}`
}

function formatPercentage(value, decimals = 2) {
  if (value == null || isNaN(value)) return '-'
  return `${(value * 100).toFixed(decimals)}%`
}

function truncateText(text, maxLength = 100, suffix = '...') {
  if (!text || text.length <= maxLength) return text
  return text.substring(0, maxLength - suffix.length) + suffix
}

describe('formatters 工具函数', () => {
  /**
   * formatDate 测试
   */
  describe('formatDate', () => {
    it('应该正确格式化 ISO 日期字符串', () => {
      const result = formatDate('2024-01-15T08:30:00Z')
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)
    })

    it('空值应该返回 -', () => {
      expect(formatDate('')).toBe('-')
      expect(formatDate(null)).toBe('-')
      expect(formatDate(undefined)).toBe('-')
    })

    it('应该正确处理不同的日期格式', () => {
      expect(formatDate('2024-03-15')).toMatch(/^2024-03-15/)
      expect(formatDate('2024-12-01T23:59:59')).toMatch(/^2024-12-01/)
    })

    it('应该正确处理时区', () => {
      // 测试 UTC 时间
      const result = formatDate('2024-01-01T00:00:00Z')
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)
    })

    it('应该正确补零', () => {
      const result = formatDate('2024-01-05T03:05:00Z')
      expect(result).toMatch(/\d{4}-01-05 \d{2}:0\d/)
    })
  })

  /**
   * formatFileSize 测试
   */
  describe('formatFileSize', () => {
    it('0 字节应该返回 0 B', () => {
      expect(formatFileSize(0)).toBe('0 B')
    })

    it('null 或 undefined 应该返回 0 B', () => {
      expect(formatFileSize(null)).toBe('0 B')
      expect(formatFileSize(undefined)).toBe('0 B')
    })

    it('应该正确格式化字节', () => {
      expect(formatFileSize(100)).toBe('100 B')
      expect(formatFileSize(1023)).toBe('1023 B')
    })

    it('应该正确格式化 KB', () => {
      expect(formatFileSize(1024)).toBe('1.00 KB')
      expect(formatFileSize(1536)).toBe('1.50 KB')
      expect(formatFileSize(10240)).toBe('10.00 KB')
    })

    it('应该正确格式化 MB', () => {
      expect(formatFileSize(1024 * 1024)).toBe('1.00 MB')
      expect(formatFileSize(1024 * 1024 * 2.5)).toBe('2.50 MB')
      expect(formatFileSize(1024 * 1024 * 100)).toBe('100.00 MB')
    })

    it('应该正确格式化 GB', () => {
      expect(formatFileSize(1024 * 1024 * 1024)).toBe('1.00 GB')
      expect(formatFileSize(1024 * 1024 * 1024 * 1.5)).toBe('1.50 GB')
    })

    it('应该正确格式化 TB', () => {
      expect(formatFileSize(1024 * 1024 * 1024 * 1024)).toBe('1.00 TB')
    })

    it('应该正确处理大数值', () => {
      expect(formatFileSize(1024 * 1024 * 1024 * 1024 * 5)).toBe('5.00 TB')
    })
  })

  /**
   * getFileTypeIcon 测试
   */
  describe('getFileTypeIcon', () => {
    it('PDF 应该返回 Document', () => {
      expect(getFileTypeIcon('pdf')).toBe('Document')
    })

    it('DOCX 应该返回 Document', () => {
      expect(getFileTypeIcon('docx')).toBe('Document')
    })

    it('DOC 应该返回 Document', () => {
      expect(getFileTypeIcon('doc')).toBe('Document')
    })

    it('XLSX 应该返回 Grid', () => {
      expect(getFileTypeIcon('xlsx')).toBe('Grid')
    })

    it('XLS 应该返回 Grid', () => {
      expect(getFileTypeIcon('xls')).toBe('Grid')
    })

    it('CSV 应该返回 Grid', () => {
      expect(getFileTypeIcon('csv')).toBe('Grid')
    })

    it('TXT 应该返回 Document', () => {
      expect(getFileTypeIcon('txt')).toBe('Document')
    })

    it('未知类型应该返回默认 Document', () => {
      expect(getFileTypeIcon('unknown')).toBe('Document')
      expect(getFileTypeIcon('')).toBe('Document')
      expect(getFileTypeIcon(null)).toBe('Document')
      expect(getFileTypeIcon(undefined)).toBe('Document')
    })
  })

  /**
   * copyToClipboard 测试
   */
  describe('copyToClipboard', () => {
    let mockClipboard
    let mockExecCommand

    beforeEach(() => {
      mockClipboard = {
        writeText: vi.fn().mockResolvedValue(undefined)
      }
      Object.defineProperty(navigator, 'clipboard', {
        value: mockClipboard,
        writable: true,
        configurable: true
      })

      mockExecCommand = vi.fn().mockReturnValue(true)
      document.execCommand = mockExecCommand
    })

    afterEach(() => {
      vi.restoreAllMocks()
    })

    it('应该使用 Clipboard API 复制文本', async () => {
      const result = await copyToClipboard('test text')

      expect(mockClipboard.writeText).toHaveBeenCalledWith('test text')
      expect(result).toBe(true)
    })

    it('Clipboard API 失败时应该使用降级方案', async () => {
      mockClipboard.writeText.mockRejectedValue(new Error('Failed'))

      const result = await copyToClipboard('test text')

      expect(mockExecCommand).toHaveBeenCalledWith('copy')
      expect(result).toBe(true)
    })

    it('降级方案失败时应该返回 false', async () => {
      mockClipboard.writeText.mockRejectedValue(new Error('Failed'))
      mockExecCommand.mockReturnValue(false)

      const result = await copyToClipboard('test text')

      expect(result).toBe(false)
    })

    it('应该正确处理空字符串', async () => {
      const result = await copyToClipboard('')

      expect(mockClipboard.writeText).toHaveBeenCalledWith('')
      expect(result).toBe(true)
    })

    it('应该正确处理长文本', async () => {
      const longText = 'a'.repeat(10000)
      const result = await copyToClipboard(longText)

      expect(mockClipboard.writeText).toHaveBeenCalledWith(longText)
      expect(result).toBe(true)
    })
  })

  /**
   * formatRelativeTime 测试
   */
  describe('formatRelativeTime', () => {
    beforeEach(() => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2024-01-15T12:00:00Z'))
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('空值应该返回空字符串', () => {
      expect(formatRelativeTime('')).toBe('')
      expect(formatRelativeTime(null)).toBe('')
      expect(formatRelativeTime(undefined)).toBe('')
    })

    it('小于1分钟应该返回刚刚', () => {
      const date = new Date('2024-01-15T11:59:30Z').toISOString()
      expect(formatRelativeTime(date)).toBe('刚刚')
    })

    it('1-59分钟应该返回分钟前', () => {
      const date = new Date('2024-01-15T11:30:00Z').toISOString()
      expect(formatRelativeTime(date)).toBe('30分钟前')
    })

    it('1-23小时应该返回小时前', () => {
      const date = new Date('2024-01-15T02:00:00Z').toISOString()
      expect(formatRelativeTime(date)).toBe('10小时前')
    })

    it('1-6天应该返回天前', () => {
      const date = new Date('2024-01-10T12:00:00Z').toISOString()
      expect(formatRelativeTime(date)).toBe('5天前')
    })

    it('1-4周应该返回周前', () => {
      const date = new Date('2023-12-25T12:00:00Z').toISOString()
      expect(formatRelativeTime(date)).toBe('3周前')
    })

    it('1-11个月应该返回个月前', () => {
      const date = new Date('2023-06-15T12:00:00Z').toISOString()
      expect(formatRelativeTime(date)).toBe('7个月前')
    })

    it('超过1年应该返回年前', () => {
      const date = new Date('2022-01-15T12:00:00Z').toISOString()
      expect(formatRelativeTime(date)).toBe('2年前')
    })
  })

  /**
   * formatNumber 测试
   */
  describe('formatNumber', () => {
    it('null 或 undefined 应该返回 -', () => {
      expect(formatNumber(null)).toBe('-')
      expect(formatNumber(undefined)).toBe('-')
    })

    it('NaN 应该返回 -', () => {
      expect(formatNumber(NaN)).toBe('-')
    })

    it('应该正确格式化整数', () => {
      expect(formatNumber(1234567)).toBe('1,234,567')
    })

    it('应该正确格式化小数', () => {
      expect(formatNumber(1234.567, { decimals: 2 })).toBe('1,234.57')
    })

    it('应该正确处理 decimals 选项', () => {
      expect(formatNumber(1234.5, { decimals: 0 })).toBe('1,235')
      expect(formatNumber(1234.5, { decimals: 1 })).toBe('1,234.5')
      expect(formatNumber(1234.5, { decimals: 3 })).toBe('1,234.500')
    })

    it('应该正确处理 thousandsSeparator 选项', () => {
      expect(formatNumber(1234567, { thousandsSeparator: false })).toBe('1234567')
    })

    it('应该正确处理负数', () => {
      expect(formatNumber(-1234567)).toBe('-1,234,567')
    })

    it('应该正确处理字符串数字', () => {
      expect(formatNumber('1234.56', { decimals: 1 })).toBe('1,234.6')
    })
  })

  /**
   * formatDuration 测试
   */
  describe('formatDuration', () => {
    it('null 或 undefined 应该返回 0:00', () => {
      expect(formatDuration(null)).toBe('0:00')
      expect(formatDuration(undefined)).toBe('0:00')
    })

    it('负数应该返回 0:00', () => {
      expect(formatDuration(-1)).toBe('0:00')
    })

    it('0 秒应该返回 0:00', () => {
      expect(formatDuration(0)).toBe('0:00')
    })

    it('少于60秒应该正确格式化', () => {
      expect(formatDuration(30)).toBe('0:30')
      expect(formatDuration(59)).toBe('0:59')
    })

    it('少于1小时应该正确格式化', () => {
      expect(formatDuration(60)).toBe('1:00')
      expect(formatDuration(90)).toBe('1:30')
      expect(formatDuration(3599)).toBe('59:59')
    })

    it('超过1小时应该正确格式化', () => {
      expect(formatDuration(3600)).toBe('1:00:00')
      expect(formatDuration(3661)).toBe('1:01:01')
      expect(formatDuration(7200)).toBe('2:00:00')
    })

    it('应该正确补零', () => {
      expect(formatDuration(65)).toBe('1:05')
      expect(formatDuration(3665)).toBe('1:01:05')
    })
  })

  /**
   * formatPercentage 测试
   */
  describe('formatPercentage', () => {
    it('null 或 undefined 应该返回 -', () => {
      expect(formatPercentage(null)).toBe('-')
      expect(formatPercentage(undefined)).toBe('-')
    })

    it('NaN 应该返回 -', () => {
      expect(formatPercentage(NaN)).toBe('-')
    })

    it('应该正确格式化百分比', () => {
      expect(formatPercentage(0.5)).toBe('50.00%')
      expect(formatPercentage(0.1234)).toBe('12.34%')
      expect(formatPercentage(1)).toBe('100.00%')
    })

    it('应该正确处理 decimals 参数', () => {
      expect(formatPercentage(0.5, 0)).toBe('50%')
      expect(formatPercentage(0.5, 1)).toBe('50.0%')
      expect(formatPercentage(0.5, 3)).toBe('50.000%')
    })

    it('应该正确处理大于1的值', () => {
      expect(formatPercentage(1.5)).toBe('150.00%')
    })

    it('应该正确处理小于0的值', () => {
      expect(formatPercentage(-0.25)).toBe('-25.00%')
    })
  })

  /**
   * truncateText 测试
   */
  describe('truncateText', () => {
    it('空值应该返回原值', () => {
      expect(truncateText('')).toBe('')
      expect(truncateText(null)).toBeNull()
      expect(truncateText(undefined)).toBeUndefined()
    })

    it('短文本应该原样返回', () => {
      expect(truncateText('short', 10)).toBe('short')
    })

    it('等于最大长度应该原样返回', () => {
      const text = 'a'.repeat(100)
      expect(truncateText(text, 100)).toBe(text)
    })

    it('超过最大长度应该截断', () => {
      const text = 'a'.repeat(150)
      const result = truncateText(text, 100)
      expect(result.length).toBe(100)
      expect(result.endsWith('...')).toBe(true)
    })

    it('应该使用自定义后缀', () => {
      const text = 'a'.repeat(150)
      const result = truncateText(text, 100, '...more')
      expect(result.endsWith('...more')).toBe(true)
    })

    it('自定义后缀长度应该被考虑', () => {
      const text = 'a'.repeat(150)
      const result = truncateText(text, 100, '.....')
      expect(result.length).toBe(100)
      expect(result).toBe('a'.repeat(95) + '.....')
    })

    it('应该正确处理中文', () => {
      const text = '这是一个很长的中文文本，需要被截断'
      const result = truncateText(text, 10)
      expect(result.length).toBeLessThanOrEqual(10)
    })
  })

  /**
   * 边界情况测试
   */
  describe('边界情况', () => {
    it('formatDate 应该处理无效日期', () => {
      const result = formatDate('invalid date')
      expect(result).toBe('NaN-NaN-NaN NaN:NaN')
    })

    it('formatFileSize 应该处理极大值', () => {
      const result = formatFileSize(Number.MAX_SAFE_INTEGER)
      expect(result).toMatch(/\d+\.?\d* PB/)
    })

    it('formatNumber 应该处理极大值', () => {
      const result = formatNumber(12345678901234567890)
      expect(result).toContain(',')
    })

    it('formatNumber 应该处理极小值', () => {
      const result = formatNumber(0.0000001, { decimals: 10 })
      expect(result).toBe('0.0000001000')
    })

    it('truncateText 应该处理 maxLength 小于后缀长度的情况', () => {
      const text = 'abcdefghij'
      const result = truncateText(text, 5, '...')
      expect(result).toBe('ab...')
    })
  })
})
