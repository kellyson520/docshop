/**
 * storage 本地存储工具单元测试
 * 测试 localStorage 和 sessionStorage 的封装功能
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// 模拟 storage 工具类
class StorageWrapper {
  constructor(storage = localStorage, prefix = '') {
    this.storage = storage
    this.prefix = prefix
  }

  _getKey(key) {
    return this.prefix ? `${this.prefix}:${key}` : key
  }

  get(key, defaultValue = null) {
    try {
      const fullKey = this._getKey(key)
      const item = this.storage.getItem(fullKey)
      if (item === null) return defaultValue
      return JSON.parse(item)
    } catch (error) {
      console.error('Storage get error:', error)
      return defaultValue
    }
  }

  set(key, value) {
    try {
      const fullKey = this._getKey(key)
      this.storage.setItem(fullKey, String(JSON.stringify(value)))
      return true
    } catch (error) {
      console.error('Storage set error:', error)
      return false
    }
  }

  remove(key) {
    try {
      const fullKey = this._getKey(key)
      this.storage.removeItem(fullKey)
      return true
    } catch (error) {
      console.error('Storage remove error:', error)
      return false
    }
  }

  clear() {
    try {
      if (this.prefix) {
        // 只清除带前缀的键
        const keysToRemove = []
        for (let i = 0; i < this.storage.length; i++) {
          const key = this.storage.key(i)
          if (key && key.startsWith(`${this.prefix}:`)) {
            keysToRemove.push(key)
          }
        }
        keysToRemove.forEach(key => this.storage.removeItem(key))
      } else {
        this.storage.clear()
      }
      return true
    } catch (error) {
      console.error('Storage clear error:', error)
      return false
    }
  }

  has(key) {
    try {
      const fullKey = this._getKey(key)
      return this.storage.getItem(fullKey) !== null
    } catch (error) {
      console.error('Storage has error:', error)
      return false
    }
  }

  keys() {
    try {
      const keys = []
      for (let i = 0; i < this.storage.length; i++) {
        const key = this.storage.key(i)
        if (key) {
          if (this.prefix) {
            if (key.startsWith(`${this.prefix}:`)) {
              keys.push(key.substring(this.prefix.length + 1))
            }
          } else {
            keys.push(key)
          }
        }
      }
      return keys
    } catch (error) {
      console.error('Storage keys error:', error)
      return []
    }
  }

  size() {
    return this.keys().length
  }
}

// 创建 localStorage 和 sessionStorage 的包装器
function createStorage(type = 'local', prefix = '') {
  const storage = type === 'session' ? sessionStorage : localStorage
  return new StorageWrapper(storage, prefix)
}

describe('storage 本地存储工具', () => {
  let localStorageMock
  let sessionStorageMock
  let storage
  let sessionStorageWrapper

  beforeEach(() => {
    // 创建模拟的 localStorage
    let localStore = {}
    localStorageMock = {
      getItem: vi.fn((key) => localStore[key] || null),
      setItem: vi.fn((key, value) => { localStore[key] = value }),
      removeItem: vi.fn((key) => { delete localStore[key] }),
      clear: vi.fn(() => { localStore = {} }),
      key: vi.fn((index) => Object.keys(localStore)[index] || null),
      get length() { return Object.keys(localStore).length }
    }
    Object.defineProperty(window, 'localStorage', { value: localStorageMock, writable: true })

    // 创建模拟的 sessionStorage
    let sessionStore = {}
    sessionStorageMock = {
      getItem: vi.fn((key) => sessionStore[key] || null),
      setItem: vi.fn((key, value) => { sessionStore[key] = value }),
      removeItem: vi.fn((key) => { delete sessionStore[key] }),
      clear: vi.fn(() => { sessionStore = {} }),
      key: vi.fn((index) => Object.keys(sessionStore)[index] || null),
      get length() { return Object.keys(sessionStore).length }
    }
    Object.defineProperty(window, 'sessionStorage', { value: sessionStorageMock, writable: true })

    storage = new StorageWrapper(localStorageMock)
    sessionStorageWrapper = new StorageWrapper(sessionStorageMock)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  /**
   * 基本操作测试
   */
  describe('基本操作', () => {
    it('set 应该存储值', () => {
      const result = storage.set('key', 'value')

      expect(result).toBe(true)
      expect(localStorageMock.setItem).toHaveBeenCalledWith('key', '"value"')
    })

    it('get 应该获取值', () => {
      localStorageMock.getItem.mockReturnValue('"stored value"')

      const result = storage.get('key')

      expect(result).toBe('stored value')
      expect(localStorageMock.getItem).toHaveBeenCalledWith('key')
    })

    it('get 不存在的键应该返回默认值', () => {
      localStorageMock.getItem.mockReturnValue(null)

      const result = storage.get('nonexistent', 'default')

      expect(result).toBe('default')
    })

    it('remove 应该删除键', () => {
      const result = storage.remove('key')

      expect(result).toBe(true)
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('key')
    })

    it('clear 应该清除所有数据', () => {
      const result = storage.clear()

      expect(result).toBe(true)
      expect(localStorageMock.clear).toHaveBeenCalled()
    })
  })

  /**
   * 数据类型测试
   */
  describe('数据类型', () => {
    it('应该正确存储字符串', () => {
      storage.set('string', 'hello world')

      expect(localStorageMock.setItem).toHaveBeenCalledWith('string', '"hello world"')
    })

    it('应该正确存储数字', () => {
      storage.set('number', 42)

      expect(localStorageMock.setItem).toHaveBeenCalledWith('number', '42')
    })

    it('应该正确存储布尔值', () => {
      storage.set('bool', true)

      expect(localStorageMock.setItem).toHaveBeenCalledWith('bool', 'true')
    })

    it('应该正确存储对象', () => {
      const obj = { name: 'test', value: 123 }
      storage.set('object', obj)

      expect(localStorageMock.setItem).toHaveBeenCalledWith('object', JSON.stringify(obj))
    })

    it('应该正确存储数组', () => {
      const arr = [1, 2, 3, 'test']
      storage.set('array', arr)

      expect(localStorageMock.setItem).toHaveBeenCalledWith('array', JSON.stringify(arr))
    })

    it('应该正确存储 null', () => {
      storage.set('null', null)

      expect(localStorageMock.setItem).toHaveBeenCalledWith('null', 'null')
    })

    it('应该正确获取并解析对象', () => {
      const obj = { name: 'test', nested: { value: 123 } }
      localStorageMock.getItem.mockReturnValue(JSON.stringify(obj))

      const result = storage.get('object')

      expect(result).toEqual(obj)
    })

    it('应该正确获取并解析数组', () => {
      const arr = [1, 2, { name: 'test' }]
      localStorageMock.getItem.mockReturnValue(JSON.stringify(arr))

      const result = storage.get('array')

      expect(result).toEqual(arr)
    })
  })

  /**
   * 前缀功能测试
   */
  describe('前缀功能', () => {
    it('应该使用前缀存储键', () => {
      const prefixedStorage = new StorageWrapper(localStorageMock, 'app')

      prefixedStorage.set('key', 'value')

      expect(localStorageMock.setItem).toHaveBeenCalledWith('app:key', '"value"')
    })

    it('应该使用前缀获取键', () => {
      const prefixedStorage = new StorageWrapper(localStorageMock, 'app')
      localStorageMock.getItem.mockReturnValue('"value"')

      prefixedStorage.get('key')

      expect(localStorageMock.getItem).toHaveBeenCalledWith('app:key')
    })

    it('应该使用前缀删除键', () => {
      const prefixedStorage = new StorageWrapper(localStorageMock, 'app')

      prefixedStorage.remove('key')

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('app:key')
    })

    it('带前缀的 clear 应该只清除带前缀的键', () => {
      const prefixedStorage = new StorageWrapper(localStorageMock, 'app')

      // 模拟存储中有多个键
      let store = {
        'app:key1': 'value1',
        'app:key2': 'value2',
        'other:key': 'value3'
      }
      localStorageMock.key = vi.fn((index) => Object.keys(store)[index])
      localStorageMock.removeItem = vi.fn((key) => { delete store[key] })
      Object.defineProperty(localStorageMock, 'length', {
        get: () => Object.keys(store).length
      })

      prefixedStorage.clear()

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('app:key1')
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('app:key2')
      expect(localStorageMock.removeItem).not.toHaveBeenCalledWith('other:key')
    })

    it('无前缀的 clear 应该清除所有数据', () => {
      storage.clear()

      expect(localStorageMock.clear).toHaveBeenCalled()
    })
  })

  /**
   * has 方法测试
   */
  describe('has 方法', () => {
    it('存在的键应该返回 true', () => {
      localStorageMock.getItem.mockReturnValue('"value"')

      const result = storage.has('existing')

      expect(result).toBe(true)
    })

    it('不存在的键应该返回 false', () => {
      localStorageMock.getItem.mockReturnValue(null)

      const result = storage.has('nonexistent')

      expect(result).toBe(false)
    })

    it('带前缀的 has 应该正确工作', () => {
      const prefixedStorage = new StorageWrapper(localStorageMock, 'app')
      localStorageMock.getItem.mockReturnValue('"value"')

      prefixedStorage.has('key')

      expect(localStorageMock.getItem).toHaveBeenCalledWith('app:key')
    })
  })

  /**
   * keys 方法测试
   */
  describe('keys 方法', () => {
    it('应该返回所有键', () => {
      const keys = ['key1', 'key2', 'key3']
      let index = 0
      localStorageMock.key = vi.fn(() => {
        const key = keys[index]
        index++
        return key
      })
      Object.defineProperty(localStorageMock, 'length', { value: 3 })

      const result = storage.keys()

      expect(result).toEqual(keys)
    })

    it('应该返回带前缀的键（去掉前缀）', () => {
      const prefixedStorage = new StorageWrapper(localStorageMock, 'app')
      const keys = ['app:key1', 'app:key2', 'other:key3']
      let index = 0
      localStorageMock.key = vi.fn(() => {
        const key = keys[index]
        index++
        return key
      })
      Object.defineProperty(localStorageMock, 'length', { value: 3 })

      const result = prefixedStorage.keys()

      expect(result).toEqual(['key1', 'key2'])
    })

    it('空存储应该返回空数组', () => {
      Object.defineProperty(localStorageMock, 'length', { value: 0 })

      const result = storage.keys()

      expect(result).toEqual([])
    })
  })

  /**
   * size 方法测试
   */
  describe('size 方法', () => {
    it('应该返回正确的数量', () => {
      const keys = ['key1', 'key2']
      let index = 0
      localStorageMock.key = vi.fn(() => {
        const key = keys[index]
        index++
        return key
      })
      Object.defineProperty(localStorageMock, 'length', { value: 2 })

      const result = storage.size()

      expect(result).toBe(2)
    })

    it('带前缀应该只计算带前缀的键', () => {
      const prefixedStorage = new StorageWrapper(localStorageMock, 'app')
      const keys = ['app:key1', 'app:key2', 'other:key3']
      let index = 0
      localStorageMock.key = vi.fn(() => {
        const key = keys[index]
        index++
        return key
      })
      Object.defineProperty(localStorageMock, 'length', { value: 3 })

      const result = prefixedStorage.size()

      expect(result).toBe(2)
    })
  })

  /**
   * sessionStorage 测试
   */
  describe('sessionStorage', () => {
    it('应该使用 sessionStorage', () => {
      sessionStorageWrapper.set('key', 'value')

      expect(sessionStorageMock.setItem).toHaveBeenCalledWith('key', '"value"')
    })

    it('应该从 sessionStorage 获取', () => {
      sessionStorageMock.getItem.mockReturnValue('"value"')

      const result = sessionStorageWrapper.get('key')

      expect(result).toBe('value')
      expect(sessionStorageMock.getItem).toHaveBeenCalledWith('key')
    })

    it('应该清除 sessionStorage', () => {
      sessionStorageWrapper.clear()

      expect(sessionStorageMock.clear).toHaveBeenCalled()
    })
  })

  /**
   * 错误处理测试
   */
  describe('错误处理', () => {
    it('get 应该处理 JSON 解析错误', () => {
      localStorageMock.getItem.mockReturnValue('invalid json')
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const result = storage.get('key', 'default')

      expect(result).toBe('default')
      expect(consoleSpy).toHaveBeenCalled()

      consoleSpy.mockRestore()
    })

    it('set 应该处理存储错误', () => {
      localStorageMock.setItem.mockImplementation(() => {
        throw new Error('QuotaExceededError')
      })
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const result = storage.set('key', 'value')

      expect(result).toBe(false)
      expect(consoleSpy).toHaveBeenCalled()

      consoleSpy.mockRestore()
    })

    it('remove 应该处理错误', () => {
      localStorageMock.removeItem.mockImplementation(() => {
        throw new Error('Storage error')
      })
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const result = storage.remove('key')

      expect(result).toBe(false)
      expect(consoleSpy).toHaveBeenCalled()

      consoleSpy.mockRestore()
    })

    it('clear 应该处理错误', () => {
      localStorageMock.clear.mockImplementation(() => {
        throw new Error('Storage error')
      })
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const result = storage.clear()

      expect(result).toBe(false)
      expect(consoleSpy).toHaveBeenCalled()

      consoleSpy.mockRestore()
    })

    it('has 应该处理错误', () => {
      localStorageMock.getItem.mockImplementation(() => {
        throw new Error('Storage error')
      })
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const result = storage.has('key')

      expect(result).toBe(false)
      expect(consoleSpy).toHaveBeenCalled()

      consoleSpy.mockRestore()
    })

    it('keys 应该处理错误', () => {
      Object.defineProperty(localStorageMock, 'length', {
        get: () => { throw new Error('Storage error') }
      })
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const result = storage.keys()

      expect(result).toEqual([])
      expect(consoleSpy).toHaveBeenCalled()

      consoleSpy.mockRestore()
    })
  })

  /**
   * 边界情况测试
   */
  describe('边界情况', () => {
    it('应该处理空字符串键', () => {
      storage.set('', 'value')

      expect(localStorageMock.setItem).toHaveBeenCalledWith('', '"value"')
    })

    it('应该处理特殊字符键', () => {
      const specialKey = 'key:with:colons'
      storage.set(specialKey, 'value')

      expect(localStorageMock.setItem).toHaveBeenCalledWith(specialKey, '"value"')
    })

    it('应该处理大对象', () => {
      const largeObj = {}
      for (let i = 0; i < 1000; i++) {
        largeObj[`key${i}`] = `value${i}`
      }

      const result = storage.set('large', largeObj)

      expect(result).toBe(true)
      expect(localStorageMock.setItem).toHaveBeenCalledWith('large', JSON.stringify(largeObj))
    })

    it('应该处理循环引用（会抛出错误）', () => {
      const obj = { name: 'test' }
      obj.self = obj

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const result = storage.set('circular', obj)

      expect(result).toBe(false)
      expect(consoleSpy).toHaveBeenCalled()

      consoleSpy.mockRestore()
    })

    it('应该处理 undefined 值', () => {
      storage.set('undefined', undefined)

      expect(localStorageMock.setItem).toHaveBeenCalledWith('undefined', 'undefined')
    })

    it('应该处理空对象', () => {
      storage.set('empty', {})

      expect(localStorageMock.setItem).toHaveBeenCalledWith('empty', '{}')
    })

    it('应该处理空数组', () => {
      storage.set('empty', [])

      expect(localStorageMock.setItem).toHaveBeenCalledWith('empty', '[]')
    })

    it('获取空对象应该返回空对象', () => {
      localStorageMock.getItem.mockReturnValue('{}')

      const result = storage.get('empty')

      expect(result).toEqual({})
    })

    it('获取空数组应该返回空数组', () => {
      localStorageMock.getItem.mockReturnValue('[]')

      const result = storage.get('empty')

      expect(result).toEqual([])
    })
  })

  /**
   * 存储配额测试
   */
  describe('存储配额', () => {
    it('应该处理存储配额超出错误', () => {
      localStorageMock.setItem.mockImplementation(() => {
        const error = new Error('QuotaExceededError')
        error.name = 'QuotaExceededError'
        throw error
      })
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const result = storage.set('key', 'value')

      expect(result).toBe(false)

      consoleSpy.mockRestore()
    })
  })

  /**
   * 并发操作测试
   */
  describe('并发操作', () => {
    it('多次设置同一键应该覆盖', () => {
      storage.set('key', 'value1')
      storage.set('key', 'value2')
      storage.set('key', 'value3')

      expect(localStorageMock.setItem).toHaveBeenLastCalledWith('key', '"value3"')
    })

    it('设置和获取应该一致', () => {
      const testData = { test: 'data', number: 123 }
      localStorageMock.getItem.mockReturnValue(JSON.stringify(testData))

      storage.set('key', testData)
      const result = storage.get('key')

      expect(result).toEqual(testData)
    })
  })
})
