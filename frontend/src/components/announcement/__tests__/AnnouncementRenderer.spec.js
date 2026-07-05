import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import AnnouncementRenderer from '../AnnouncementRenderer.vue'

describe('AnnouncementRenderer', () => {
  it('renders code and button blocks safely', () => {
    render(AnnouncementRenderer, {
      props: {
        blocks: [
          { type: 'paragraph', text: 'Deploy at 22:00' },
          { type: 'code', language: 'bash', content: 'docker compose up -d' },
          { type: 'button', label: '查看详情', url: '/docs/deploy' },
        ],
      },
    })

    expect(screen.getByText('Deploy at 22:00')).toBeInTheDocument()
    expect(screen.getByText('docker compose up -d')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '查看详情' })).toHaveAttribute('href', '/docs/deploy')
  })
})
