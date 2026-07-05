import { test, expect } from '@playwright/test'

function base64Url(value) {
  return Buffer.from(JSON.stringify(value)).toString('base64url')
}

function fakeJwt() {
  const header = base64Url({ alg: 'HS256', typ: 'JWT' })
  const payload = base64Url({ sub: 'admin', role: 'admin', roles: ['admin'], exp: Math.floor(Date.now() / 1000) + 3600 })
  return `${header}.${payload}.signature`
}

const diffPayload = {
  type: 'docx_diff',
  status: 'completed',
  summary: '发现 7 处差异',
  text: [
    { change_type: 'insert', new_text: '新增无人机施肥策略' },
    { change_type: 'move', old_text: '移动段落', new_text: '移动段落', metadata: { from: 1, to: 3, description: '第 2 段移动到第 4 段之后' } }
  ],
  tables: [
    {
      table_index: 0,
      old_rows: [['作物', '旧值'], ['玉米', '12']],
      new_rows: [['作物', '新值'], ['玉米', '18']],
      cell_changes: [{ row: 1, col: 1, old_value: '12', new_value: '18', change_type: 'replace' }]
    }
  ],
  images: {
    added: [{ display_name: 'drone-map.png', data_uri: 'data:image/png;base64,iVBORw0KGgo=', short_hash: 'img123456789' }],
    deleted: [],
    replaced: [],
    resized: []
  },
  metadata: { elapsed_ms: 88, file_type: 'docx' },
  stats: { text_changes: 2, text_added: 1, text_moves: 1, tables_changed: 1, image_added: 1, total_changes: 4 }
}

test.describe('DOCX diff display regression', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((token) => {
      localStorage.setItem('access_token', token)
    }, fakeJwt())

    await page.route('**/api/v1/**', async (route) => {
      const url = new URL(route.request().url())

      if (url.pathname.endsWith('/api/v1/auth/me')) {
        await route.fulfill({ json: { code: 0, message: 'ok', data: { id: 'admin-1', username: 'admin', role: 'admin' } } })
        return
      }

      if (url.pathname.endsWith('/api/v1/files/file-1/versions')) {
        await route.fulfill({
          json: {
            code: 0,
            message: 'ok',
            data: {
              file_type: 'docx',
              filename: 'demo.docx',
              versions: [
                { id: 'v1', version: 1, created_at: '2026-06-01T00:00:00Z' },
                { id: 'v2', version: 2, created_at: '2026-06-02T00:00:00Z' }
              ]
            }
          }
        })
        return
      }

      if (url.pathname.endsWith('/api/v1/files/file-1/diffs')) {
        await route.fulfill({
          json: {
            code: 0,
            message: 'ok',
            data: {
              diffs: [{ diff_type: 'docx_diff', summary: diffPayload.summary, diff_data: diffPayload }]
            }
          }
        })
        return
      }

      if (url.pathname.endsWith('/api/v1/exams/upcoming') || url.pathname.endsWith('/api/v1/notices')) {
        await route.fulfill({ json: { code: 0, message: 'ok', data: [] } })
        return
      }

      await route.fallback()
    })
  })

  test('renders text/table/image sections and supports filter/search', async ({ page }) => {
    await page.goto('/admin/projects/project-1/diff/file-1')
    const insertedLine = page.locator('.line-content', { hasText: '新增无人机施肥策略' })

    await expect(page.getByText('7 处差异')).toBeVisible()
    await expect(page.getByText('状态 completed')).toBeVisible()
    await expect(insertedLine).toBeVisible()
    await expect(page.getByText('表格 #1')).toBeVisible()
    await expect(page.getByAltText('drone-map.png')).toBeVisible()

    await page.getByTestId('docx-filter-image').click()
    await expect(page.getByAltText('drone-map.png')).toBeVisible()
    await expect(insertedLine).toHaveCount(0)

    await page.getByTestId('docx-filter-text').click()
    await page.getByTestId('docx-diff-search').fill('无人机')
    await expect(page.locator('.search-hit').first()).toBeVisible()
    await expect(insertedLine).toBeVisible()
  })
})
