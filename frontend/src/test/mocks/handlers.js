/**
 * MSW (Mock Service Worker) 请求处理器
 * 用于模拟后端 API 响应，实现前端测试的独立性
 */
import { http, HttpResponse } from 'msw'

// ==================== 模拟数据 ====================

// 模拟用户数据
const mockUsers = [
  {
    id: 1,
    username: 'admin',
    email: 'admin@example.com',
    role: 'admin',
    created_at: '2024-01-01T00:00:00Z'
  },
  {
    id: 2,
    username: 'user',
    email: 'user@example.com',
    role: 'user',
    created_at: '2024-01-02T00:00:00Z'
  }
]

// 模拟项目数据
const mockProjects = [
  {
    id: 1,
    name: '示例项目1',
    description: '这是一个示例项目描述',
    owner_id: 1,
    status: 'active',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-10T00:00:00Z'
  },
  {
    id: 2,
    name: '示例项目2',
    description: '另一个示例项目',
    owner_id: 2,
    status: 'archived',
    created_at: '2024-01-05T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z'
  }
]

// 模拟文件数据
const mockFiles = [
  {
    id: 1,
    name: 'document.pdf',
    original_name: '原始文档.pdf',
    path: '/uploads/document.pdf',
    size: 1024000,
    mime_type: 'application/pdf',
    project_id: 1,
    uploaded_by: 1,
    created_at: '2024-01-01T00:00:00Z'
  },
  {
    id: 2,
    name: 'image.png',
    original_name: '截图.png',
    path: '/uploads/image.png',
    size: 512000,
    mime_type: 'image/png',
    project_id: 1,
    uploaded_by: 1,
    created_at: '2024-01-02T00:00:00Z'
  }
]

// 模拟卡片数据
const mockCards = [
  {
    id: 1,
    title: '待办事项1',
    content: '这是第一个待办事项的内容',
    status: 'todo',
    priority: 'high',
    project_id: 1,
    assigned_to: 1,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-10T00:00:00Z'
  },
  {
    id: 2,
    title: '已完成事项',
    content: '这是已完成事项的内容',
    status: 'done',
    priority: 'medium',
    project_id: 1,
    assigned_to: 2,
    created_at: '2024-01-05T00:00:00Z',
    updated_at: '2024-01-12T00:00:00Z'
  }
]

// 模拟考试数据
const mockExams = [
  {
    id: 1,
    title: '期末考试',
    description: '2024年春季期末考试',
    duration: 120,
    total_score: 100,
    passing_score: 60,
    status: 'published',
    created_by: 1,
    created_at: '2024-01-01T00:00:00Z',
    start_time: '2024-06-01T09:00:00Z',
    end_time: '2024-06-01T11:00:00Z'
  },
  {
    id: 2,
    title: '模拟测试',
    description: '期中模拟测试',
    duration: 90,
    total_score: 100,
    passing_score: 60,
    status: 'draft',
    created_by: 1,
    created_at: '2024-01-10T00:00:00Z',
    start_time: null,
    end_time: null
  }
]

// ==================== Auth API 处理器 ====================

const authHandlers = [
  // 登录接口
  http.post('/api/auth/login', async ({ request }) => {
    const body = await request.json()
    const { username, password } = body

    if (username === 'admin' && password === 'password') {
      return HttpResponse.json({
        success: true,
        data: {
          user: mockUsers[0],
          token: 'mock-jwt-token-admin',
          refresh_token: 'mock-refresh-token-admin'
        }
      })
    }

    if (username === 'user' && password === 'password') {
      return HttpResponse.json({
        success: true,
        data: {
          user: mockUsers[1],
          token: 'mock-jwt-token-user',
          refresh_token: 'mock-refresh-token-user'
        }
      })
    }

    return HttpResponse.json(
      { success: false, message: '用户名或密码错误' },
      { status: 401 }
    )
  }),

  // 注册接口
  http.post('/api/auth/register', async ({ request }) => {
    const body = await request.json()
    const { username, email, password } = body

    // 检查用户名是否已存在
    const existingUser = mockUsers.find(u => u.username === username)
    if (existingUser) {
      return HttpResponse.json(
        { success: false, message: '用户名已存在' },
        { status: 400 }
      )
    }

    const newUser = {
      id: mockUsers.length + 1,
      username,
      email,
      role: 'user',
      created_at: new Date().toISOString()
    }

    return HttpResponse.json({
      success: true,
      data: { user: newUser },
      message: '注册成功'
    })
  }),

  // 登出接口
  http.post('/api/auth/logout', () => {
    return HttpResponse.json({
      success: true,
      message: '登出成功'
    })
  }),

  // 获取当前用户信息
  http.get('/api/auth/me', () => {
    return HttpResponse.json({
      success: true,
      data: { user: mockUsers[0] }
    })
  }),

  // 刷新 Token
  http.post('/api/auth/refresh', () => {
    return HttpResponse.json({
      success: true,
      data: {
        token: 'mock-new-jwt-token',
        refresh_token: 'mock-new-refresh-token'
      }
    })
  })
]

// ==================== Project API 处理器 ====================

const projectHandlers = [
  // 获取项目列表
  http.get('/api/projects', ({ request }) => {
    const url = new URL(request.url)
    const page = parseInt(url.searchParams.get('page') || '1')
    const pageSize = parseInt(url.searchParams.get('page_size') || '10')
    const status = url.searchParams.get('status')

    let filteredProjects = [...mockProjects]
    if (status) {
      filteredProjects = filteredProjects.filter(p => p.status === status)
    }

    const total = filteredProjects.length
    const start = (page - 1) * pageSize
    const end = start + pageSize
    const items = filteredProjects.slice(start, end)

    return HttpResponse.json({
      success: true,
      data: {
        items,
        total,
        page,
        page_size: pageSize,
        total_pages: Math.ceil(total / pageSize)
      }
    })
  }),

  // 获取单个项目
  http.get('/api/projects/:id', ({ params }) => {
    const project = mockProjects.find(p => p.id === parseInt(params.id))

    if (!project) {
      return HttpResponse.json(
        { success: false, message: '项目不存在' },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      success: true,
      data: { project }
    })
  }),

  // 创建项目
  http.post('/api/projects', async ({ request }) => {
    const body = await request.json()
    const newProject = {
      id: mockProjects.length + 1,
      ...body,
      owner_id: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }

    return HttpResponse.json({
      success: true,
      data: { project: newProject },
      message: '项目创建成功'
    })
  }),

  // 更新项目
  http.put('/api/projects/:id', async ({ params, request }) => {
    const body = await request.json()
    const project = mockProjects.find(p => p.id === parseInt(params.id))

    if (!project) {
      return HttpResponse.json(
        { success: false, message: '项目不存在' },
        { status: 404 }
      )
    }

    const updatedProject = {
      ...project,
      ...body,
      updated_at: new Date().toISOString()
    }

    return HttpResponse.json({
      success: true,
      data: { project: updatedProject },
      message: '项目更新成功'
    })
  }),

  // 删除项目
  http.delete('/api/projects/:id', ({ params }) => {
    const project = mockProjects.find(p => p.id === parseInt(params.id))

    if (!project) {
      return HttpResponse.json(
        { success: false, message: '项目不存在' },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      success: true,
      message: '项目删除成功'
    })
  })
]

// ==================== File API 处理器 ====================

const fileHandlers = [
  // 获取文件列表
  http.get('/api/files', ({ request }) => {
    const url = new URL(request.url)
    const projectId = url.searchParams.get('project_id')

    let filteredFiles = [...mockFiles]
    if (projectId) {
      filteredFiles = filteredFiles.filter(f => f.project_id === parseInt(projectId))
    }

    return HttpResponse.json({
      success: true,
      data: { items: filteredFiles, total: filteredFiles.length }
    })
  }),

  // 获取单个文件
  http.get('/api/files/:id', ({ params }) => {
    const file = mockFiles.find(f => f.id === parseInt(params.id))

    if (!file) {
      return HttpResponse.json(
        { success: false, message: '文件不存在' },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      success: true,
      data: { file }
    })
  }),

  // 上传文件
  http.post('/api/files/upload', async () => {
    return HttpResponse.json({
      success: true,
      data: { file: mockFiles[0] },
      message: '文件上传成功'
    })
  }),

  // 删除文件
  http.delete('/api/files/:id', ({ params }) => {
    const file = mockFiles.find(f => f.id === parseInt(params.id))

    if (!file) {
      return HttpResponse.json(
        { success: false, message: '文件不存在' },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      success: true,
      message: '文件删除成功'
    })
  }),

  // 下载文件
  http.get('/api/files/:id/download', ({ params }) => {
    const file = mockFiles.find(f => f.id === parseInt(params.id))

    if (!file) {
      return HttpResponse.json(
        { success: false, message: '文件不存在' },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      success: true,
      data: { download_url: `/downloads/${file.name}` }
    })
  })
]

// ==================== Card API 处理器 ====================

const cardHandlers = [
  // 获取卡片列表
  http.get('/api/cards', ({ request }) => {
    const url = new URL(request.url)
    const projectId = url.searchParams.get('project_id')
    const status = url.searchParams.get('status')

    let filteredCards = [...mockCards]
    if (projectId) {
      filteredCards = filteredCards.filter(c => c.project_id === parseInt(projectId))
    }
    if (status) {
      filteredCards = filteredCards.filter(c => c.status === status)
    }

    return HttpResponse.json({
      success: true,
      data: { items: filteredCards, total: filteredCards.length }
    })
  }),

  // 获取单个卡片
  http.get('/api/cards/:id', ({ params }) => {
    const card = mockCards.find(c => c.id === parseInt(params.id))

    if (!card) {
      return HttpResponse.json(
        { success: false, message: '卡片不存在' },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      success: true,
      data: { card }
    })
  }),

  // 创建卡片
  http.post('/api/cards', async ({ request }) => {
    const body = await request.json()
    const newCard = {
      id: mockCards.length + 1,
      ...body,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }

    return HttpResponse.json({
      success: true,
      data: { card: newCard },
      message: '卡片创建成功'
    })
  }),

  // 更新卡片
  http.put('/api/cards/:id', async ({ params, request }) => {
    const body = await request.json()
    const card = mockCards.find(c => c.id === parseInt(params.id))

    if (!card) {
      return HttpResponse.json(
        { success: false, message: '卡片不存在' },
        { status: 404 }
      )
    }

    const updatedCard = {
      ...card,
      ...body,
      updated_at: new Date().toISOString()
    }

    return HttpResponse.json({
      success: true,
      data: { card: updatedCard },
      message: '卡片更新成功'
    })
  }),

  // 删除卡片
  http.delete('/api/cards/:id', ({ params }) => {
    const card = mockCards.find(c => c.id === parseInt(params.id))

    if (!card) {
      return HttpResponse.json(
        { success: false, message: '卡片不存在' },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      success: true,
      message: '卡片删除成功'
    })
  }),

  // 更新卡片状态
  http.patch('/api/cards/:id/status', async ({ params, request }) => {
    const body = await request.json()
    const card = mockCards.find(c => c.id === parseInt(params.id))

    if (!card) {
      return HttpResponse.json(
        { success: false, message: '卡片不存在' },
        { status: 404 }
      )
    }

    const updatedCard = {
      ...card,
      status: body.status,
      updated_at: new Date().toISOString()
    }

    return HttpResponse.json({
      success: true,
      data: { card: updatedCard },
      message: '状态更新成功'
    })
  })
]

// ==================== Exam API 处理器 ====================

const examHandlers = [
  // 获取考试列表
  http.get('/api/exams', ({ request }) => {
    const url = new URL(request.url)
    const status = url.searchParams.get('status')

    let filteredExams = [...mockExams]
    if (status) {
      filteredExams = filteredExams.filter(e => e.status === status)
    }

    return HttpResponse.json({
      success: true,
      data: { items: filteredExams, total: filteredExams.length }
    })
  }),

  // 获取单个考试
  http.get('/api/exams/:id', ({ params }) => {
    const exam = mockExams.find(e => e.id === parseInt(params.id))

    if (!exam) {
      return HttpResponse.json(
        { success: false, message: '考试不存在' },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      success: true,
      data: { exam }
    })
  }),

  // 创建考试
  http.post('/api/exams', async ({ request }) => {
    const body = await request.json()
    const newExam = {
      id: mockExams.length + 1,
      ...body,
      created_by: 1,
      created_at: new Date().toISOString()
    }

    return HttpResponse.json({
      success: true,
      data: { exam: newExam },
      message: '考试创建成功'
    })
  }),

  // 更新考试
  http.put('/api/exams/:id', async ({ params, request }) => {
    const body = await request.json()
    const exam = mockExams.find(e => e.id === parseInt(params.id))

    if (!exam) {
      return HttpResponse.json(
        { success: false, message: '考试不存在' },
        { status: 404 }
      )
    }

    const updatedExam = { ...exam, ...body }

    return HttpResponse.json({
      success: true,
      data: { exam: updatedExam },
      message: '考试更新成功'
    })
  }),

  // 删除考试
  http.delete('/api/exams/:id', ({ params }) => {
    const exam = mockExams.find(e => e.id === parseInt(params.id))

    if (!exam) {
      return HttpResponse.json(
        { success: false, message: '考试不存在' },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      success: true,
      message: '考试删除成功'
    })
  }),

  // 发布考试
  http.post('/api/exams/:id/publish', ({ params }) => {
    const exam = mockExams.find(e => e.id === parseInt(params.id))

    if (!exam) {
      return HttpResponse.json(
        { success: false, message: '考试不存在' },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      success: true,
      data: { exam: { ...exam, status: 'published' } },
      message: '考试发布成功'
    })
  }),

  // 开始考试
  http.post('/api/exams/:id/start', ({ params }) => {
    const exam = mockExams.find(e => e.id === parseInt(params.id))

    if (!exam) {
      return HttpResponse.json(
        { success: false, message: '考试不存在' },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      success: true,
      data: {
        session_id: `session-${Date.now()}`,
        exam: exam,
        start_time: new Date().toISOString(),
        end_time: new Date(Date.now() + exam.duration * 60000).toISOString()
      }
    })
  }),

  // 提交考试
  http.post('/api/exams/:id/submit', async ({ params, request }) => {
    const body = await request.json()
    const exam = mockExams.find(e => e.id === parseInt(params.id))

    if (!exam) {
      return HttpResponse.json(
        { success: false, message: '考试不存在' },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      success: true,
      data: {
        score: 85,
        total_score: exam.total_score,
        passed: true,
        submitted_at: new Date().toISOString()
      },
      message: '考试提交成功'
    })
  })
]

// ==================== 导出所有处理器 ====================

export const handlers = [
  ...authHandlers,
  ...projectHandlers,
  ...fileHandlers,
  ...cardHandlers,
  ...examHandlers
]
