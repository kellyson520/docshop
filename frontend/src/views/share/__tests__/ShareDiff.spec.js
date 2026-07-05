import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import ShareDiff from '../ShareDiff.vue'

const mocks = vi.hoisted(() => ({
  downloadViaIframe: vi.fn(),
  routerPush: vi.fn(),
}))

const shareApiMocks = vi.hoisted(() => ({
  getShareVersions: vi.fn(),
  getShareDiffs: vi.fn(() => Promise.resolve({ diffs: [] })),
}))

const shareSessionMocks = vi.hoisted(() => ({
  withShareHeaders: vi.fn(() => ({
    'X-Share-Tab-Id': 'tab-a',
    'X-Share-Grant': 'grant-1',
  })),
}))

const shareResourceTicketMocks = vi.hoisted(() => ({
  getShareResourceUrl: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { token: 'share-token', fileId: 'file-1' } }),
  useRouter: () => ({ push: mocks.routerPush }),
}))

vi.mock('@/api/share', () => ({
  getShareVersions: shareApiMocks.getShareVersions,
  getShareDiffs: shareApiMocks.getShareDiffs,
}))

vi.mock('@/composables/useShareSession', () => ({
  useShareSession: () => ({
    tabId: 'tab-a',
    grantToken: { value: 'grant-1' },
    withShareHeaders: shareSessionMocks.withShareHeaders,
  }),
}))

vi.mock('@/utils', () => ({
  formatDate: (value) => value || '',
  downloadViaIframe: mocks.downloadViaIframe,
}))

vi.mock('@/utils/shareResourceTickets', () => ({
  getShareResourceUrl: shareResourceTicketMocks.getShareResourceUrl,
}))

const passthrough = (name, tag = 'div') =>
  defineComponent({
    name,
    inheritAttrs: false,
    props: ['disabled'],
    emits: ['click'],
    setup(props, { slots, attrs, emit }) {
      return () => h(tag, {
        class: [name, attrs.class],
        disabled: props.disabled || undefined,
        ...attrs,
        onClick: (event) => emit('click', event),
      }, slots.default?.())
    },
  })

const ElCard = defineComponent({
  name: 'ElCard',
  inheritAttrs: false,
  setup(_, { slots, attrs }) {
    return () => h('div', { class: ['el-card', attrs.class] }, [slots.header?.(), slots.default?.()])
  },
})

const globalConfig = {
  components: {
    ElCard,
    ElButton: passthrough('ElButton', 'button'),
    ElIcon: passthrough('ElIcon', 'span'),
    ElSelect: passthrough('ElSelect'),
    ElOption: passthrough('ElOption'),
    ElDropdown: passthrough('ElDropdown'),
    ElDropdownMenu: passthrough('ElDropdownMenu'),
    ElDropdownItem: passthrough('ElDropdownItem'),
    ElEmpty: passthrough('ElEmpty'),
    ElResult: passthrough('ElResult'),
    DiffSummary: passthrough('DiffSummary'),
    DocxDiffView: passthrough('DocxDiffView'),
    XlsxDiffView: passthrough('XlsxDiffView'),
    PdfDiffView: passthrough('PdfDiffView'),
    ArrowLeft: passthrough('ArrowLeft', 'span'),
    Download: passthrough('Download', 'span'),
    Sort: passthrough('Sort', 'span'),
  },
  directives: {
    loading: () => {},
  },
}

describe('ShareDiff downloads', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    shareApiMocks.getShareVersions.mockResolvedValue({
      filename: 'spec.docx',
      file_type: 'docx',
      versions: [
        { id: 'version-2', version: 2, created_at: '2026-06-18T10:00:00Z', download_formats: ['docx', 'pdf'] },
        { id: 'version-1', version: 1, created_at: '2026-06-17T10:00:00Z', download_formats: ['docx', 'pdf'] },
      ],
    })
    shareResourceTicketMocks.getShareResourceUrl.mockResolvedValue(
      '/api/v1/share/share-token/files/file-1/versions/version-1/download/pdf?ticket=ticket-diff-download',
    )
  })

  it('renders old/new version download actions as disabled grey buttons when share download is closed', async () => {
    shareApiMocks.getShareVersions.mockResolvedValueOnce({
      filename: 'spec.docx',
      file_type: 'docx',
      share: { allow_download: false },
      versions: [
        { id: 'version-2', version: 2, created_at: '2026-06-18T10:00:00Z', download_formats: ['docx', 'pdf'] },
        { id: 'version-1', version: 1, created_at: '2026-06-17T10:00:00Z', download_formats: ['docx', 'pdf'] },
      ],
    })

    const wrapper = mount(ShareDiff, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const disabledDownloadButtons = buttons.filter((button) => button.text().includes('禁止下载'))

    expect(disabledDownloadButtons).toHaveLength(2)
    disabledDownloadButtons.forEach((button) => {
      expect(button.attributes('disabled')).toBeDefined()
    })
  })

  it('downloads diff versions through a ticketized share url', async () => {
    const wrapper = mount(ShareDiff, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const vm = wrapper.vm.$?.setupState
    await vm.downloadVersion('version-1', 'pdf')
    await flushPromises()

    expect(shareResourceTicketMocks.getShareResourceUrl).toHaveBeenCalledWith(
      expect.objectContaining({
        token: 'share-token',
        kind: 'download_converted',
        fileId: 'file-1',
        versionId: 'version-1',
        format: 'pdf',
      }),
    )
    expect(mocks.downloadViaIframe).toHaveBeenCalledWith(
      '/api/v1/share/share-token/files/file-1/versions/version-1/download/pdf?ticket=ticket-diff-download',
    )
  })

  it('routes original format downloads through download_original instead of converted download', async () => {
    const wrapper = mount(ShareDiff, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const vm = wrapper.vm.$?.setupState
    await vm.downloadVersion('version-1', 'docx')
    await flushPromises()

    expect(shareResourceTicketMocks.getShareResourceUrl).toHaveBeenCalledWith(
      expect.objectContaining({
        token: 'share-token',
        kind: 'download_original',
        fileId: 'file-1',
        versionId: 'version-1',
        format: undefined,
      }),
    )
  })

  it('renders format labels from backend download formats instead of hard-coded word labels', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const source = fs.readFileSync(path.resolve(__dirname, '../ShareDiff.vue'), 'utf-8')

    expect(source).toContain('getDownloadFormatLabel')
    expect(source).toContain('v-for="format in getDownloadFormats(selectedOldVersion)"')
    expect(source).toContain('v-for="format in getDownloadFormats(selectedNewVersion)"')
    expect(source).not.toContain('<el-dropdown-item command="docx">Word 下载</el-dropdown-item>')
    expect(source).not.toContain('<el-dropdown-item command="pdf">PDF 下载</el-dropdown-item>')
  })
})
