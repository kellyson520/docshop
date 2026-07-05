/**
 * useConfirm 组合式函数单元测试
 * 测试确认对话框功能
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useConfirm } from '../useConfirm.js'

// 模拟 Element Plus 的 ElMessageBox
const mockConfirm = vi.fn()
vi.mock('element-plus', () => ({
  ElMessageBox: {
    confirm: (...args) => mockConfirm(...args)
  }
}))

describe('useConfirm 组合式函数', () => {
  beforeEach(() => {
    mockConfirm.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  /**
   * 初始化和基本结构测试
   */
  describe('初始化', () => {
    it('应该返回所有确认方法', () => {
      const confirm = useConfirm()

      expect(confirm).toHaveProperty('confirm')
      expect(confirm).toHaveProperty('confirmDelete')
      expect(confirm).toHaveProperty('confirmDanger')
      expect(confirm).toHaveProperty('confirmSave')
      expect(confirm).toHaveProperty('confirmLeave')
      expect(confirm).toHaveProperty('confirmAction')
    })

    it('所有方法都应该是函数', () => {
      const { confirm, confirmDelete, confirmDanger, confirmSave, confirmLeave, confirmAction } = useConfirm()

      expect(typeof confirm).toBe('function')
      expect(typeof confirmDelete).toBe('function')
      expect(typeof confirmDanger).toBe('function')
      expect(typeof confirmSave).toBe('function')
      expect(typeof confirmLeave).toBe('function')
      expect(typeof confirmAction).toBe('function')
    })
  })

  /**
   * 显示确认对话框测试
   */
  describe('显示确认对话框', () => {
    it('confirm 应该调用 ElMessageBox.confirm', () => {
      const { confirm } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirm({ title: '测试标题', message: '测试消息' })

      expect(mockConfirm).toHaveBeenCalled()
    })

    it('应该使用默认配置', () => {
      const { confirm } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirm({})

      expect(mockConfirm).toHaveBeenCalledWith(
        '',
        '确认',
        expect.objectContaining({
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          type: 'info',
          confirmButtonClass: '',
          closeOnClickModal: true,
          showClose: true,
          dangerouslyUseHTMLString: false
        })
      )
    })

    it('应该使用自定义配置', () => {
      const { confirm } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirm({
        title: '自定义标题',
        message: '自定义消息',
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'custom-class',
        closeOnClickModal: false,
        showClose: false
      })

      expect(mockConfirm).toHaveBeenCalledWith(
        '自定义消息',
        '自定义标题',
        expect.objectContaining({
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
          confirmButtonClass: 'custom-class',
          closeOnClickModal: false,
          showClose: false
        })
      )
    })

    it('应该返回 Promise', () => {
      const { confirm } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      const result = confirm({})

      expect(result).toBeInstanceOf(Promise)
    })
  })

  /**
   * 确认回调测试
   */
  describe('确认回调', () => {
    it('用户点击确认时应该 resolve', async () => {
      const { confirm } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      const result = await confirm({ title: '测试', message: '消息' })

      expect(result).toBe('confirm')
    })

    it('confirmDelete 应该 resolve', async () => {
      const { confirmDelete } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      const result = await confirmDelete()

      expect(result).toBe('confirm')
    })

    it('confirmDanger 应该 resolve', async () => {
      const { confirmDanger } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      const result = await confirmDanger()

      expect(result).toBe('confirm')
    })

    it('confirmSave 应该 resolve', async () => {
      const { confirmSave } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      const result = await confirmSave()

      expect(result).toBe('confirm')
    })

    it('confirmLeave 应该 resolve', async () => {
      const { confirmLeave } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      const result = await confirmLeave()

      expect(result).toBe('confirm')
    })

    it('confirmAction 应该 resolve', async () => {
      const { confirmAction } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      const result = await confirmAction('标题', '消息')

      expect(result).toBe('confirm')
    })
  })

  /**
   * 取消回调测试
   */
  describe('取消回调', () => {
    it('用户点击取消时应该 reject', async () => {
      const { confirm } = useConfirm()
      const cancelError = new Error('cancel')
      mockConfirm.mockRejectedValueOnce(cancelError)

      await expect(confirm({})).rejects.toBe(cancelError)
    })

    it('confirmDelete 取消时应该 reject', async () => {
      const { confirmDelete } = useConfirm()
      mockConfirm.mockRejectedValueOnce(new Error('cancel'))

      await expect(confirmDelete()).rejects.toThrow('cancel')
    })

    it('confirmDanger 取消时应该 reject', async () => {
      const { confirmDanger } = useConfirm()
      mockConfirm.mockRejectedValueOnce(new Error('cancel'))

      await expect(confirmDanger()).rejects.toThrow('cancel')
    })

    it('confirmSave 取消时应该 reject', async () => {
      const { confirmSave } = useConfirm()
      mockConfirm.mockRejectedValueOnce(new Error('cancel'))

      await expect(confirmSave()).rejects.toThrow('cancel')
    })

    it('confirmLeave 取消时应该 reject', async () => {
      const { confirmLeave } = useConfirm()
      mockConfirm.mockRejectedValueOnce(new Error('cancel'))

      await expect(confirmLeave()).rejects.toThrow('cancel')
    })

    it('confirmAction 取消时应该 reject', async () => {
      const { confirmAction } = useConfirm()
      mockConfirm.mockRejectedValueOnce(new Error('cancel'))

      await expect(confirmAction('标题', '消息')).rejects.toThrow('cancel')
    })
  })

  /**
   * 删除确认对话框测试
   */
  describe('删除确认对话框', () => {
    it('应该使用删除确认默认配置', () => {
      const { confirmDelete } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirmDelete()

      expect(mockConfirm).toHaveBeenCalledWith(
        '此操作不可恢复，是否继续？',
        '确认删除',
        expect.objectContaining({
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
          confirmButtonClass: 'el-button--danger'
        })
      )
    })

    it('应该支持自定义删除确认配置', () => {
      const { confirmDelete } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirmDelete({
        title: '自定义删除标题',
        message: '自定义删除消息',
        confirmButtonText: '确认删除'
      })

      expect(mockConfirm).toHaveBeenCalledWith(
        '自定义删除消息',
        '自定义删除标题',
        expect.objectContaining({
          confirmButtonText: '确认删除',
          cancelButtonText: '取消',
          type: 'warning',
          confirmButtonClass: 'el-button--danger'
        })
      )
    })
  })

  /**
   * 危险操作确认对话框测试
   */
  describe('危险操作确认对话框', () => {
    it('应该使用危险操作默认配置', () => {
      const { confirmDanger } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirmDanger()

      expect(mockConfirm).toHaveBeenCalledWith(
        '此操作具有风险，请确认是否继续？',
        '危险操作',
        expect.objectContaining({
          confirmButtonText: '确认执行',
          cancelButtonText: '取消',
          type: 'error',
          confirmButtonClass: 'el-button--danger'
        })
      )
    })

    it('应该支持自定义危险操作配置', () => {
      const { confirmDanger } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirmDanger({
        title: '危险！',
        message: '这将删除所有数据',
        confirmButtonText: '我确认'
      })

      expect(mockConfirm).toHaveBeenCalledWith(
        '这将删除所有数据',
        '危险！',
        expect.objectContaining({
          confirmButtonText: '我确认',
          cancelButtonText: '取消',
          type: 'error',
          confirmButtonClass: 'el-button--danger'
        })
      )
    })
  })

  /**
   * 保存确认对话框测试
   */
  describe('保存确认对话框', () => {
    it('应该使用保存确认默认配置', () => {
      const { confirmSave } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirmSave()

      expect(mockConfirm).toHaveBeenCalledWith(
        '是否保存当前更改？',
        '保存确认',
        expect.objectContaining({
          confirmButtonText: '保存',
          cancelButtonText: '不保存',
          type: 'info',
          confirmButtonClass: 'el-button--primary'
        })
      )
    })

    it('应该支持自定义保存确认配置', () => {
      const { confirmSave } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirmSave({
        title: '保存修改',
        message: '您有未保存的修改',
        confirmButtonText: '保存修改'
      })

      expect(mockConfirm).toHaveBeenCalledWith(
        '您有未保存的修改',
        '保存修改',
        expect.objectContaining({
          confirmButtonText: '保存修改',
          cancelButtonText: '不保存',
          type: 'info',
          confirmButtonClass: 'el-button--primary'
        })
      )
    })
  })

  /**
   * 离开确认对话框测试
   */
  describe('离开确认对话框', () => {
    it('应该使用离开确认默认配置', () => {
      const { confirmLeave } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirmLeave()

      expect(mockConfirm).toHaveBeenCalledWith(
        '您有未保存的更改，确定要离开吗？',
        '确认离开',
        expect.objectContaining({
          confirmButtonText: '离开',
          cancelButtonText: '留在当前页',
          type: 'warning'
        })
      )
    })

    it('应该支持自定义离开确认配置', () => {
      const { confirmLeave } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirmLeave({
        title: '离开页面',
        message: '确定要离开此页面吗？',
        confirmButtonText: '确定离开'
      })

      expect(mockConfirm).toHaveBeenCalledWith(
        '确定要离开此页面吗？',
        '离开页面',
        expect.objectContaining({
          confirmButtonText: '确定离开',
          cancelButtonText: '留在当前页',
          type: 'warning'
        })
      )
    })
  })

  /**
   * 自定义确认对话框测试
   */
  describe('自定义确认对话框', () => {
    it('应该使用传入的标题和消息', () => {
      const { confirmAction } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirmAction('自定义标题', '自定义消息')

      expect(mockConfirm).toHaveBeenCalledWith(
        '自定义消息',
        '自定义标题',
        expect.objectContaining({
          type: 'info'
        })
      )
    })

    it('应该支持自定义类型', () => {
      const { confirmAction } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirmAction('标题', '消息', 'success')

      expect(mockConfirm).toHaveBeenCalledWith(
        '消息',
        '标题',
        expect.objectContaining({
          type: 'success'
        })
      )
    })

    it('应该支持 warning 类型', () => {
      const { confirmAction } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirmAction('警告', '请注意', 'warning')

      expect(mockConfirm).toHaveBeenCalledWith(
        '请注意',
        '警告',
        expect.objectContaining({
          type: 'warning'
        })
      )
    })

    it('应该支持 error 类型', () => {
      const { confirmAction } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirmAction('错误', '发生错误', 'error')

      expect(mockConfirm).toHaveBeenCalledWith(
        '发生错误',
        '错误',
        expect.objectContaining({
          type: 'error'
        })
      )
    })
  })

  /**
   * 边界情况测试
   */
  describe('边界情况', () => {
    it('空对象配置应该使用默认值', () => {
      const { confirm } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirm({})

      expect(mockConfirm).toHaveBeenCalledWith(
        '',
        '确认',
        expect.any(Object)
      )
    })

    it('undefined 配置应该使用默认值', () => {
      const { confirm } = useConfirm()
      mockConfirm.mockResolvedValueOnce('confirm')

      confirm()

      expect(mockConfirm).toHaveBeenCalledWith(
        '',
        '确认',
        expect.any(Object)
      )
    })

    it('多次调用应该每次都调用 ElMessageBox.confirm', () => {
      const { confirm } = useConfirm()
      mockConfirm.mockResolvedValue('confirm')

      confirm({ title: '第一次' })
      confirm({ title: '第二次' })
      confirm({ title: '第三次' })

      expect(mockConfirm).toHaveBeenCalledTimes(3)
    })
  })
})
