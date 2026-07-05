/**
 * MSW (Mock Service Worker) 请求处理器
 * 供前端单测中的全局 mock server 使用。
 */
import { http, HttpResponse } from 'msw'

const mockUsers = [
  {
    id: 1,
    username: 'admin',
    email: 'admin@example.com',
    role: 'admin',
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 2,
    username: 'user',
    email: 'user@example.com',
    role: 'user',
    created_at: '2024-01-02T00:00:00Z',
  },
]

const mockProjects = [
  {
    id: 1,
    name: '示例项目 1',
    description: '这是一个示例项目',
    owner_id: 1,
    status: 'active',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-10T00:00:00Z',
  },
  {
    id: 2,
    name: '示例项目 2',
    description: '这是另一个示例项目',
    owner_id: 2,
    status: 'archived',
    created_at: '2024-01-05T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
  },
]

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
    created_at: '2024-01-01T00:00:00Z',
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
    created_at: '2024-01-02T00:00:00Z',
  },
]

const mockCards = [
  {
    id: 1,
    title: '待办事项 1',
    content: '这是第一个待办事项',
    status: 'todo',
    priority: 'high',
    project_id: 1,
    assigned_to: 1,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-10T00:00:00Z',
  },
  {
    id: 2,
    title: '已完成事项',
    content: '这是已完成事项',
    status: 'done',
    priority: 'medium',
    project_id: 1,
    assigned_to: 2,
    created_at: '2024-01-05T00:00:00Z',
    updated_at: '2024-01-12T00:00:00Z',
  },
]

const mockExams = [
  {
    id: 1,
    title: '期末考试',
    description: '2024 春季期末考试',
    duration: 120,
    total_score: 100,
    passing_score: 60,
    status: 'published',
    created_by: 1,
    created_at: '2024-01-01T00:00:00Z',
    start_time: '2024-06-01T09:00:00Z',
    end_time: '2024-06-01T11:00:00Z',
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
    end_time: null,
  },
]

function ok(body, init) {
  return HttpResponse.json(body, init)
}

function fail(message, status = 400) {
  return HttpResponse.json(
    {
      success: false,
      message,
    },
    { status },
  )
}

function parseId(value) {
  return Number.parseInt(String(value), 10)
}

function apiPatterns(path) {
  return [`*/api${path}`, `*/api/v1${path}`]
}

function register(method, path, resolver) {
  return apiPatterns(path).map((pattern) => http[method](pattern, resolver))
}

const authHandlers = [
  ...register('post', '/auth/login', async ({ request }) => {
    const { username, password } = await request.json()

    if (username === 'admin' && password === 'password') {
      return ok({
        success: true,
        data: {
          user: mockUsers[0],
          token: 'mock-jwt-token-admin',
          refresh_token: 'mock-refresh-token-admin',
        },
      })
    }

    if (username === 'user' && password === 'password') {
      return ok({
        success: true,
        data: {
          user: mockUsers[1],
          token: 'mock-jwt-token-user',
          refresh_token: 'mock-refresh-token-user',
        },
      })
    }

    return fail('用户名或密码错误', 401)
  }),

  ...register('post', '/auth/register', async ({ request }) => {
    const { username, email } = await request.json()
    const existingUser = mockUsers.find((user) => user.username === username)

    if (existingUser) {
      return fail('用户名已存在', 400)
    }

    return ok({
      success: true,
      data: {
        user: {
          id: mockUsers.length + 1,
          username,
          email,
          role: 'user',
          created_at: new Date().toISOString(),
        },
      },
      message: '注册成功',
    })
  }),

  ...register('post', '/auth/logout', () => ok({ success: true, message: '退出成功' })),

  ...register('get', '/auth/me', () =>
    ok({
      success: true,
      data: {
        user: mockUsers[0],
      },
    })),

  ...register('post', '/auth/refresh', () =>
    ok({
      success: true,
      data: {
        token: 'mock-new-jwt-token',
        refresh_token: 'mock-new-refresh-token',
      },
    })),
]

const projectHandlers = [
  ...register('get', '/projects', ({ request }) => {
    const url = new URL(request.url)
    const page = Number.parseInt(url.searchParams.get('page') || '1', 10)
    const pageSize = Number.parseInt(url.searchParams.get('page_size') || '10', 10)
    const status = url.searchParams.get('status')

    let items = [...mockProjects]
    if (status) {
      items = items.filter((project) => project.status === status)
    }

    const total = items.length
    const start = (page - 1) * pageSize
    const pagedItems = items.slice(start, start + pageSize)

    return ok({
      success: true,
      data: {
        items: pagedItems,
        total,
        page,
        page_size: pageSize,
        total_pages: Math.ceil(total / pageSize) || 1,
      },
    })
  }),

  ...register('post', '/projects', async ({ request }) => {
    const body = await request.json()
    return ok({
      success: true,
      data: {
        project: {
          id: mockProjects.length + 1,
          ...body,
          owner_id: 1,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      },
      message: '项目创建成功',
    })
  }),

  ...register('get', '/projects/:id', ({ params }) => {
    const project = mockProjects.find((item) => item.id === parseId(params.id))
    if (!project) return fail('项目不存在', 404)
    return ok({
      success: true,
      data: { project },
    })
  }),

  ...register('put', '/projects/:id', async ({ params, request }) => {
    const body = await request.json()
    const project = mockProjects.find((item) => item.id === parseId(params.id))
    if (!project) return fail('项目不存在', 404)
    return ok({
      success: true,
      data: {
        project: {
          ...project,
          ...body,
          updated_at: new Date().toISOString(),
        },
      },
      message: '项目更新成功',
    })
  }),

  ...register('delete', '/projects/:id', ({ params }) => {
    const project = mockProjects.find((item) => item.id === parseId(params.id))
    if (!project) return fail('项目不存在', 404)
    return ok({
      success: true,
      message: '项目删除成功',
    })
  }),
]

const fileHandlers = [
  ...register('post', '/files/upload', async () =>
    ok({
      success: true,
      data: { file: mockFiles[0] },
      message: '文件上传成功',
    })),

  ...register('get', '/files/:id/download', ({ params }) => {
    const file = mockFiles.find((item) => item.id === parseId(params.id))
    if (!file) return fail('文件不存在', 404)
    return ok({
      success: true,
      data: { download_url: `/downloads/${file.name}` },
    })
  }),

  ...register('get', '/files', ({ request }) => {
    const url = new URL(request.url)
    const projectId = url.searchParams.get('project_id')
    let items = [...mockFiles]
    if (projectId) {
      items = items.filter((file) => file.project_id === Number.parseInt(projectId, 10))
    }

    return ok({
      success: true,
      data: {
        items,
        total: items.length,
      },
    })
  }),

  ...register('get', '/files/:id', ({ params }) => {
    const file = mockFiles.find((item) => item.id === parseId(params.id))
    if (!file) return fail('文件不存在', 404)
    return ok({
      success: true,
      data: { file },
    })
  }),

  ...register('delete', '/files/:id', ({ params }) => {
    const file = mockFiles.find((item) => item.id === parseId(params.id))
    if (!file) return fail('文件不存在', 404)
    return ok({
      success: true,
      message: '文件删除成功',
    })
  }),
]

const cardHandlers = [
  ...register('patch', '/cards/:id/status', async ({ params, request }) => {
    const { status } = await request.json()
    const card = mockCards.find((item) => item.id === parseId(params.id))
    if (!card) return fail('卡片不存在', 404)
    return ok({
      success: true,
      data: {
        card: {
          ...card,
          status,
          updated_at: new Date().toISOString(),
        },
      },
      message: '状态更新成功',
    })
  }),

  ...register('get', '/cards', ({ request }) => {
    const url = new URL(request.url)
    const projectId = url.searchParams.get('project_id')
    const status = url.searchParams.get('status')
    let items = [...mockCards]

    if (projectId) {
      items = items.filter((card) => card.project_id === Number.parseInt(projectId, 10))
    }
    if (status) {
      items = items.filter((card) => card.status === status)
    }

    return ok({
      success: true,
      data: {
        items,
        total: items.length,
      },
    })
  }),

  ...register('post', '/cards', async ({ request }) => {
    const body = await request.json()
    return ok({
      success: true,
      data: {
        card: {
          id: mockCards.length + 1,
          ...body,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      },
      message: '卡片创建成功',
    })
  }),

  ...register('get', '/cards/:id', ({ params }) => {
    const card = mockCards.find((item) => item.id === parseId(params.id))
    if (!card) return fail('卡片不存在', 404)
    return ok({
      success: true,
      data: { card },
    })
  }),

  ...register('put', '/cards/:id', async ({ params, request }) => {
    const body = await request.json()
    const card = mockCards.find((item) => item.id === parseId(params.id))
    if (!card) return fail('卡片不存在', 404)
    return ok({
      success: true,
      data: {
        card: {
          ...card,
          ...body,
          updated_at: new Date().toISOString(),
        },
      },
      message: '卡片更新成功',
    })
  }),

  ...register('delete', '/cards/:id', ({ params }) => {
    const card = mockCards.find((item) => item.id === parseId(params.id))
    if (!card) return fail('卡片不存在', 404)
    return ok({
      success: true,
      message: '卡片删除成功',
    })
  }),
]

const examHandlers = [
  ...register('post', '/exams/:id/publish', ({ params }) => {
    const exam = mockExams.find((item) => item.id === parseId(params.id))
    if (!exam) return fail('考试不存在', 404)
    return ok({
      success: true,
      data: {
        exam: {
          ...exam,
          status: 'published',
        },
      },
      message: '考试发布成功',
    })
  }),

  ...register('post', '/exams/:id/start', ({ params }) => {
    const exam = mockExams.find((item) => item.id === parseId(params.id))
    if (!exam) return fail('考试不存在', 404)
    return ok({
      success: true,
      data: {
        session_id: `session-${Date.now()}`,
        exam,
        start_time: new Date().toISOString(),
        end_time: new Date(Date.now() + exam.duration * 60 * 1000).toISOString(),
      },
    })
  }),

  ...register('post', '/exams/:id/submit', async ({ params }) => {
    const exam = mockExams.find((item) => item.id === parseId(params.id))
    if (!exam) return fail('考试不存在', 404)
    return ok({
      success: true,
      data: {
        score: 85,
        total_score: exam.total_score,
        passed: true,
        submitted_at: new Date().toISOString(),
      },
      message: '考试提交成功',
    })
  }),

  ...register('get', '/exams', ({ request }) => {
    const url = new URL(request.url)
    const status = url.searchParams.get('status')
    let items = [...mockExams]
    if (status) {
      items = items.filter((exam) => exam.status === status)
    }

    return ok({
      success: true,
      data: {
        items,
        total: items.length,
      },
    })
  }),

  ...register('post', '/exams', async ({ request }) => {
    const body = await request.json()
    return ok({
      success: true,
      data: {
        exam: {
          id: mockExams.length + 1,
          ...body,
          created_by: 1,
          created_at: new Date().toISOString(),
        },
      },
      message: '考试创建成功',
    })
  }),

  ...register('get', '/exams/:id', ({ params }) => {
    const exam = mockExams.find((item) => item.id === parseId(params.id))
    if (!exam) return fail('考试不存在', 404)
    return ok({
      success: true,
      data: { exam },
    })
  }),

  ...register('put', '/exams/:id', async ({ params, request }) => {
    const body = await request.json()
    const exam = mockExams.find((item) => item.id === parseId(params.id))
    if (!exam) return fail('考试不存在', 404)
    return ok({
      success: true,
      data: {
        exam: {
          ...exam,
          ...body,
        },
      },
      message: '考试更新成功',
    })
  }),

  ...register('delete', '/exams/:id', ({ params }) => {
    const exam = mockExams.find((item) => item.id === parseId(params.id))
    if (!exam) return fail('考试不存在', 404)
    return ok({
      success: true,
      message: '考试删除成功',
    })
  }),
]

export const handlers = [
  ...authHandlers,
  ...projectHandlers,
  ...fileHandlers,
  ...cardHandlers,
  ...examHandlers,
]
