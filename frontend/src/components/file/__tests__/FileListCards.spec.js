import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import FileListCards from '../FileListCards.vue'

describe('FileListCards mobile action layout', () => {
  it('keeps a dedicated two-column touch-friendly action grid on phones', async () => {
    const fs = await import('node:fs')
    const path = await import('node:path')
    const sourcePath = path.resolve(__dirname, '../FileListCards.vue')
    const source = fs.readFileSync(sourcePath, 'utf-8')

    expect(source).toContain('@media (max-width: 767px)')
    expect(source).toContain('grid-template-columns: repeat(2, minmax(0, 1fr));')
    expect(source).toContain('width: 100%;')
    expect(source).toContain('min-height: 40px;')
    expect(source).toContain('justify-content: center;')
  })

  it('adds a dedicated compact class for parent navigation cards', () => {
    const wrapper = mount(FileListCards, {
      props: {
        items: [
          { id: 'parent-folder-row', type: 'parent' },
          { id: 'file-1', type: 'file' },
        ],
      },
      slots: {
        title: ({ item }) => item.type,
      },
    })

    const cards = wrapper.findAll('.file-list-card')

    expect(cards[0].classes()).toContain('file-list-card--parent')
    expect(cards[1].classes()).not.toContain('file-list-card--parent')
  })
})
