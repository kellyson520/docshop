import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import SharePreview from '../SharePreview.vue'

let mockedShareFileData
let mockedLocation
let latestIntersectionObserverCallback = null
const originalIntersectionObserver = globalThis.IntersectionObserver
const responsiveState = {
  isMobile: false,
}
const scrollState = {
  isScrolled: false,
  scrollToTop: vi.fn(),
}

const clientMocks = vi.hoisted(() => ({
  get: vi.fn(),
}))
const shareApiMocks = vi.hoisted(() => ({
  getShareFile: vi.fn(),
  unlockShareAccess: vi.fn(() => Promise.resolve({ unlocked: true })),
}))
const shareSessionMocks = vi.hoisted(() => ({
  unlock: vi.fn(() => Promise.resolve({ unlocked: true, grant_token: 'grant-1' })),
  release: vi.fn(() => Promise.resolve({ released: true })),
  heartbeat: vi.fn(() => Promise.resolve({ active: true })),
  withShareHeaders: vi.fn(() => ({
    'X-Share-Tab-Id': 'tab-a',
    'X-Share-Grant': 'grant-1',
  })),
}))

const publicAccessSessionMocks = vi.hoisted(() => ({
  unlock: vi.fn(() => Promise.resolve({ unlocked: true, grant_token: 'access-grant-1' })),
  release: vi.fn(() => Promise.resolve({ released: true })),
  heartbeat: vi.fn(() => Promise.resolve({ active: true })),
  withAccessHeaders: vi.fn(() => ({
    'X-Access-Tab-Id': 'tab-a',
    'X-Access-Grant': 'access-grant-1',
  })),
}))
const shareResourceTicketMocks = vi.hoisted(() => ({
  getShareResourceUrl: vi.fn(),
}))
const routerMocks = vi.hoisted(() => ({
  push: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { token: 'share-token', fileId: 'file-1' },
    path: '/s/share-token/preview/file-1',
    fullPath: '/s/share-token/preview/file-1',
    query: {},
  }),
  useRouter: () => ({ push: routerMocks.push }),
}))

vi.mock('@/api/share', () => ({
  getShareFile: shareApiMocks.getShareFile,
  unlockShareAccess: shareApiMocks.unlockShareAccess,
}))

vi.mock('@/composables/useShareSession', () => ({
  useShareSession: () => ({
    tabId: 'tab-a',
    grantToken: { value: 'grant-1' },
    unlock: shareSessionMocks.unlock,
    release: shareSessionMocks.release,
    heartbeat: shareSessionMocks.heartbeat,
    withShareHeaders: shareSessionMocks.withShareHeaders,
    isPasswordRequiredError: (err) => err?.response?.data?.detail === 'share_password_required',
    getUnlockErrorMessage: (err) => (
      err?.response?.data?.detail === 'share_password_invalid'
        ? '密码错误，请重试'
        : '解锁失败，请稍后再试'
    ),
  }),
}))

vi.mock('@/composables/usePublicAccessSession', () => ({
  usePublicAccessSession: () => ({
    tabId: 'tab-a',
    grantToken: { value: 'access-grant-1' },
    unlock: publicAccessSessionMocks.unlock,
    release: publicAccessSessionMocks.release,
    heartbeat: publicAccessSessionMocks.heartbeat,
    withAccessHeaders: publicAccessSessionMocks.withAccessHeaders,
    isResourcePasswordRequiredError: (err) => err?.response?.data?.detail === 'resource_password_required',
    getUnlockErrorMessage: (err) => (
      err?.response?.data?.detail === 'resource_password_invalid'
        ? '访问密码错误，请重试'
        : '资源解锁失败，请稍后重试'
    ),
  }),
}))

vi.mock('@/utils/shareResourceTickets', () => ({
  getShareResourceUrl: shareResourceTicketMocks.getShareResourceUrl,
}))

vi.mock('@/api/client', () => ({
  default: {
    get: clientMocks.get,
  },
}))

vi.mock('@/utils', () => ({
  formatDate: (value) => value || '',
  formatFileSize: (value) => `${value} B`,
}))

vi.mock('@/composables/useResponsive', () => ({
  useResponsive: () => ({
    isMobile: { value: responsiveState.isMobile },
  }),
}))

vi.mock('@/composables/useScroll', () => ({
  useScroll: () => ({
    isScrolled: { value: scrollState.isScrolled },
    scrollToTop: scrollState.scrollToTop,
  }),
}))

const passthrough = (name, tag = 'div') =>
  defineComponent({
    name,
    inheritAttrs: false,
    setup(_, { slots, attrs }) {
      return () => h(tag, { class: [name, attrs.class], ...attrs }, slots.default?.())
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
    ElTag: passthrough('ElTag', 'span'),
    ElIcon: passthrough('ElIcon', 'span'),
    ElSkeleton: passthrough('ElSkeleton'),
    ElResult: passthrough('ElResult'),
  },
}

describe('SharePreview page', () => {
  beforeEach(() => {
    latestIntersectionObserverCallback = null
    mockedLocation = {
      ...window.location,
      replace: vi.fn(),
    }
    vi.stubGlobal('location', mockedLocation)
    globalThis.IntersectionObserver = vi.fn((callback) => {
      latestIntersectionObserverCallback = callback
      return {
        observe: vi.fn(),
        unobserve: vi.fn(),
        disconnect: vi.fn(),
      }
    })
    clientMocks.get.mockReset()
    shareApiMocks.getShareFile.mockImplementation(() => Promise.resolve(mockedShareFileData))
    shareApiMocks.unlockShareAccess.mockResolvedValue({ unlocked: true })
    shareSessionMocks.unlock.mockResolvedValue({ unlocked: true, grant_token: 'grant-1' })
    shareSessionMocks.release.mockResolvedValue({ released: true })
    shareSessionMocks.heartbeat.mockResolvedValue({ active: true })
    shareSessionMocks.withShareHeaders.mockImplementation((headers = {}) => ({
      ...headers,
      'X-Share-Tab-Id': 'tab-a',
      'X-Share-Grant': 'grant-1',
    }))
    publicAccessSessionMocks.unlock.mockResolvedValue({ unlocked: true, grant_token: 'access-grant-1' })
    publicAccessSessionMocks.release.mockResolvedValue({ released: true })
    publicAccessSessionMocks.heartbeat.mockResolvedValue({ active: true })
    publicAccessSessionMocks.withAccessHeaders.mockImplementation((headers = {}) => ({
      ...headers,
      'X-Access-Tab-Id': 'tab-a',
      'X-Access-Grant': 'access-grant-1',
    }))
    shareResourceTicketMocks.getShareResourceUrl.mockImplementation(
      async ({ token, kind, fileId, version, assetId }) => {
        if (kind === 'preview_asset') {
          return `/api/v1/share/${token}/files/${fileId}/preview-assets/${assetId}?ticket=ticket-${assetId}`
        }
        return `/api/v1/share/${token}/files/${fileId}/preview${version ? `?version=${version}` : ''}`
      },
    )
    responsiveState.isMobile = false
    scrollState.isScrolled = false
    scrollState.scrollToTop.mockReset()
    routerMocks.push.mockReset()
    mockedShareFileData = {
      id: 'file-1',
      display_name: 'Course Video',
      filename: 'lesson.mp4',
      original_filename: 'lesson.mp4',
      current_version: 3,
      file_type: 'mp4',
      file_size: 4096,
      created_at: '2026-06-17T10:00:00Z',
      share: { allow_download: true },
      analysis_summary: { duration_seconds: 12 },
      preview_manifest: {
        type: 'video_native',
        status: 'ready',
        primary_asset: {
          asset_type: 'video',
          url: '/api/v1/share/share-token/files/file-1/preview',
        },
        summary: { duration_seconds: 12 },
      },
    }
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    globalThis.IntersectionObserver = originalIntersectionObserver
  })

  it('renders the video viewer for video preview pages', async () => {
    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const video = wrapper.find('[data-testid="video-player"]')
    expect(video.exists()).toBe(true)
    expect(shareResourceTicketMocks.getShareResourceUrl).toHaveBeenCalledWith(
      expect.objectContaining({
        token: 'share-token',
        kind: 'preview',
        fileId: 'file-1',
        version: 3,
      }),
    )
    expect(video.attributes('src')).toBe('/api/v1/share/share-token/files/file-1/preview?version=3')
  })

  it('renders a compact mobile preview shell with collapsible info and sticky actions on phones', async () => {
    responsiveState.isMobile = true

    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="share-preview-mobile-toolbar"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="share-preview-mobile-actions"]').exists()).toBe(true)

    const toggle = wrapper.find('[data-testid="share-preview-mobile-info-toggle"]')
    expect(toggle.exists()).toBe(true)
    expect(wrapper.find('[data-testid="share-preview-mobile-info-panel"]').exists()).toBe(false)

    await toggle.trigger('click')

    expect(wrapper.find('[data-testid="share-preview-mobile-info-panel"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Course Video')
  })

  it('renders a compact collapsed desktop preview shell with shorter back button and disabled back-to-top control before scrolling', async () => {
    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const shell = wrapper.find('[data-testid="share-preview-desktop-shell"]')
    expect(shell.exists()).toBe(true)
    expect(shell.text()).toContain('Course Video')
    expect(shell.text()).toContain('v3')
    expect(shell.text()).toContain('返回')
    expect(wrapper.find('[data-testid="share-preview-desktop-meta"]').exists()).toBe(false)
    const backToTop = wrapper.find('[data-testid="share-preview-back-to-top"]')
    expect(backToTop.exists()).toBe(true)
    expect(backToTop.attributes('disabled')).toBeDefined()

    const toggle = wrapper.find('[data-testid="share-preview-desktop-toggle"]')
    expect(toggle.exists()).toBe(true)
    await toggle.trigger('click')

    expect(wrapper.find('[data-testid="share-preview-desktop-meta"]').exists()).toBe(true)
    expect(shell.text()).toContain('MP4')
  })

  it('enables desktop back-to-top after scrolling and wires the action correctly', async () => {
    scrollState.isScrolled = true

    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const backToTop = wrapper.find('[data-testid="share-preview-back-to-top"]')
    expect(backToTop.exists()).toBe(true)
    expect(backToTop.attributes('disabled')).toBeUndefined()

    await backToTop.trigger('click')
    expect(scrollState.scrollToTop).toHaveBeenCalled()
  })

  it('also enables desktop back-to-top when the top sentinel leaves the viewport', async () => {
    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const backToTop = wrapper.find('[data-testid="share-preview-back-to-top"]')
    expect(backToTop.exists()).toBe(true)
    expect(backToTop.attributes('disabled')).toBeDefined()
    expect(latestIntersectionObserverCallback).toBeTypeOf('function')

    latestIntersectionObserverCallback([{ isIntersecting: false }])
    await flushPromises()

    expect(wrapper.find('[data-testid="share-preview-back-to-top"]').attributes('disabled')).toBeUndefined()
  })

  it('uses refresh and back-to-top as the only mobile bottom actions to avoid duplicate return buttons', async () => {
    responsiveState.isMobile = true

    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const actions = wrapper.find('[data-testid="share-preview-mobile-actions"]')
    expect(actions.exists()).toBe(true)
    expect(actions.text()).toContain('刷新预览')
    expect(actions.text()).toContain('回到顶部')
    expect(actions.text()).not.toContain('返回列表')
  })

  it('renders share video previews when the primary asset is preview_video', async () => {
    mockedShareFileData = {
      ...mockedShareFileData,
      preview_manifest: {
        ...mockedShareFileData.preview_manifest,
        primary_asset: {
          asset_id: 'asset-preview',
          asset_type: 'preview_video',
          url: '/api/v1/share/share-token/files/file-1/preview-assets/asset-preview',
        },
        poster_asset: {
          asset_id: 'asset-poster',
          asset_type: 'poster',
          url: '/api/v1/share/share-token/files/file-1/preview-assets/asset-poster',
        },
      },
    }

    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    const video = wrapper.find('[data-testid="video-player"]')
    expect(video.exists()).toBe(true)
    expect(shareResourceTicketMocks.getShareResourceUrl).toHaveBeenCalledWith(
      expect.objectContaining({
        token: 'share-token',
        kind: 'preview_asset',
        fileId: 'file-1',
        assetId: 'asset-preview',
        version: 3,
      }),
    )
    expect(shareResourceTicketMocks.getShareResourceUrl).toHaveBeenCalledWith(
      expect.objectContaining({
        token: 'share-token',
        kind: 'preview_asset',
        fileId: 'file-1',
        assetId: 'asset-poster',
        version: 3,
      }),
    )
    expect(video.attributes('src')).toBe(
      '/api/v1/share/share-token/files/file-1/preview-assets/asset-preview?ticket=ticket-asset-preview',
    )
    expect(video.attributes('poster')).toBe(
      '/api/v1/share/share-token/files/file-1/preview-assets/asset-poster?ticket=ticket-asset-poster',
    )
  })

  it('keeps the existing video preview layout for video files', async () => {
    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="video-player"]').exists()).toBe(true)
    expect(wrapper.find('.preview-card').exists()).toBe(true)
    expect(wrapper.find('[data-testid="share-preview-direct-stage"]').exists()).toBe(false)
  })

  it('renders runtime html previews in a shell-free immersive stage instead of raw location.replace', async () => {
    mockedShareFileData = {
      id: 'file-1',
      display_name: 'Interactive Page',
      filename: 'page.html',
      original_filename: 'page.html',
      file_type: 'html',
      file_size: 1024,
      created_at: '2026-06-17T10:00:00Z',
      share: { allow_download: true },
      analysis_summary: {},
      preview_manifest: {
        type: 'html_runtime',
        status: 'ready',
        primary_asset: {
          asset_type: 'html_runtime_entry',
          url: '/api/v1/share/share-token/files/file-1/preview',
        },
      },
    }

    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('.preview-card').exists()).toBe(false)
    expect(wrapper.find('.file-info-card').exists()).toBe(false)
    expect(wrapper.find('[data-testid="share-preview-direct-stage"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="share-preview-desktop-shell"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="share-preview-mobile-shell"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="share-preview-html-frame"]').exists()).toBe(true)
    expect(mockedLocation.replace).not.toHaveBeenCalled()
    expect(clientMocks.get).not.toHaveBeenCalled()
  })

  it('restores office preview as directly mounted skeleton html instead of iframe srcdoc', async () => {
    mockedShareFileData = {
      id: 'file-1',
      display_name: 'Spec Document',
      filename: 'spec.docx',
      original_filename: 'spec.docx',
      file_type: 'docx',
      file_size: 1024,
      created_at: '2026-06-17T10:00:00Z',
      share: { allow_download: true },
      analysis_summary: { page_count: 3 },
      preview_manifest: {
        type: 'office_pdf',
        status: 'ready',
        primary_asset: {
          asset_type: 'pdf',
          url: '/api/v1/share/share-token/files/file-1/preview',
        },
      },
    }
    clientMocks.get.mockResolvedValueOnce('<!DOCTYPE html><html><body><main>office skeleton</main></body></html>')

    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('.preview-card').exists()).toBe(false)
    expect(wrapper.find('.file-info-card').exists()).toBe(false)
    expect(wrapper.find('[data-testid="share-preview-direct-stage"]').exists()).toBe(true)
    expect(clientMocks.get).toHaveBeenCalledWith(
      '/share/share-token/files/file-1/preview?version=1',
      expect.objectContaining({
        responseType: 'text',
      }),
    )

    const mountedOffice = wrapper.find('[data-testid="share-preview-office-mounted"]')
    expect(mountedOffice.exists()).toBe(true)
    expect(mountedOffice.html()).toContain('office skeleton')
    expect(wrapper.find('[data-testid="share-preview-office-frame"]').exists()).toBe(false)
  })

  it('renders images directly without the shared preview card container', async () => {
    mockedShareFileData = {
      id: 'file-1',
      display_name: 'Poster',
      filename: 'poster.png',
      original_filename: 'poster.png',
      file_type: 'png',
      file_size: 1024,
      created_at: '2026-06-17T10:00:00Z',
      share: { allow_download: true },
      analysis_summary: {},
      preview_manifest: {
        type: 'image_native',
        status: 'ready',
        primary_asset: {
          asset_type: 'image',
          url: '/api/v1/share/share-token/files/file-1/preview',
        },
      },
    }

    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('.preview-card').exists()).toBe(false)
    expect(wrapper.find('.file-info-card').exists()).toBe(false)
    expect(wrapper.find('[data-testid="share-preview-direct-stage"]').exists()).toBe(true)
    const image = wrapper.find('[data-testid="share-preview-image"]')
    expect(image.exists()).toBe(true)
    expect(image.attributes('src')).toBe('/api/v1/share/share-token/files/file-1/preview?version=1')
  })

  it('renders pdf preview in immersive direct stage without preview card', async () => {
    mockedShareFileData = {
      id: 'file-9',
      display_name: 'PDF Handout',
      filename: 'handout.pdf',
      original_filename: 'handout.pdf',
      file_type: 'pdf',
      file_size: 2048,
      created_at: '2026-06-17T10:00:00Z',
      share: { allow_download: true },
      analysis_summary: {},
      preview_manifest: {
        type: 'pdf_native',
        status: 'ready',
        primary_asset: {
          asset_type: 'pdf',
          url: '/api/v1/share/share-token/files/file-9/preview',
        },
      },
    }

    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('.preview-card').exists()).toBe(false)
    expect(wrapper.find('.file-info-card').exists()).toBe(false)
    expect(wrapper.find('[data-testid="share-preview-direct-stage"]').exists()).toBe(true)
    const pdf = wrapper.find('[data-testid="share-preview-pdf-frame"]')
    expect(pdf.exists()).toBe(true)
    expect(pdf.attributes('src')).toBe('/api/v1/share/share-token/files/file-1/preview?version=1')
  })

  it('renders the backend preview title and page number shell for office previews', async () => {
    mockedShareFileData = {
      id: 'file-1',
      display_name: '汽车服务 - protable.docx',
      filename: 'protable.docx',
      original_filename: 'protable.docx',
      file_type: 'docx',
      file_size: 1024,
      created_at: '2026-06-17T10:00:00Z',
      share: { allow_download: true },
      analysis_summary: { page_count: 3 },
      preview_manifest: {
        type: 'office_pdf',
        status: 'ready',
        primary_asset: {
          asset_type: 'pdf',
          url: '/api/v1/share/share-token/files/file-1/preview',
        },
      },
    }
    clientMocks.get.mockResolvedValueOnce(
      '<!DOCTYPE html><html><body><div class="preview-shell"><h1 class="preview-title">汽车服务 - protable.docx · v3</h1><main>office skeleton</main><div class="page-num">1 / 3</div></div></body></html>',
    )

    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('.preview-title').exists()).toBe(true)
    expect(wrapper.find('.preview-title').text()).toBe('汽车服务 - protable.docx · v3')
    expect(wrapper.text()).toContain('1 / 3')
    expect(wrapper.find('[data-testid="share-preview-direct-stage"]').exists()).toBe(true)
  })

  it('keeps a dedicated preview scale token for immersive share previews', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../SharePreview.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')

    expect(source).toContain('--share-preview-scale')
    expect(source).toContain('zoom: var(--share-preview-scale)')
  })

  it('keeps html previews in an immersive full-viewport stage and only scales embeddable non-html preview surfaces', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../SharePreview.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')

    expect(source).not.toContain('location.replace(resolvedPreviewUrl.value)')
    expect(source).not.toContain('redirectingToNativeHtml')
    expect(source).toContain("!previewUsesBareHtmlStage.value && !showMobilePreviewShell.value && !!fileInfo.value")
    expect(source).toContain('data-testid="share-preview-html-frame"')
    expect(source).toContain("class=\"['preview-frame preview-frame--direct', { 'preview-frame--html-immersive': previewUsesBareHtmlStage }]\"")
    expect(source).toContain(":class=\"['share-preview__direct-stage', { 'share-preview__direct-stage--html-immersive': previewUsesBareHtmlStage }]\"")
    expect(source).toContain('.share-preview__direct-stage--html-immersive')
    expect(source).toContain('.preview-frame--html-immersive')
    expect(source).toContain('sandbox="allow-scripts allow-forms allow-modals allow-downloads"')
  })

  it('keeps the mobile preview shell sticky with safe-area spacing and touch-friendly controls', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../SharePreview.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')

    expect(source).toContain('.preview-mobile-shell')
    expect(source).toContain('top: calc(8px + env(safe-area-inset-top));')
    expect(source).toContain('.preview-mobile-toolbar__button')
    expect(source).toContain('min-height: 40px;')
    expect(source).toContain('padding: 10px max(12px, env(safe-area-inset-right))')
  })

  it('keeps a desktop sticky title shell with centered content, shorter shell container and sentinel-backed back-to-top button state', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../SharePreview.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')

    expect(source).toContain("from '@/composables/useScroll'")
    expect(source).toContain('data-testid="share-preview-desktop-shell"')
    expect(source).toContain('data-testid="share-preview-desktop-toggle"')
    expect(source).toContain('data-testid="share-preview-desktop-meta"')
    expect(source).toContain('data-testid="share-preview-back-to-top"')
    expect(source).toContain('desktopShellExpanded')
    expect(source).toContain('desktopTopSentinelRef')
    expect(source).toContain('desktopTopSentinelVisible')
    expect(source).toContain('IntersectionObserver')
    expect(source).toContain('preview-desktop-shell__top-sentinel')
    expect(source).toContain('preview-desktop-shell__back')
    expect(source).toContain('.preview-desktop-shell')
    expect(source).toContain('position: sticky;')
    expect(source).toContain('inline-size: fit-content;')
    expect(source).toContain('grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);')
    expect(source).toContain('text-align: center;')
    expect(source).toContain("` · v${currentPreviewVersion.value}`")
    expect(source).toContain(':disabled="!showDesktopBackToTop"')
    expect(source).toContain('justify-self: start;')
    expect(source).toContain('padding: 10px 14px;')
    expect(source).toContain('font-size: 16px;')
    expect(source).toContain('padding: 8px 14px 10px;')
    expect(source).toContain('scrollToTop()')
  })

  it('prompts for password-protected previews and retries after unlock', async () => {
    shareApiMocks.getShareFile
      .mockRejectedValueOnce({ response: { data: { detail: 'share_password_required' } } })
      .mockResolvedValueOnce({
        ...mockedShareFileData,
        display_name: 'Unlocked Preview',
      })

    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="share-unlock-card"]').exists()).toBe(true)

    const vm = wrapper.vm.$?.setupState
    vm.unlockPassword = 'OpenSesame!1'
    await vm.submitUnlock()

    await flushPromises()
    await flushPromises()

    expect(shareSessionMocks.unlock).toHaveBeenCalledWith('OpenSesame!1')
    expect(shareApiMocks.getShareFile).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Unlocked Preview')
  })

  it('prompts for legacy public preview passwords and retries after resource unlock', async () => {
    shareApiMocks.getShareFile
      .mockRejectedValueOnce({ response: { data: { detail: 'resource_password_required' } } })
      .mockResolvedValueOnce({
        ...mockedShareFileData,
        display_name: 'Unlocked Preview',
      })

    const wrapper = mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(wrapper.find('[data-testid="share-unlock-card"]').exists()).toBe(true)

    const vm = wrapper.vm.$?.setupState
    vm.unlockPassword = 'OpenSesame!1'
    await vm.submitUnlock()

    await flushPromises()
    await flushPromises()

    expect(publicAccessSessionMocks.unlock).toHaveBeenCalledWith('OpenSesame!1')
    expect(shareApiMocks.getShareFile).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Unlocked Preview')
  })

  it('reuses the existing access-denied gate page when share preview is blocked by invalid local auth', async () => {
    shareApiMocks.getShareFile.mockRejectedValueOnce({
      response: {
        status: 401,
        data: { detail: 'Could not validate credentials' },
      },
    })

    mount(SharePreview, { global: globalConfig })

    await flushPromises()
    await flushPromises()

    expect(routerMocks.push).toHaveBeenCalledWith({
      path: '/access-denied',
      query: {
        redirect: '/s/share-token/preview/file-1',
        reason: 'invalid_token',
      },
    })
  })
})
