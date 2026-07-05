/**
 * 排序组合式函数
 * 提供通用的排序功能，支持数字、字符串、日期等多种数据类型排序
 */

import { ref, computed } from 'vue'

/**
 * 排序组合式函数
 * @param {Object} options - 配置选项
 * @param {Array} [options.data=[]] - 初始数据
 * @param {string} [options.initialSortKey=''] - 初始排序字段
 * @param {string} [options.initialSortOrder='asc'] - 初始排序方向
 * @param {Object} [options.customSort={}] - 自定义排序函数
 * @returns {Object} 排序状态及相关方法
 */
export function useSort(options = {}) {
  const {
    data = [],
    initialSortKey = '',
    initialSortOrder = 'asc',
    customSort = {}
  } = options

  const sortKey = ref(initialSortKey)
  const sortOrder = ref(initialSortOrder)
  const originalData = ref([...data])

  // 设置数据
  function setData(newData) {
    originalData.value = [...newData]
  }

  // 切换排序
  function toggleSort(key) {
    if (sortKey.value === key) {
      // 切换排序方向
      sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
    } else {
      // 新字段，默认升序
      sortKey.value = key
      sortOrder.value = 'asc'
    }
  }

  // 设置排序
  function setSort(key, order = 'asc') {
    sortKey.value = key
    sortOrder.value = order
  }

  // 清除排序
  function clearSort() {
    sortKey.value = ''
    sortOrder.value = 'asc'
  }

  // 获取排序状态
  function getSortState(key) {
    if (sortKey.value !== key) {
      return null
    }
    return sortOrder.value
  }

  // 排序后的数据
  const sortedData = computed(() => {
    if (!sortKey.value) {
      return [...originalData.value]
    }

    const key = sortKey.value
    const order = sortOrder.value
    const multiplier = order === 'asc' ? 1 : -1

    // 检查是否有自定义排序函数
    if (customSort[key]) {
      return [...originalData.value].sort((a, b) => {
        return customSort[key](a, b) * multiplier
      })
    }

    return [...originalData.value].sort((a, b) => {
      const aVal = a[key]
      const bVal = b[key]

      // 处理 null/undefined
      if (aVal == null && bVal == null) return 0
      if (aVal == null) return 1 * multiplier
      if (bVal == null) return -1 * multiplier

      // 日期比较
      if (aVal instanceof Date && bVal instanceof Date) {
        return (aVal.getTime() - bVal.getTime()) * multiplier
      }

      // 字符串比较
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return aVal.localeCompare(bVal, 'zh-CN') * multiplier
      }

      // 数字比较
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return (aVal - bVal) * multiplier
      }

      // 默认转为字符串比较
      return String(aVal).localeCompare(String(bVal), 'zh-CN') * multiplier
    })
  })

  // 排序配置（用于表格等组件）
  const sortConfig = computed(() => ({
    key: sortKey.value,
    order: sortOrder.value
  }))

  return {
    sortKey,
    sortOrder,
    sortedData,
    sortConfig,
    setData,
    toggleSort,
    setSort,
    clearSort,
    getSortState
  }
}

export default useSort
