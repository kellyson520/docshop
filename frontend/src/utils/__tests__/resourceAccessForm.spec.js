import { describe, it, expect } from 'vitest'

import {
  FILE_PUBLIC_ACCESS_VISIBILITY_OPTIONS,
  PROJECT_PUBLIC_ACCESS_VISIBILITY_OPTIONS,
  buildResourceAccessFormState,
  buildResourceAccessMutationPayload,
} from '@/utils/resourceAccessForm'

describe('resourceAccessForm', () => {
  it('normalizes merged public-browse access form state', () => {
    const state = buildResourceAccessFormState({
      scope: 'file',
      defaultVisibility: 'inherit',
      policy: {
        visibility: 'groups_required',
        allow_preview: true,
        allow_download: false,
        allow_diff: false,
        allow_versions: true,
        password_hint: 'team code',
        has_password: true,
        group_codes: ['legal', 'legal', 'finance'],
      },
    })

    expect(FILE_PUBLIC_ACCESS_VISIBILITY_OPTIONS.map((item) => item.value)).toEqual([
      'inherit',
      'public',
      'password_required',
      'groups_required',
      'private',
    ])
    expect(PROJECT_PUBLIC_ACCESS_VISIBILITY_OPTIONS.map((item) => item.value)).toEqual([
      'public',
      'password_required',
      'groups_required',
      'private',
    ])
    expect(state).toMatchObject({
      visibility: 'groups_required',
      allow_preview: true,
      allow_download: false,
      allow_diff: false,
      allow_versions: true,
      password: '',
      clear_password: false,
      password_hint: 'team code',
      has_password: true,
      group_codes: ['legal', 'finance'],
    })
  })

  it('builds merged mutation payload with password and explicit clear flag', () => {
    expect(
      buildResourceAccessMutationPayload({
        visibility: 'password_required',
        allow_preview: false,
        allow_download: false,
        allow_diff: true,
        allow_versions: false,
        password: 'OpenSesame!1',
        clear_password: false,
        password_hint: 'project code',
        group_codes: ['legal'],
      }, { scope: 'project' }),
    ).toEqual({
      visibility: 'password_required',
      allow_preview: false,
      allow_download: false,
      allow_diff: true,
      allow_versions: false,
      password: 'OpenSesame!1',
      password_hint: 'project code',
      group_codes: ['legal'],
    })

    expect(
      buildResourceAccessMutationPayload({
        visibility: 'public',
        allow_preview: true,
        allow_download: true,
        allow_diff: true,
        allow_versions: true,
        password: '',
        clear_password: true,
        password_hint: '',
        group_codes: [],
      }, { scope: 'file' }),
    ).toEqual({
      visibility: 'public',
      allow_preview: true,
      allow_download: true,
      allow_diff: true,
      allow_versions: true,
      clear_password: true,
      password_hint: '',
      group_codes: [],
    })
  })
})
