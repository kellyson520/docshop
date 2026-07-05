import { render, screen } from '@testing-library/vue'
import FileViewer from '../FileViewer.vue'

describe('FileViewer', () => {
  it('renders the video viewer for video manifests', () => {
    render(FileViewer, {
      props: {
        file: { filename: 'demo.mp4' },
        manifest: {
          type: 'video_native',
          status: 'ready',
          primary_asset: { asset_type: 'video', url: '/api/v1/files/file-1/preview?version=1' },
          poster_asset: { asset_type: 'poster', url: '/api/v1/files/file-1/preview-assets/asset-1' },
        },
        analysisSummary: {
          duration_seconds: 30,
          dimensions: { width: 1920, height: 1080 },
          codec: 'h264',
          bit_rate: 512000,
        },
      },
    })

    expect(screen.getByTestId('video-viewer')).toBeInTheDocument()
    const video = screen.getByTestId('video-player')
    expect(video).toHaveAttribute('poster', '/api/v1/files/file-1/preview-assets/asset-1')
    expect(video).toHaveAttribute('src', '/api/v1/files/file-1/preview?version=1')
    expect(screen.getByTestId('video-viewer-resolution')).toHaveTextContent('1920 × 1080')
    expect(screen.getByTestId('video-viewer-codec')).toHaveTextContent('h264')
    expect(screen.getByTestId('video-viewer-bitrate')).toHaveTextContent('512 kbps')
  })

  it('renders the video viewer when the primary asset is preview_video', () => {
    render(FileViewer, {
      props: {
        file: { filename: 'demo.mp4' },
        manifest: {
          type: 'video_native',
          status: 'ready',
          primary_asset: {
            asset_type: 'preview_video',
            url: '/api/v1/files/file-1/preview-assets/asset-preview',
          },
          poster_asset: {
            asset_type: 'poster',
            url: '/api/v1/files/file-1/preview-assets/asset-poster',
          },
        },
        analysisSummary: {
          codec: 'h264',
        },
      },
    })

    const video = screen.getByTestId('video-player')
    expect(video).toHaveAttribute('poster', '/api/v1/files/file-1/preview-assets/asset-poster')
    expect(video).toHaveAttribute('src', '/api/v1/files/file-1/preview-assets/asset-preview')
  })

  it('keeps video previews in a fixed contain stage for extreme aspect ratios', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../VideoViewer.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')

    expect(source).toContain('object-fit: contain;')
    expect(source).toContain('height: min(72vh, 720px);')
    expect(source).toContain('display: flex;')
    expect(source).toContain('justify-content: center;')
    expect(source).toContain('align-items: center;')
  })

  it('renders the html viewer for html manifests', () => {
    render(FileViewer, {
      props: {
        file: { filename: 'report.html' },
        manifest: {
          type: 'html_runtime',
          status: 'ready',
          primary_asset: {
            asset_type: 'html_runtime_entry',
            url: '/api/v1/files/file-1/preview?version=1',
          },
        },
        analysisSummary: {},
      },
    })

    const iframe = screen.getByTestId('html-viewer-frame')
    expect(iframe).toHaveAttribute('src', '/api/v1/files/file-1/preview?version=1')
    expect(iframe).toHaveAttribute('sandbox', 'allow-scripts allow-forms allow-modals allow-downloads')
    expect(iframe).toHaveAttribute('referrerpolicy', 'no-referrer')
  })

  it('renders the office preview viewer for converted office manifests', () => {
    render(FileViewer, {
      props: {
        file: { filename: 'slides.pptx' },
        manifest: { type: 'office_pdf', status: 'ready' },
        analysisSummary: { page_count: 12 },
      },
    })

    expect(screen.getByTestId('office-preview-viewer')).toBeInTheDocument()
  })

  it('renders the archive structure viewer for archive manifests', () => {
    render(FileViewer, {
      props: {
        file: { filename: 'bundle.zip' },
        manifest: { type: 'archive_structure', status: 'ready' },
        analysisSummary: { entry_count: 42 },
      },
    })

    expect(screen.getByTestId('archive-structure-viewer')).toBeInTheDocument()
  })

  it('renders the image viewer for native image manifests', () => {
    render(FileViewer, {
      props: {
        file: { filename: 'poster.jpg' },
        manifest: {
          type: 'image_native',
          status: 'ready',
          primary_asset: { url: '/preview/poster.jpg' },
        },
        analysisSummary: { format: 'JPEG', dimensions: { width: 3024, height: 4032 } },
      },
    })

    expect(screen.getByTestId('image-viewer')).toBeInTheDocument()
  })

  it('falls back to a simple card when no specialized viewer exists', () => {
    render(FileViewer, {
      props: {
        file: { filename: 'archive.bin' },
        manifest: { type: 'fallback', status: 'not_supported' },
        analysisSummary: {},
      },
    })

    expect(screen.getByTestId('fallback-file-card')).toBeInTheDocument()
  })
})
