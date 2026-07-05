import { describe, it, expect, vi, beforeEach } from 'vitest'
import { shallowMount, flushPromises } from '@vue/test-utils'
import MultiVersionCompare from '../compare/MultiVersionCompare.vue'

const mocks = vi.hoisted(() => ({
  getVersions: vi.fn(),
  compareVersions: vi.fn(),
  messageError: vi.fn(),
  messageWarning: vi.fn(),
}))

vi.mock('@/api/card', () => ({
  cardApi: {
    getVersions: mocks.getVersions,
    compareVersions: mocks.compareVersions,
  },
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    error: mocks.messageError,
    warning: mocks.messageWarning,
  },
}))

vi.mock('@element-plus/icons-vue', () => ({
  Sort: { template: '<i />' },
}))

const mountOptions = {
  props: {
    cardId: 'card-1',
    versionIds: ['ver-1', 'ver-2'],
    fileType: 'docx',
  },
  global: {
    renderStubDefaultSlot: true,
    stubs: {
      ElSelect: { template: '<div><slot /></div>' },
      ElOption: { template: '<div />' },
      ElButton: { template: '<button><slot /></button>' },
      ElSkeleton: { template: '<div />' },
      ElTag: { template: '<span><slot /></span>' },
      ElEmpty: { template: '<div><slot /></div>' },
      ElCard: { template: '<div><slot name="header" /><slot /></div>' },
      ElIcon: { template: '<i><slot /></i>' },
    },
  },
}

function getSetupValue(wrapper, key) {
  return wrapper.vm[key] ?? wrapper.vm.$?.setupState?.[key]
}

describe('MultiVersionCompare', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getVersions.mockResolvedValue({
      versions: [
        { id: 'ver-2', version: 2, created_at: '2026-06-16T10:00:00Z' },
        { id: 'ver-1', version: 1, created_at: '2026-06-15T10:00:00Z' },
      ],
    })
    mocks.compareVersions.mockResolvedValue({
      card_id: 'card-1',
      compare_results: [
        {
          version_a_id: 'ver-1',
          version_a_number: 1,
          version_b_id: 'ver-2',
          version_b_number: 2,
          has_diff: true,
          diff_summary: 'changed',
        },
      ],
    })
  })

  it('supports wrapped API payloads for versions and compare results', async () => {
    const wrapper = shallowMount(MultiVersionCompare, mountOptions)
    await flushPromises()

    expect(getSetupValue(wrapper, 'versions')).toHaveLength(2)
    expect(getSetupValue(wrapper, 'compareResults')).toEqual([
      expect.objectContaining({
        version_a_id: 'ver-1',
        version_b_id: 'ver-2',
        has_diff: true,
      }),
    ])
  })
})
