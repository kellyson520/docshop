import { shallowMount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import UserProfile from '../UserProfile.vue'

const mocks = vi.hoisted(() => ({
  authStore: {
    user: {
      username: 'admin',
      avatar: 'avatars/user-1/avatar.png',
      is_admin: true,
      created_at: '2026-06-29T08:00:00Z',
    },
  },
  updateUserSettings: vi.fn(),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => mocks.authStore,
}))

vi.mock('@/api/settings', () => ({
  updateUserSettings: mocks.updateUserSettings,
}))

const passthrough = (template = '<div><slot /></div>') => ({ template })

function mountUserProfile() {
  return shallowMount(UserProfile, {
    global: {
      renderStubDefaultSlot: true,
      stubs: {
        ElPageHeader: passthrough(),
        ElTabs: passthrough(),
        ElTabPane: passthrough(),
        ElRow: passthrough(),
        ElCol: passthrough(),
        ElCard: passthrough(),
        ElAvatar: passthrough('<span><slot /></span>'),
        ElIcon: passthrough('<i><slot /></i>'),
        ElTag: passthrough('<span><slot /></span>'),
        ElDivider: passthrough('<hr />'),
        ElButton: passthrough('<button><slot /></button>'),
        ElForm: passthrough('<form><slot /></form>'),
        ElFormItem: passthrough('<div><slot /></div>'),
        ElInput: passthrough('<input />'),
        ElTimeline: passthrough(),
        ElTimelineItem: passthrough(),
        ElEmpty: passthrough(),
        ElDialog: passthrough('<div><slot /><slot name="footer" /></div>'),
      },
    },
  })
}

function getExpose(wrapper, key) {
  return wrapper.vm[key] ?? wrapper.vm.$?.setupState?.[key]
}

describe('UserProfile', () => {
  it('loads and normalizes the current user avatar for profile display', () => {
    const wrapper = mountUserProfile()
    const userInfo = getExpose(wrapper, 'userInfo')

    expect(userInfo.username).toBe('admin')
    expect(userInfo.avatar).toBe('/api/v1/avatars/user-1/avatar.png')
  })
})
