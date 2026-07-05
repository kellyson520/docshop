import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import ShareProject from '../ShareProject.vue'
import ShareFile from '../ShareFile.vue'
import SharePreview from '../SharePreview.vue'

const responsiveState = {
  isMobile: false,
}

const clientMocks = vi.hoisted(() => ({
  get: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { token: 'share-token', fileId: 'file-1' } }),
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/api/share', () => ({
  getShareProject: () => Promise.resolve({
    project: { name: 'Shared Project', description: '' },
    share: { allow_download: true },
    folders: [{ id: 'folder-1', name: 'Contracts' }],
    files: [
      {
        id: 'file-1',
        display_name: 'Edited Name.docx',
        original_filename: 'original-name.docx',
        filename: 'original-name.docx',
        folder_id: 'folder-1',
        file_type: 'docx',
        current_version: 2,
        updated_at: '2026-06-17T10:00:00Z',
        versions: [{ id: 'version-2' }],
      },
      {
        id: 'file-2',
        display_name: 'Root File.pdf',
        original_filename: 'root-file.pdf',
        filename: 'root-file.pdf',
        folder_id: '',
        file_type: 'pdf',
        current_version: 1,
        updated_at: '2026-06-17T10:00:00Z',
        versions: [{ id: 'version-1' }],
      },
    ],
  }),
  getShareFile: () => Promise.resolve({
    id: 'file-1',
    display_name: 'Edited Name.docx',
    original_filename: 'original-name.docx',
    filename: 'original-name.docx',
    file_type: 'docx',
    file_size: 1024,
    created_at: '2026-06-17T10:00:00Z',
    share: { allow_download: true },
    preview_manifest: {
      type: 'office_pdf',
      status: 'ready',
      primary_asset: {
        asset_type: 'pdf',
        url: '/api/v1/share/share-token/files/file-1/preview',
      },
    },
  }),
  getShareVersions: () => Promise.resolve({
    share: { allow_download: true },
    versions: [{ id: 'version-2', version: 2, created_at: '2026-06-17T10:00:00Z' }],
  }),
  getShareDiffs: () => Promise.resolve({ diffs: [] }),
}))

vi.mock('@/api/client', () => ({
  default: {
    get: clientMocks.get,
  },
}))

vi.mock('@/composables/useResponsive', () => ({
  useResponsive: () => ({
    isMobile: { value: responsiveState.isMobile },
  }),
}))

vi.mock('@/utils', () => ({
  formatDate: (value) => value || '',
  formatFileSize: (value) => `${value} B`,
  getFileTypeIcon: () => 'Document',
  downloadViaIframe: vi.fn(),
}))

vi.mock('@/utils/versionHistory', () => ({
  buildDiffByNewVersion: () => ({}),
  canCompareWithPreviousVersion: () => false,
  getVersionDiffStats: () => null,
  isLatestVersion: () => true,
  normalizeVersionHistory: (versions) => versions,
}))

const passthrough = (name, tag = 'div') =>
  defineComponent({
    name,
    inheritAttrs: false,
    props: ['disabled'],
    emits: ['click', 'command'],
    setup(props, { slots, emit, attrs }) {
      return () =>
        h(
          tag,
          {
            class: [name, attrs.class],
            disabled: props.disabled || undefined,
            onClick: (event) => emit('click', event),
          },
          slots.default?.(),
        )
    },
  })

const ElTableColumn = defineComponent({
  name: 'ElTableColumn',
  props: ['prop', 'label'],
  setup() {
    return () => null
  },
})

const ElTable = defineComponent({
  name: 'ElTable',
  props: ['data'],
  setup(props, { slots, attrs }) {
    return () => {
      const columns = (slots.default?.() || []).filter((vnode) => vnode && vnode.type)
      return h(
        'div',
        { class: ['el-table', attrs.class] },
        (props.data || []).map((row, rowIndex) =>
          h(
            'div',
            { class: 'el-table__row', 'data-row': rowIndex },
            columns.map((column, columnIndex) => {
              const cellSlot = column.children?.default
              const content = cellSlot ? cellSlot({ row, $index: rowIndex }) : row[column.props?.prop] ?? ''
              return h('div', { class: 'el-table__cell', 'data-column': columnIndex }, content)
            }),
          ),
        ),
      )
    }
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
    ElTable,
    ElTableColumn,
    ElButton: passthrough('ElButton', 'button'),
    ElTag: passthrough('ElTag', 'span'),
    ElIcon: passthrough('ElIcon', 'span'),
    ElDropdown: passthrough('ElDropdown'),
    ElDropdownMenu: passthrough('ElDropdownMenu'),
    ElDropdownItem: passthrough('ElDropdownItem'),
    ElTooltip: passthrough('ElTooltip'),
    ElEmpty: passthrough('ElEmpty'),
    ElSkeleton: passthrough('ElSkeleton'),
    ElResult: passthrough('ElResult'),
    ElTimeline: passthrough('ElTimeline'),
    ElTimelineItem: passthrough('ElTimelineItem'),
    ElInput: passthrough('ElInput', 'input'),
  },
}

beforeEach(() => {
  clientMocks.get.mockReset()
  clientMocks.get.mockResolvedValue(
    '<html><body><div class="preview-shell"><h1 class="preview-title">Edited Name.docx v2</h1><main>office skeleton</main><div class="page-num">1 / 2</div></div></body></html>',
  )
  responsiveState.isMobile = false
})

describe('share file display name', () => {
  it('share project list prefers edited display_name over original_filename', async () => {
    const wrapper = mount(ShareProject, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('Edited Name.docx')
    expect(wrapper.text()).not.toContain('original-name.docx')
  })

  it('share file detail prefers edited display_name over original_filename', async () => {
    const wrapper = mount(ShareFile, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('.file-name').text()).toBe('Edited Name.docx')
  })

  it('share preview page keeps the backend title shell for office previews', async () => {
    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(clientMocks.get).toHaveBeenCalledWith(
      expect.stringContaining('/share/share-token/files/file-1/preview'),
      expect.objectContaining({ responseType: 'text' }),
    )
    expect(wrapper.find('.preview-title').text()).toBe('Edited Name.docx v2')
    expect(wrapper.text()).toContain('1 / 2')
    expect(wrapper.find('[data-testid="share-preview-office-mounted"]').exists()).toBe(true)
  })

  it('share project mixes folders and files in one resource list and opens folders inline', async () => {
    const wrapper = mount(ShareProject, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const vm = wrapper.vm.$?.setupState
    const readItems = () => {
      const raw = vm.resourceItems?.value ?? vm.resourceItems
      return Array.isArray(raw) ? raw : []
    }

    expect(wrapper.find('.folder-grid').exists()).toBe(false)
    expect(readItems().map((item) => item.type)).toEqual(['folder', 'file'])
    expect(wrapper.text()).toContain('Contracts')
    expect(wrapper.text()).toContain('Root File.pdf')

    vm.handleResourceRowClick(readItems()[0])
    await flushPromises()

    const nestedItems = readItems()
    expect(nestedItems[0].type).toBe('parent')
    expect(nestedItems.some((item) => item.type === 'file' && item.id === 'file-1')).toBe(true)
    expect(wrapper.text()).toContain('Edited Name.docx')
    expect(wrapper.text()).not.toContain('Root File.pdf')
  })

  it('share project uses stacked mobile file cards on phones', async () => {
    responsiveState.isMobile = true
    const wrapper = mount(ShareProject, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="share-mobile-file-list"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Edited Name.docx')
    expect(wrapper.text()).toContain('Root File.pdf')
    expect(wrapper.find('.file-table').exists()).toBe(false)
  })

  it('share project renders a dedicated mobile shell with collapsible project info and resource summary', async () => {
    responsiveState.isMobile = true
    const wrapper = mount(ShareProject, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const shell = wrapper.find('[data-testid="share-project-mobile-shell"]')
    expect(shell.exists()).toBe(true)
    expect(shell.text()).toContain('Shared Project')
    expect(shell.text()).toContain('2 个文件')
    expect(shell.text()).toContain('1 个文件夹')
    expect(wrapper.find('[data-testid="share-project-mobile-info-summary"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="share-project-mobile-resource-head"]').exists()).toBe(true)

    responsiveState.isMobile = false
  })

  it('keeps the mobile resource head sticky with safe-area spacing on phones', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../ShareProject.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')

    expect(source).toContain('.share-project-mobile-resource-head')
    expect(source).toContain('position: sticky;')
    expect(source).toContain('top: calc(8px + env(safe-area-inset-top));')
    expect(source).toContain('z-index: 4;')
  })

  it('keeps the mobile parent-folder card concise instead of repeating return copy in multiple sections', async () => {
    responsiveState.isMobile = true
    const wrapper = mount(ShareProject, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const vm = wrapper.vm.$?.setupState
    vm.openFolder('folder-1')
    await flushPromises()

    const cards = wrapper.findAll('.file-list-card')
    expect(cards.length).toBeGreaterThan(0)

    const parentCardText = cards[0].text()
    const repeatedReturnRootMatches = parentCardText.match(/返回根目录/g) || []

    expect(parentCardText).toContain('返回上一级')
    expect(repeatedReturnRootMatches.length).toBeLessThanOrEqual(1)

    responsiveState.isMobile = false
  })
})
