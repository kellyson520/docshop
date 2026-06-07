/**
 * useSort 组合式函数单元测试
 * 测试排序功能的计算属性、方法和边界情况
 */

import { describe, it, expect, vi } from 'vitest'
import { ref, computed } from 'vue'

// 模拟 useSort 组合式函数
function useSort(options = {}) {
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

describe('useSort 组合式函数', () => {
  // 测试数据
  const mockData = [
    { id: 1, name: '张三', age: 25, score: 85.5, createdAt: new Date('2024-01-15') },
    { id: 2, name: '李四', age: 30, score: 92.0, createdAt: new Date('2024-01-10') },
    { id: 3, name: '王五', age: 20, score: 78.5, createdAt: new Date('2024-01-20') },
    { id: 4, name: '赵六', age: 28, score: 88.0, createdAt: new Date('2024-01-12') },
    { id: 5, name: '钱七', age: 35, score: 95.5, createdAt: new Date('2024-01-08') }
  ]

  /**
   * 初始状态测试
   */
  describe('初始状态', () => {
    it('应该使用默认值初始化', () => {
      const sort = useSort()

      expect(sort.sortKey.value).toBe('')
      expect(sort.sortOrder.value).toBe('asc')
      expect(sort.sortedData.value).toEqual([])
    })

    it('应该接受自定义初始值', () => {
      const sort = useSort({
        data: mockData,
        initialSortKey: 'age',
        initialSortOrder: 'desc'
      })

      expect(sort.sortKey.value).toBe('age')
      expect(sort.sortOrder.value).toBe('desc')
    })

    it('初始数据应该被正确设置', () => {
      const sort = useSort({ data: mockData })

      expect(sort.sortedData.value).toEqual(mockData)
    })
  })

  /**
   * 数字排序测试
   */
  describe('数字排序', () => {
    it('应该按数字升序排序', () => {
      const sort = useSort({ data: mockData })

      sort.setSort('age', 'asc')

      const ages = sort.sortedData.value.map(item => item.age)
      expect(ages).toEqual([20, 25, 28, 30, 35])
    })

    it('应该按数字降序排序', () => {
      const sort = useSort({ data: mockData })

      sort.setSort('age', 'desc')

      const ages = sort.sortedData.value.map(item => item.age)
      expect(ages).toEqual([35, 30, 28, 25, 20])
    })

    it('应该正确处理小数排序', () => {
      const sort = useSort({ data: mockData })

      sort.setSort('score', 'asc')

      const scores = sort.sortedData.value.map(item => item.score)
      expect(scores).toEqual([78.5, 85.5, 88.0, 92.0, 95.5])
    })
  })

  /**
   * 字符串排序测试
   */
  describe('字符串排序', () => {
    it('应该按字符串升序排序', () => {
      const sort = useSort({ data: mockData })

      sort.setSort('name', 'asc')

      const names = sort.sortedData.value.map(item => item.name)
      expect(names).toEqual(['李四', '钱七', '王五', '张三', '赵六'])
    })

    it('应该按字符串降序排序', () => {
      const sort = useSort({ data: mockData })

      sort.setSort('name', 'desc')

      const names = sort.sortedData.value.map(item => item.name)
      expect(names).toEqual(['赵六', '张三', '王五', '钱七', '李四'])
    })

    it('应该正确处理中文排序', () => {
      const chineseData = [
        { name: '重庆' },
        { name: '北京' },
        { name: '上海' },
        { name: '天津' }
      ]
      const sort = useSort({ data: chineseData })

      sort.setSort('name', 'asc')

      const names = sort.sortedData.value.map(item => item.name)
      expect(names).toEqual(['北京', '重庆', '上海', '天津'])
    })
  })

  /**
   * 日期排序测试
   */
  describe('日期排序', () => {
    it('应该按日期升序排序', () => {
      const sort = useSort({ data: mockData })

      sort.setSort('createdAt', 'asc')

      const dates = sort.sortedData.value.map(item => item.createdAt)
      expect(dates[0]).toEqual(new Date('2024-01-08'))
      expect(dates[dates.length - 1]).toEqual(new Date('2024-01-20'))
    })

    it('应该按日期降序排序', () => {
      const sort = useSort({ data: mockData })

      sort.setSort('createdAt', 'desc')

      const dates = sort.sortedData.value.map(item => item.createdAt)
      expect(dates[0]).toEqual(new Date('2024-01-20'))
      expect(dates[dates.length - 1]).toEqual(new Date('2024-01-08'))
    })
  })

  /**
   * 切换排序测试
   */
  describe('切换排序', () => {
    it('toggleSort 应该设置排序字段', () => {
      const sort = useSort({ data: mockData })

      sort.toggleSort('age')

      expect(sort.sortKey.value).toBe('age')
      expect(sort.sortOrder.value).toBe('asc')
    })

    it('toggleSort 相同字段应该切换排序方向', () => {
      const sort = useSort({ data: mockData })

      sort.toggleSort('age')
      expect(sort.sortOrder.value).toBe('asc')

      sort.toggleSort('age')
      expect(sort.sortOrder.value).toBe('desc')

      sort.toggleSort('age')
      expect(sort.sortOrder.value).toBe('asc')
    })

    it('toggleSort 不同字段应该重置为升序', () => {
      const sort = useSort({ data: mockData })

      sort.toggleSort('age')
      sort.toggleSort('age') // desc
      sort.toggleSort('name') // 新字段，应该重置为 asc

      expect(sort.sortKey.value).toBe('name')
      expect(sort.sortOrder.value).toBe('asc')
    })
  })

  /**
   * 清除排序测试
   */
  describe('清除排序', () => {
    it('clearSort 应该清除排序状态', () => {
      const sort = useSort({
        data: mockData,
        initialSortKey: 'age',
        initialSortOrder: 'desc'
      })

      sort.clearSort()

      expect(sort.sortKey.value).toBe('')
      expect(sort.sortOrder.value).toBe('asc')
    })

    it('清除排序后应该返回原始数据顺序', () => {
      const sort = useSort({ data: mockData })

      sort.setSort('age', 'desc')
      sort.clearSort()

      expect(sort.sortedData.value).toEqual(mockData)
    })
  })

  /**
   * 获取排序状态测试
   */
  describe('获取排序状态', () => {
    it('getSortState 应该返回当前排序方向', () => {
      const sort = useSort({ data: mockData })

      sort.setSort('age', 'desc')

      expect(sort.getSortState('age')).toBe('desc')
    })

    it('getSortState 非当前排序字段应该返回 null', () => {
      const sort = useSort({ data: mockData })

      sort.setSort('age', 'asc')

      expect(sort.getSortState('name')).toBeNull()
    })

    it('无排序时应该返回 null', () => {
      const sort = useSort({ data: mockData })

      expect(sort.getSortState('age')).toBeNull()
    })
  })

  /**
   * 设置数据测试
   */
  describe('设置数据', () => {
    it('setData 应该更新数据', () => {
      const sort = useSort({ data: mockData })
      const newData = [
        { id: 10, age: 50 },
        { id: 20, age: 40 }
      ]

      sort.setData(newData)

      expect(sort.sortedData.value).toEqual(newData)
    })

    it('setData 后排序应该应用到新数据', () => {
      const sort = useSort({ data: mockData })
      sort.setSort('age', 'asc')

      const newData = [
        { id: 10, age: 50 },
        { id: 20, age: 40 }
      ]
      sort.setData(newData)

      const ages = sort.sortedData.value.map(item => item.age)
      expect(ages).toEqual([40, 50])
    })

    it('setData 不应该修改原始数组', () => {
      const original = [...mockData]
      const sort = useSort({ data: original })

      const newData = [{ id: 1, age: 100 }]
      sort.setData(newData)

      expect(original).toEqual(mockData)
    })
  })

  /**
   * 排序配置测试
   */
  describe('排序配置', () => {
    it('sortConfig 应该包含当前排序信息', () => {
      const sort = useSort({
        data: mockData,
        initialSortKey: 'age',
        initialSortOrder: 'desc'
      })

      expect(sort.sortConfig.value).toEqual({
        key: 'age',
        order: 'desc'
      })
    })

    it('sortConfig 应该响应排序变化', () => {
      const sort = useSort({ data: mockData })

      sort.setSort('name', 'asc')

      expect(sort.sortConfig.value).toEqual({
        key: 'name',
        order: 'asc'
      })

      sort.toggleSort('name')

      expect(sort.sortConfig.value).toEqual({
        key: 'name',
        order: 'desc'
      })
    })
  })

  /**
   * 自定义排序测试
   */
  describe('自定义排序', () => {
    it('应该使用自定义排序函数', () => {
      const customSort = {
        age: (a, b) => b.age - a.age // 降序
      }
      const sort = useSort({
        data: mockData,
        customSort
      })

      sort.setSort('age', 'asc') // 即使指定 asc，也应该使用自定义函数

      const ages = sort.sortedData.value.map(item => item.age)
      expect(ages).toEqual([35, 30, 28, 25, 20])
    })

    it('自定义排序应该支持升序', () => {
      const customSort = {
        score: (a, b) => a.score - b.score
      }
      const sort = useSort({
        data: mockData,
        customSort
      })

      sort.setSort('score', 'asc')

      const scores = sort.sortedData.value.map(item => item.score)
      expect(scores).toEqual([78.5, 85.5, 88.0, 92.0, 95.5])
    })

    it('没有自定义排序的字段应该使用默认排序', () => {
      const customSort = {
        score: (a, b) => a.score - b.score
      }
      const sort = useSort({
        data: mockData,
        customSort
      })

      sort.setSort('age', 'asc')

      const ages = sort.sortedData.value.map(item => item.age)
      expect(ages).toEqual([20, 25, 28, 30, 35])
    })
  })

  /**
   * 边界情况测试
   */
  describe('边界情况', () => {
    it('空数组排序不应该报错', () => {
      const sort = useSort({ data: [] })

      sort.setSort('age', 'asc')

      expect(sort.sortedData.value).toEqual([])
    })

    it('单条数据排序不应该报错', () => {
      const singleData = [{ id: 1, age: 25 }]
      const sort = useSort({ data: singleData })

      sort.setSort('age', 'asc')

      expect(sort.sortedData.value).toEqual(singleData)
    })

    it('应该正确处理 null 值', () => {
      const dataWithNull = [
        { id: 1, age: null },
        { id: 2, age: 25 },
        { id: 3, age: null }
      ]
      const sort = useSort({ data: dataWithNull })

      sort.setSort('age', 'asc')

      const ages = sort.sortedData.value.map(item => item.age)
      expect(ages).toEqual([25, null, null])
    })

    it('应该正确处理 undefined 值', () => {
      const dataWithUndefined = [
        { id: 1, age: undefined },
        { id: 2, age: 25 },
        { id: 3 }
      ]
      const sort = useSort({ data: dataWithUndefined })

      sort.setSort('age', 'asc')

      const ages = sort.sortedData.value.map(item => item.age)
      expect(ages).toEqual([25, undefined, undefined])
    })

    it('应该正确处理混合类型数据', () => {
      const mixedData = [
        { id: 1, value: '100' },
        { id: 2, value: 50 },
        { id: 3, value: 'abc' }
      ]
      const sort = useSort({ data: mixedData })

      sort.setSort('value', 'asc')

      // 默认转为字符串比较
      const values = sort.sortedData.value.map(item => item.value)
      expect(values).toEqual(['100', 50, 'abc'])
    })

    it('不存在的排序字段应该返回原始顺序', () => {
      const sort = useSort({ data: mockData })

      sort.setSort('nonExistent', 'asc')

      expect(sort.sortedData.value).toEqual(mockData)
    })

    it('大数据量排序应该正常工作', () => {
      const largeData = Array.from({ length: 10000 }, (_, i) => ({
        id: i,
        value: Math.random()
      }))
      const sort = useSort({ data: largeData })

      sort.setSort('value', 'asc')

      const values = sort.sortedData.value.map(item => item.value)
      // 验证是升序
      for (let i = 1; i < values.length; i++) {
        expect(values[i]).toBeGreaterThanOrEqual(values[i - 1])
      }
    })
  })

  /**
   * 响应式测试
   */
  describe('响应式', () => {
    it('修改原始数据应该触发排序更新', () => {
      const data = ref([...mockData])
      const sort = useSort({ data: data.value })

      sort.setSort('age', 'asc')

      // 修改原始数据
      data.value.push({ id: 6, age: 15 })
      sort.setData(data.value)

      const ages = sort.sortedData.value.map(item => item.age)
      expect(ages).toEqual([15, 20, 25, 28, 30, 35])
    })

    it('排序状态变化应该触发 sortedData 更新', () => {
      const sort = useSort({ data: mockData })

      let sortedAges

      // 使用 watch 监听
      const stop = watch(() => sort.sortedData.value, (val) => {
        sortedAges = val.map(item => item.age)
      }, { immediate: true, flush: 'sync' })

      expect(sortedAges).toEqual([25, 30, 20, 28, 35])

      sort.setSort('age', 'asc')

      expect(sortedAges).toEqual([20, 25, 28, 30, 35])

      stop()
    })
  })

  /**
   * 多级排序测试
   */
  describe('多级排序场景', () => {
    it('应该先按第一字段排序，再按第二字段排序', () => {
      const data = [
        { name: '张三', age: 25 },
        { name: '李四', age: 25 },
        { name: '张三', age: 20 }
      ]
      const sort = useSort({ data })

      // 模拟多级排序：先按 name 排序，再按 age 排序
      sort.setSort('name', 'asc')
      const nameSorted = [...sort.sortedData.value]

      // 在相同 name 的情况下按 age 排序
      const grouped = nameSorted.sort((a, b) => {
        if (a.name === b.name) {
          return a.age - b.age
        }
        return 0
      })

      expect(grouped.map(item => ({ name: item.name, age: item.age }))).toEqual([
        { name: '李四', age: 25 },
        { name: '张三', age: 20 },
        { name: '张三', age: 25 }
      ])
    })
  })
})

// 导入 watch
import { watch } from 'vue'
