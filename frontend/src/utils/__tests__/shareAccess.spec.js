import { describe, expect, it } from 'vitest'

import {
  buildShareAccessSummaryItems,
  formatShareAccessSummary,
  getSharePolicyModeMeta,
  normalizeSharePolicyMode,
} from '../shareAccess'

describe('shareAccess helpers', () => {
  it('normalizes unknown policy mode and exposes independent-share metadata', () => {
    expect(normalizeSharePolicyMode('unexpected')).toBe('override_with_token_policy')
    expect(getSharePolicyModeMeta('override_with_token_policy')).toMatchObject({
      value: 'override_with_token_policy',
      label: '分享权限独立生效',
      summary: '分享权限独立生效',
    })
  })

  it('builds aligned summary items for share-token access control', () => {
    expect(buildShareAccessSummaryItems({
      require_login: true,
      password_hint: '部门简称',
      allow_download: false,
      allow_preview: false,
      allow_diff: true,
      allow_versions: false,
      policy_mode: 'override_with_token_policy',
    })).toEqual([
      { key: 'require_login', text: '需要登录' },
      { key: 'password_hint', text: '密码提示：部门简称' },
      { key: 'allow_download', text: '禁止下载' },
      { key: 'allow_preview', text: '禁用预览' },
      { key: 'allow_diff', text: '允许 Diff' },
      { key: 'allow_versions', text: '禁用版本历史' },
      { key: 'policy_mode', text: '分享权限独立生效' },
    ])
  })

  it('omits blank password hints and keeps permissive defaults aligned', () => {
    expect(buildShareAccessSummaryItems({
      require_login: false,
      password_hint: '   ',
    })).toEqual([
      { key: 'require_login', text: '免登录访问' },
      { key: 'allow_download', text: '允许下载' },
      { key: 'allow_preview', text: '允许预览' },
      { key: 'allow_diff', text: '允许 Diff' },
      { key: 'allow_versions', text: '允许版本历史' },
      { key: 'policy_mode', text: '分享权限独立生效' },
    ])
  })

  it('formats the summary items into reusable display text', () => {
    expect(formatShareAccessSummary({
      require_login: true,
      allow_download: true,
      allow_preview: true,
      allow_diff: false,
      allow_versions: true,
      policy_mode: 'inherit_resource_policy',
    })).toBe('需要登录 · 允许下载 · 允许预览 · 禁用 Diff · 允许版本历史 · 分享权限独立生效')
  })
})
