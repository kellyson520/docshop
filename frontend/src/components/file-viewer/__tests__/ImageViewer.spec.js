import { render, screen } from '@testing-library/vue'
import ImageViewer from '../ImageViewer.vue'

describe('ImageViewer', () => {
  it('renders image preview and enriched metadata summary', () => {
    render(ImageViewer, {
      props: {
        file: { filename: 'poster.jpg', display_name: 'Poster' },
        manifest: {
          type: 'image_native',
          status: 'ready',
          primary_asset: { url: '/preview/poster.jpg' },
        },
        analysisSummary: {
          dimensions: { width: 3024, height: 4032 },
          format: 'JPEG',
          color_mode: 'RGB',
          has_alpha: false,
          orientation: 1,
          aspect_ratio: '3:4',
        },
      },
    })

    expect(screen.getByTestId('image-viewer')).toBeInTheDocument()
    expect(screen.getByTestId('image-viewer-preview')).toHaveAttribute('src', '/preview/poster.jpg')
    expect(screen.getByTestId('image-viewer-dimensions')).toHaveTextContent('3024 × 4032')
    expect(screen.getByTestId('image-viewer-format')).toHaveTextContent('JPEG')
    expect(screen.getByTestId('image-viewer-mode')).toHaveTextContent('RGB')
    expect(screen.getByTestId('image-viewer-alpha')).toHaveTextContent('No')
    expect(screen.getByTestId('image-viewer-ratio')).toHaveTextContent('3:4')
  })
})
