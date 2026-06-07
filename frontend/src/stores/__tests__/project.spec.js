/**
 * project store 单元测试
 * 测试项目状态管理功能
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useProjectStore } from '../project.js'

// 模拟 API 模块
const mockGetProjects = vi.fn()
const mockGetProject = vi.fn()
const mockCreateProject = vi.fn()
const mockDeleteProject = vi.fn()
vi.mock('@/api/project', () => ({
  getProjects: (...args) => mockGetProjects(...args),
  getProject: (...args) => mockGetProject(...args),
  createProject: (...args) => mockCreateProject(...args),
  deleteProject: (...args) => mockDeleteProject(...args)
}))

describe('project store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockGetProjects.mockClear()
    mockGetProject.mockClear()
    mockCreateProject.mockClear()
    mockDeleteProject.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  /**
   * 初始状态测试
   */
  describe('初始状态', () => {
    it('应该具有正确的初始状态', () => {
      const store = useProjectStore()

      expect(store.projects).toEqual([])
      expect(store.currentProject).toBeNull()
      expect(store.loading).toBe(false)
    })

    it('projects 应该是空数组', () => {
      const store = useProjectStore()

      expect(Array.isArray(store.projects)).toBe(true)
      expect(store.projects.length).toBe(0)
    })

    it('currentProject 应该是 null', () => {
      const store = useProjectStore()

      expect(store.currentProject).toBeNull()
    })

    it('loading 应该是 false', () => {
      const store = useProjectStore()

      expect(store.loading).toBe(false)
    })
  })

  /**
   * 获取项目列表测试
   */
  describe('获取项目列表', () => {
    it('fetchProjects 应该调用 API', async () => {
      const store = useProjectStore()
      const projectsData = {
        items: [
          { id: 1, name: '项目1' },
          { id: 2, name: '项目2' }
        ]
      }
      mockGetProjects.mockResolvedValueOnce(projectsData)

      await store.fetchProjects()

      expect(mockGetProjects).toHaveBeenCalled()
    })

    it('fetchProjects 应该传入参数', async () => {
      const store = useProjectStore()
      const projectsData = { items: [] }
      mockGetProjects.mockResolvedValueOnce(projectsData)

      const params = { page: 1, pageSize: 10 }
      await store.fetchProjects(params)

      expect(mockGetProjects).toHaveBeenCalledWith(params)
    })

    it('fetchProjects 应该设置 projects 数据', async () => {
      const store = useProjectStore()
      const projectsData = {
        items: [
          { id: 1, name: '项目1' },
          { id: 2, name: '项目2' }
        ]
      }
      mockGetProjects.mockResolvedValueOnce(projectsData)

      await store.fetchProjects()

      expect(store.projects).toEqual(projectsData.items)
    })

    it('fetchProjects 应该直接处理数组返回', async () => {
      const store = useProjectStore()
      const projectsArray = [
        { id: 1, name: '项目1' },
        { id: 2, name: '项目2' }
      ]
      mockGetProjects.mockResolvedValueOnce(projectsArray)

      await store.fetchProjects()

      expect(store.projects).toEqual(projectsArray)
    })

    it('fetchProjects 应该返回 API 数据', async () => {
      const store = useProjectStore()
      const projectsData = { items: [{ id: 1, name: '项目1' }] }
      mockGetProjects.mockResolvedValueOnce(projectsData)

      const result = await store.fetchProjects()

      expect(result).toEqual(projectsData)
    })

    it('fetchProjects 开始时应该设置 loading 为 true', async () => {
      const store = useProjectStore()
      mockGetProjects.mockImplementation(() => new Promise(resolve => {
        // 验证 loading 状态
        expect(store.loading).toBe(true)
        resolve({ items: [] })
      }))

      await store.fetchProjects()
    })

    it('fetchProjects 结束时应该设置 loading 为 false', async () => {
      const store = useProjectStore()
      mockGetProjects.mockResolvedValueOnce({ items: [] })

      await store.fetchProjects()

      expect(store.loading).toBe(false)
    })

    it('fetchProjects 失败时应该设置 loading 为 false', async () => {
      const store = useProjectStore()
      mockGetProjects.mockRejectedValueOnce(new Error('Network error'))

      try {
        await store.fetchProjects()
      } catch {
        // 忽略错误
      }

      expect(store.loading).toBe(false)
    })

    it('fetchProjects 空数据应该设置空数组', async () => {
      const store = useProjectStore()
      mockGetProjects.mockResolvedValueOnce({ items: [] })

      await store.fetchProjects()

      expect(store.projects).toEqual([])
    })
  })

  /**
   * 获取单个项目测试
   */
  describe('获取单个项目', () => {
    it('fetchProject 应该调用 API 传入项目 ID', async () => {
      const store = useProjectStore()
      const projectData = { id: 1, name: '项目1' }
      mockGetProject.mockResolvedValueOnce(projectData)

      await store.fetchProject(1)

      expect(mockGetProject).toHaveBeenCalledWith(1)
    })

    it('fetchProject 应该设置 currentProject', async () => {
      const store = useProjectStore()
      const projectData = { id: 1, name: '项目1', description: '描述' }
      mockGetProject.mockResolvedValueOnce(projectData)

      await store.fetchProject(1)

      expect(store.currentProject).toEqual(projectData)
    })

    it('fetchProject 应该返回项目数据', async () => {
      const store = useProjectStore()
      const projectData = { id: 1, name: '项目1' }
      mockGetProject.mockResolvedValueOnce(projectData)

      const result = await store.fetchProject(1)

      expect(result).toEqual(projectData)
    })

    it('fetchProject 开始时应该设置 loading 为 true', async () => {
      const store = useProjectStore()
      mockGetProject.mockImplementation(() => new Promise(resolve => {
        expect(store.loading).toBe(true)
        resolve({ id: 1, name: '项目1' })
      }))

      await store.fetchProject(1)
    })

    it('fetchProject 结束时应该设置 loading 为 false', async () => {
      const store = useProjectStore()
      mockGetProject.mockResolvedValueOnce({ id: 1, name: '项目1' })

      await store.fetchProject(1)

      expect(store.loading).toBe(false)
    })

    it('fetchProject 失败时应该设置 loading 为 false', async () => {
      const store = useProjectStore()
      mockGetProject.mockRejectedValueOnce(new Error('Not found'))

      try {
        await store.fetchProject(999)
      } catch {
        // 忽略错误
      }

      expect(store.loading).toBe(false)
    })
  })

  /**
   * 创建项目测试
   */
  describe('创建项目', () => {
    it('createProject 应该调用 API 传入项目数据', async () => {
      const store = useProjectStore()
      const projectData = { name: '新项目', description: '新描述' }
      const createdProject = { id: 1, ...projectData }
      mockCreateProject.mockResolvedValueOnce(createdProject)

      await store.createProject(projectData)

      expect(mockCreateProject).toHaveBeenCalledWith(projectData)
    })

    it('createProject 应该将新项目添加到 projects 数组开头', async () => {
      const store = useProjectStore()
      store.projects = [{ id: 1, name: '现有项目' }]

      const newProject = { id: 2, name: '新项目' }
      mockCreateProject.mockResolvedValueOnce(newProject)

      await store.createProject({ name: '新项目' })

      expect(store.projects[0]).toEqual(newProject)
      expect(store.projects.length).toBe(2)
    })

    it('createProject 应该返回创建的项目数据', async () => {
      const store = useProjectStore()
      const createdProject = { id: 1, name: '新项目' }
      mockCreateProject.mockResolvedValueOnce(createdProject)

      const result = await store.createProject({ name: '新项目' })

      expect(result).toEqual(createdProject)
    })

    it('createProject 应该在空数组中添加项目', async () => {
      const store = useProjectStore()
      const newProject = { id: 1, name: '新项目' }
      mockCreateProject.mockResolvedValueOnce(newProject)

      await store.createProject({ name: '新项目' })

      expect(store.projects).toEqual([newProject])
    })

    it('createProject 失败应该抛出错误', async () => {
      const store = useProjectStore()
      mockCreateProject.mockRejectedValueOnce(new Error('Validation failed'))

      await expect(store.createProject({ name: '' })).rejects.toThrow('Validation failed')
    })
  })

  /**
   * 删除项目测试
   */
  describe('删除项目', () => {
    it('deleteProject 应该调用 API 传入项目 ID', async () => {
      const store = useProjectStore()
      mockDeleteProject.mockResolvedValueOnce(undefined)

      await store.deleteProject(1)

      expect(mockDeleteProject).toHaveBeenCalledWith(1)
    })

    it('deleteProject 应该从 projects 数组中移除项目', async () => {
      const store = useProjectStore()
      store.projects = [
        { id: 1, name: '项目1' },
        { id: 2, name: '项目2' },
        { id: 3, name: '项目3' }
      ]
      mockDeleteProject.mockResolvedValueOnce(undefined)

      await store.deleteProject(2)

      expect(store.projects.length).toBe(2)
      expect(store.projects.find(p => p.id === 2)).toBeUndefined()
    })

    it('deleteProject 应该清除 currentProject 如果匹配', async () => {
      const store = useProjectStore()
      store.currentProject = { id: 1, name: '项目1' }
      mockDeleteProject.mockResolvedValueOnce(undefined)

      await store.deleteProject(1)

      expect(store.currentProject).toBeNull()
    })

    it('deleteProject 不应该清除 currentProject 如果不匹配', async () => {
      const store = useProjectStore()
      store.currentProject = { id: 2, name: '项目2' }
      mockDeleteProject.mockResolvedValueOnce(undefined)

      await store.deleteProject(1)

      expect(store.currentProject).toEqual({ id: 2, name: '项目2' })
    })

    it('deleteProject 应该处理不存在的项目 ID', async () => {
      const store = useProjectStore()
      store.projects = [
        { id: 1, name: '项目1' },
        { id: 2, name: '项目2' }
      ]
      mockDeleteProject.mockResolvedValueOnce(undefined)

      await store.deleteProject(999)

      expect(store.projects.length).toBe(2)
    })

    it('deleteProject 失败应该抛出错误', async () => {
      const store = useProjectStore()
      mockDeleteProject.mockRejectedValueOnce(new Error('Cannot delete'))

      await expect(store.deleteProject(1)).rejects.toThrow('Cannot delete')
    })
  })

  /**
   * 错误处理测试
   */
  describe('错误处理', () => {
    it('fetchProjects 应该抛出 API 错误', async () => {
      const store = useProjectStore()
      mockGetProjects.mockRejectedValueOnce(new Error('Server error'))

      await expect(store.fetchProjects()).rejects.toThrow('Server error')
    })

    it('fetchProject 应该抛出 API 错误', async () => {
      const store = useProjectStore()
      mockGetProject.mockRejectedValueOnce(new Error('Not found'))

      await expect(store.fetchProject(999)).rejects.toThrow('Not found')
    })

    it('createProject 应该抛出 API 错误', async () => {
      const store = useProjectStore()
      mockCreateProject.mockRejectedValueOnce(new Error('Validation failed'))

      await expect(store.createProject({})).rejects.toThrow('Validation failed')
    })

    it('错误后 loading 状态应该被重置', async () => {
      const store = useProjectStore()
      mockGetProjects.mockRejectedValueOnce(new Error('Error'))

      try {
        await store.fetchProjects()
      } catch {
        // 忽略错误
      }

      expect(store.loading).toBe(false)
    })

    it('错误后 projects 数据应该保持不变', async () => {
      const store = useProjectStore()
      const existingProjects = [{ id: 1, name: '项目1' }]
      store.projects = existingProjects

      mockGetProjects.mockRejectedValueOnce(new Error('Error'))

      try {
        await store.fetchProjects()
      } catch {
        // 忽略错误
      }

      expect(store.projects).toEqual(existingProjects)
    })
  })

  /**
   * 复杂场景测试
   */
  describe('复杂场景', () => {
    it('应该正确处理多个操作的序列', async () => {
      const store = useProjectStore()

      // 1. 获取项目列表
      mockGetProjects.mockResolvedValueOnce({
        items: [{ id: 1, name: '项目1' }]
      })
      await store.fetchProjects()
      expect(store.projects.length).toBe(1)

      // 2. 创建新项目
      mockCreateProject.mockResolvedValueOnce({ id: 2, name: '项目2' })
      await store.createProject({ name: '项目2' })
      expect(store.projects.length).toBe(2)

      // 3. 获取单个项目
      mockGetProject.mockResolvedValueOnce({ id: 1, name: '项目1', detail: '详情' })
      await store.fetchProject(1)
      expect(store.currentProject).toEqual({ id: 1, name: '项目1', detail: '详情' })

      // 4. 删除项目
      mockDeleteProject.mockResolvedValueOnce(undefined)
      await store.deleteProject(1)
      expect(store.projects.length).toBe(1)
      expect(store.currentProject).toBeNull()
    })

    it('应该正确处理并发请求', async () => {
      const store = useProjectStore()

      mockGetProjects.mockResolvedValueOnce({ items: [{ id: 1, name: '项目1' }] })
      mockGetProject.mockResolvedValueOnce({ id: 2, name: '项目2' })

      // 同时发起两个请求
      const promise1 = store.fetchProjects()
      const promise2 = store.fetchProject(2)

      await Promise.all([promise1, promise2])

      expect(store.projects).toEqual([{ id: 1, name: '项目1' }])
      expect(store.currentProject).toEqual({ id: 2, name: '项目2' })
    })
  })
})
