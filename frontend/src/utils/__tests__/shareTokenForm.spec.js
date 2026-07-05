import { describe, expect, it } from 'vitest'

import {
  buildShareTokenFormState,
  buildShareTokenMutationPayload,
  normalizeShareTokenDateTimeInput,
} from '../shareTokenForm'

describe('shareTokenForm helpers', () => {
  it('builds a new share form with secure independent-share defaults', () => {
    const form = buildShareTokenFormState({
      defaults: {
        name: '分享文件：制度说明',
        resource_type: 'file',
        resource_id: 'file-1',
        policy_mode: 'override_with_token_policy',
      },
    })

    expect(form).toMatchObject({
      name: '分享文件：制度说明',
      resource_type: 'file',
      resource_id: 'file-1',
      max_views: 0,
      max_downloads: 0,
      allow_download: true,
      require_login: false,
      password: '',
      clear_password: false,
      password_hint: '',
      allow_preview: true,
      allow_diff: true,
      allow_versions: true,
      policy_mode: 'override_with_token_policy',
      expires_at: '',
    })
  })

  it('prefills an existing token without leaking the current password', () => {
    const form = buildShareTokenFormState({
      token: {
        name: '当前分享',
        resource_type: 'project',
        resource_id: 'project-1',
        max_views: 6,
        max_downloads: 3,
        allow_download: false,
        require_login: true,
        password_hint: '部门简称',
        allow_preview: false,
        allow_diff: true,
        allow_versions: false,
        policy_mode: 'override_with_token_policy',
        expires_at: '2026-07-08T10:20:30Z',
      },
      defaults: {
        name: '分享项目：项目一',
        resource_type: 'project',
        resource_id: 'project-1',
      },
    })

    expect(form).toMatchObject({
      name: '当前分享',
      resource_type: 'project',
      resource_id: 'project-1',
      max_views: 6,
      max_downloads: 3,
      allow_download: false,
      require_login: true,
      password: '',
      clear_password: false,
      password_hint: '部门简称',
      allow_preview: false,
      allow_diff: true,
      allow_versions: false,
      policy_mode: 'override_with_token_policy',
      expires_at: '2026-07-08T10:20:30',
    })
  })

  it('normalizes legacy inherit mode to the canonical independent mode', () => {
    const form = buildShareTokenFormState({
      token: {
        name: 'legacy share',
        resource_type: 'file',
        resource_id: 'file-legacy',
        policy_mode: 'inherit_resource_policy',
      },
    })

    expect(form.policy_mode).toBe('override_with_token_policy')
  })

  it('builds create-mode payloads and keeps blank password as explicit empty string', () => {
    const payload = buildShareTokenMutationPayload({
      name: '创建分享',
      resource_type: 'file',
      resource_id: 'file-1',
      max_views: 0,
      max_downloads: 0,
      allow_download: false,
      require_login: true,
      password: '',
      clear_password: false,
      password_hint: '',
      allow_preview: false,
      allow_diff: false,
      allow_versions: true,
      policy_mode: 'inherit_resource_policy',
      expires_at: '2026-07-09T08:09:10',
    })

    expect(payload).toEqual({
      name: '创建分享',
      resource_type: 'file',
      resource_id: 'file-1',
      max_views: 0,
      max_downloads: 0,
      allow_download: false,
      require_login: true,
      password: '',
      password_hint: '',
      allow_preview: false,
      allow_diff: false,
      allow_versions: true,
      policy_mode: 'override_with_token_policy',
      expires_at: '2026-07-09T08:09:10Z',
    })
  })

  it('builds edit-mode payloads with safe password semantics and canonical independent mode', () => {
    const baseForm = {
      name: '编辑分享',
      max_views: 12,
      max_downloads: 6,
      allow_download: true,
      require_login: false,
      password: '',
      clear_password: false,
      password_hint: '新提示',
      allow_preview: true,
      allow_diff: false,
      allow_versions: true,
      policy_mode: 'inherit_resource_policy',
      expires_at: '2026-07-10T08:09:10',
    }

    expect(buildShareTokenMutationPayload(baseForm, { preservePasswordWhenBlank: true })).toEqual({
      name: '编辑分享',
      max_views: 12,
      max_downloads: 6,
      allow_download: true,
      require_login: false,
      password_hint: '新提示',
      allow_preview: true,
      allow_diff: false,
      allow_versions: true,
      policy_mode: 'override_with_token_policy',
      expires_at: '2026-07-10T08:09:10Z',
    })

    expect(buildShareTokenMutationPayload(
      { ...baseForm, clear_password: true },
      { preservePasswordWhenBlank: true },
    )).toEqual({
      name: '编辑分享',
      max_views: 12,
      max_downloads: 6,
      allow_download: true,
      require_login: false,
      password: '',
      password_hint: '新提示',
      allow_preview: true,
      allow_diff: false,
      allow_versions: true,
      policy_mode: 'override_with_token_policy',
      expires_at: '2026-07-10T08:09:10Z',
    })

    expect(buildShareTokenMutationPayload(
      { ...baseForm, password: 'NewPass#2026' },
      { preservePasswordWhenBlank: true },
    )).toEqual({
      name: '编辑分享',
      max_views: 12,
      max_downloads: 6,
      allow_download: true,
      require_login: false,
      password: 'NewPass#2026',
      password_hint: '新提示',
      allow_preview: true,
      allow_diff: false,
      allow_versions: true,
      policy_mode: 'override_with_token_policy',
      expires_at: '2026-07-10T08:09:10Z',
    })
  })

  it('normalizes datetime input for dialog form controls', () => {
    expect(normalizeShareTokenDateTimeInput('2026-07-08T10:20:30Z')).toBe('2026-07-08T10:20:30')
    expect(normalizeShareTokenDateTimeInput('')).toBe('')
    expect(normalizeShareTokenDateTimeInput(null)).toBe('')
  })
})
