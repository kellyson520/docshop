/**
 * usePagination 组合式函数单元测试
 * 测试分页功能的计算属性、方法和边界情况
 */

import { describe, it, expect, vi } from 'vitest'
import { ref, nextTick } from 'vue'

// 模拟 usePagination 组合式函数
function usePagination(options = {}) {
  const {
    total = 0,
    pageSize = 10,
    currentPage = 1,
    pageSizes = [10, 20, 50, 100]
  } = options

  const currentPageRef = ref(currentPage)
  const pageSizeRef = ref(pageSize)
  const totalRef = ref(total)

  // 计算总页数
  const totalPages = computed(() => {
    if (totalRef.value <= 0) return 0
    return Math.ceil(totalRef.value / pageSizeRef.value)
  })

  // 计算当前页的数据范围
  const pageRange = computed(() => {
    const start = (currentPageRef.value - 1) * pageSizeRef.value
    const end = Math.min(start + pageSizeRef.value, totalRef.value)
    return { start, end }
  })

  // 是否有上一页
  const hasPrevPage = computed(() => currentPageRef.value > 1)

  // 是否有下一页
  const hasNextPage = computed(() => currentPageRef.value < totalPages.value)

  // 页码列表（用于显示页码按钮）
  const pageList = computed(() => {
    const pages = []
    const maxVisible = 7 // 最多显示的页码数
    const halfVisible = Math.floor(maxVisible / 2)

    let startPage = Math.max(1, currentPageRef.value - halfVisible)
    let endPage = Math.min(totalPages.value, startPage + maxVisible - 1)

    if (endPage - startPage + 1 < maxVisible) {
      startPage = Math.max(1, endPage - maxVisible + 1)
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i)
    }

    return pages
  })

  // 跳转到指定页
  function goToPage(page) {
    const targetPage = Math.max(1, Math.min(page, totalPages.value || 1))
    currentPageRef.value = targetPage
    return targetPage
  }

  // 上一页
  function prevPage() {
    if (hasPrevPage.value) {
      currentPageRef.value--
    }
    return currentPageRef.value
  }

  // 下一页
  function nextPage() {
    if (hasNextPage.value) {
      currentPageRef.value++
    }
    return currentPageRef.value
  }

  // 第一页
  function firstPage() {
    currentPageRef.value = 1
    return 1
  }

  // 最后一页
  function lastPage() {
    currentPageRef.value = totalPages.value || 1
    return currentPageRef.value
  }

  // 改变每页大小
  function changePageSize(size) {
    const oldPage = currentPageRef.value
    pageSizeRef.value = size
    // 重新计算当前页，确保数据范围正确
    const newPage = Math.min(oldPage, totalPages.value || 1)
    currentPageRef.value = newPage
    return { pageSize: size, currentPage: newPage }
  }

  // 重置分页
  function reset() {
    currentPageRef.value = 1
    pageSizeRef.value = pageSize
    totalRef.value = total
  }

  // 获取分页参数（用于 API 请求）
  function getPaginationParams() {
    return {
      page: currentPageRef.value,
      pageSize: pageSizeRef.value,
      offset: (currentPageRef.value - 1) * pageSizeRef.value,
      limit: pageSizeRef.value
    }
  }

  return {
    currentPage: currentPageRef,
    pageSize: pageSizeRef,
    total: totalRef,
    totalPages,
    pageRange,
    hasPrevPage,
    hasNextPage,
    pageList,
    pageSizes,
    goToPage,
    prevPage,
    nextPage,
    firstPage,
    lastPage,
    changePageSize,
    reset,
    getPaginationParams
  }
}

// 导入 computed
import { computed } from 'vue'

describe('usePagination 组合式函数', () => {
  /**
   * 初始状态测试
   */
  describe('初始状态', () => {
    it('应该使用默认值初始化', () => {
      const pagination = usePagination()

      expect(pagination.currentPage.value).toBe(1)
      expect(pagination.pageSize.value).toBe(10)
      expect(pagination.total.value).toBe(0)
      expect(pagination.pageSizes).toEqual([10, 20, 50, 100])
    })

    it('应该接受自定义初始值', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 20,
        currentPage: 3
      })

      expect(pagination.currentPage.value).toBe(3)
      expect(pagination.pageSize.value).toBe(20)
      expect(pagination.total.value).toBe(100)
    })

    it('应该接受自定义 pageSizes', () => {
      const pagination = usePagination({
        pageSizes: [5, 10, 15]
      })

      expect(pagination.pageSizes).toEqual([5, 10, 15])
    })
  })

  /**
   * 总页数计算测试
   */
  describe('总页数计算', () => {
    it('应该正确计算总页数', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10
      })

      expect(pagination.totalPages.value).toBe(10)
    })

    it('有余数时应该向上取整', () => {
      const pagination = usePagination({
        total: 95,
        pageSize: 10
      })

      expect(pagination.totalPages.value).toBe(10)
    })

    it('总数据为0时总页数应该为0', () => {
      const pagination = usePagination({
        total: 0,
        pageSize: 10
      })

      expect(pagination.totalPages.value).toBe(0)
    })

    it('改变 pageSize 应该重新计算总页数', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10
      })

      expect(pagination.totalPages.value).toBe(10)

      pagination.changePageSize(20)

      expect(pagination.totalPages.value).toBe(5)
    })

    it('改变 total 应该重新计算总页数', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10
      })

      expect(pagination.totalPages.value).toBe(10)

      pagination.total.value = 50

      expect(pagination.totalPages.value).toBe(5)
    })
  })

  /**
   * 页码范围计算测试
   */
  describe('页码范围计算', () => {
    it('应该正确计算第一页的数据范围', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 1
      })

      expect(pagination.pageRange.value).toEqual({ start: 0, end: 10 })
    })

    it('应该正确计算中间页的数据范围', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 3
      })

      expect(pagination.pageRange.value).toEqual({ start: 20, end: 30 })
    })

    it('最后一页的范围不应该超过总数', () => {
      const pagination = usePagination({
        total: 95,
        pageSize: 10,
        currentPage: 10
      })

      expect(pagination.pageRange.value).toEqual({ start: 90, end: 95 })
    })

    it('改变页码应该更新数据范围', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 1
      })

      expect(pagination.pageRange.value).toEqual({ start: 0, end: 10 })

      pagination.goToPage(5)

      expect(pagination.pageRange.value).toEqual({ start: 40, end: 50 })
    })
  })

  /**
   * 翻页功能测试
   */
  describe('翻页功能', () => {
    it('goToPage 应该跳转到指定页', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10
      })

      const result = pagination.goToPage(5)

      expect(result).toBe(5)
      expect(pagination.currentPage.value).toBe(5)
    })

    it('goToPage 不应该小于1', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 5
      })

      const result = pagination.goToPage(0)

      expect(result).toBe(1)
      expect(pagination.currentPage.value).toBe(1)
    })

    it('goToPage 不应该超过总页数', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 1
      })

      const result = pagination.goToPage(100)

      expect(result).toBe(10)
      expect(pagination.currentPage.value).toBe(10)
    })

    it('prevPage 应该返回上一页', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 5
      })

      const result = pagination.prevPage()

      expect(result).toBe(4)
      expect(pagination.currentPage.value).toBe(4)
    })

    it('在第一页时 prevPage 不应该改变页码', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 1
      })

      const result = pagination.prevPage()

      expect(result).toBe(1)
      expect(pagination.currentPage.value).toBe(1)
    })

    it('nextPage 应该返回下一页', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 5
      })

      const result = pagination.nextPage()

      expect(result).toBe(6)
      expect(pagination.currentPage.value).toBe(6)
    })

    it('在最后一页时 nextPage 不应该改变页码', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 10
      })

      const result = pagination.nextPage()

      expect(result).toBe(10)
      expect(pagination.currentPage.value).toBe(10)
    })

    it('firstPage 应该跳转到第一页', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 5
      })

      const result = pagination.firstPage()

      expect(result).toBe(1)
      expect(pagination.currentPage.value).toBe(1)
    })

    it('lastPage 应该跳转到最后一页', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 1
      })

      const result = pagination.lastPage()

      expect(result).toBe(10)
      expect(pagination.currentPage.value).toBe(10)
    })

    it('当总页数为0时 lastPage 应该返回1', () => {
      const pagination = usePagination({
        total: 0,
        pageSize: 10,
        currentPage: 1
      })

      const result = pagination.lastPage()

      expect(result).toBe(1)
      expect(pagination.currentPage.value).toBe(1)
    })
  })

  /**
   * 上一页/下一页状态测试
   */
  describe('翻页状态', () => {
    it('第一页时不应该有上一页', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 1
      })

      expect(pagination.hasPrevPage.value).toBe(false)
    })

    it('非第一页时应该有上一页', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 5
      })

      expect(pagination.hasPrevPage.value).toBe(true)
    })

    it('最后一页时不应该有下一页', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 10
      })

      expect(pagination.hasNextPage.value).toBe(false)
    })

    it('非最后一页时应该有下一页', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 5
      })

      expect(pagination.hasNextPage.value).toBe(true)
    })

    it('只有一页时不应该有上一页和下一页', () => {
      const pagination = usePagination({
        total: 5,
        pageSize: 10,
        currentPage: 1
      })

      expect(pagination.hasPrevPage.value).toBe(false)
      expect(pagination.hasNextPage.value).toBe(false)
    })
  })

  /**
   * 页码列表测试
   */
  describe('页码列表', () => {
    it('应该生成正确的页码列表', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 1
      })

      expect(pagination.pageList.value).toEqual([1, 2, 3, 4, 5, 6, 7])
    })

    it('当前页在中间时应该显示周围的页码', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 5
      })

      expect(pagination.pageList.value).toEqual([2, 3, 4, 5, 6, 7, 8])
    })

    it('当前页靠近末尾时应该显示最后的页码', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 10
      })

      expect(pagination.pageList.value).toEqual([4, 5, 6, 7, 8, 9, 10])
    })

    it('总页数较少时应该显示所有页码', () => {
      const pagination = usePagination({
        total: 30,
        pageSize: 10,
        currentPage: 2
      })

      expect(pagination.pageList.value).toEqual([1, 2, 3])
    })

    it('总页数为0时页码列表应该为空', () => {
      const pagination = usePagination({
        total: 0,
        pageSize: 10
      })

      expect(pagination.pageList.value).toEqual([])
    })
  })

  /**
   * 改变每页大小测试
   */
  describe('改变每页大小', () => {
    it('changePageSize 应该改变 pageSize', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10
      })

      const result = pagination.changePageSize(20)

      expect(pagination.pageSize.value).toBe(20)
      expect(result.pageSize).toBe(20)
    })

    it('改变 pageSize 后当前页应该在有效范围内', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 10
      })

      pagination.changePageSize(50)

      expect(pagination.currentPage.value).toBe(2)
    })

    it('改变 pageSize 应该返回新的分页参数', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 5
      })

      const result = pagination.changePageSize(20)

      expect(result).toEqual({ pageSize: 20, currentPage: 5 })
    })
  })

  /**
   * 重置功能测试
   */
  describe('重置功能', () => {
    it('reset 应该重置所有状态到初始值', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 20,
        currentPage: 5
      })

      pagination.goToPage(8)
      pagination.pageSize.value = 50
      pagination.total.value = 200

      pagination.reset()

      expect(pagination.currentPage.value).toBe(1)
      expect(pagination.pageSize.value).toBe(20)
      expect(pagination.total.value).toBe(100)
    })

    it('reset 后应该可以正常使用', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 5
      })

      pagination.reset()
      pagination.nextPage()

      expect(pagination.currentPage.value).toBe(2)
    })
  })

  /**
   * 获取分页参数测试
   */
  describe('获取分页参数', () => {
    it('应该返回正确的分页参数', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 3
      })

      const params = pagination.getPaginationParams()

      expect(params).toEqual({
        page: 3,
        pageSize: 10,
        offset: 20,
        limit: 10
      })
    })

    it('改变分页状态后参数应该更新', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10,
        currentPage: 1
      })

      pagination.goToPage(5)
      pagination.changePageSize(20)

      const params = pagination.getPaginationParams()

      expect(params).toEqual({
        page: 5,
        pageSize: 20,
        offset: 80,
        limit: 20
      })
    })
  })

  /**
   * 边界情况测试
   */
  describe('边界情况', () => {
    it('pageSize 为0时应该处理正确', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 0
      })

      // 避免除以0错误
      expect(pagination.totalPages.value).toBe(Infinity)
    })

    it('负数的 total 应该处理为0页', () => {
      const pagination = usePagination({
        total: -10,
        pageSize: 10
      })

      expect(pagination.totalPages.value).toBe(0)
    })

    it('大数据量时应该正常工作', () => {
      const pagination = usePagination({
        total: 1000000,
        pageSize: 10,
        currentPage: 50000
      })

      expect(pagination.totalPages.value).toBe(100000)
      expect(pagination.pageRange.value).toEqual({
        start: 499990,
        end: 500000
      })
    })

    it('只有一条数据时应该只有一页', () => {
      const pagination = usePagination({
        total: 1,
        pageSize: 10
      })

      expect(pagination.totalPages.value).toBe(1)
      expect(pagination.pageRange.value).toEqual({ start: 0, end: 1 })
      expect(pagination.hasPrevPage.value).toBe(false)
      expect(pagination.hasNextPage.value).toBe(false)
    })

    it('pageSize 大于 total 时应该只有一页', () => {
      const pagination = usePagination({
        total: 5,
        pageSize: 10
      })

      expect(pagination.totalPages.value).toBe(1)
      expect(pagination.pageRange.value).toEqual({ start: 0, end: 5 })
    })
  })

  /**
   * 响应式测试
   */
  describe('响应式', () => {
    it('修改响应式数据应该触发更新', () => {
      const pagination = usePagination({
        total: 100,
        pageSize: 10
      })

      let pageRangeValue

      // 模拟监听
      const stop = watch(() => pagination.pageRange.value, (val) => {
        pageRangeValue = val
      }, { immediate: true, flush: 'sync' })

      expect(pageRangeValue).toEqual({ start: 0, end: 10 })

      pagination.goToPage(2)

      expect(pageRangeValue).toEqual({ start: 10, end: 20 })

      stop()
    })
  })
})

// 导入 watch
import { watch } from 'vue'
