/**
 * 分页组合式函数
 * 提供通用的分页功能，支持页码计算、翻页、每页大小调整等
 */

import { ref, computed } from 'vue'

/**
 * 分页组合式函数
 * @param {Object} options - 配置选项
 * @param {number} [options.total=0] - 总数据量
 * @param {number} [options.pageSize=10] - 每页大小
 * @param {number} [options.currentPage=1] - 当前页码
 * @param {Array} [options.pageSizes=[10, 20, 50, 100]] - 可选的每页大小列表
 * @returns {Object} 分页状态及相关方法
 */
export function usePagination(options = {}) {
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

export default usePagination
