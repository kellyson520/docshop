import { beforeEach, describe, expect, it } from 'vitest'
import { resolveDocumentTitle, setDocumentTitle } from '../pageTitle'

describe('page title utilities', () => {
  beforeEach(() => {
    document.title = 'old title'
  })

  it('builds a readable document title from route meta title', () => {
    expect(resolveDocumentTitle({ meta: { title: '项目管理' }, matched: [] })).toBe('项目管理 - DocShop')
  })

  it('falls back to the deepest matched route title', () => {
    expect(resolveDocumentTitle({
      meta: {},
      matched: [
        { meta: { title: '后台' } },
        { meta: { title: '系统设置' } }
      ]
    })).toBe('系统设置 - DocShop')
  })

  it('uses the app name for empty or home titles', () => {
    expect(resolveDocumentTitle({ meta: {}, matched: [] })).toBe('DocShop')
    expect(resolveDocumentTitle({ meta: { title: '首页' }, matched: [] })).toBe('DocShop')
  })

  it('updates document.title safely', () => {
    const title = setDocumentTitle({ meta: { title: '访问排行榜' }, matched: [] })

    expect(title).toBe('访问排行榜 - DocShop')
    expect(document.title).toBe('访问排行榜 - DocShop')
  })
})
