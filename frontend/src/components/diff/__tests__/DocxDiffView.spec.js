import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DocxDiffView from '../DocxDiffView.vue'

const dataUri = 'data:image/png;base64,iVBORw0KGgo='

const global = {
  stubs: {
    'el-empty': { template: '<div class="el-empty">{{ description }}</div>', props: ['description'] },
    'el-icon': { template: '<span class="el-icon"><slot /></span>' },
    'el-tag': { template: '<span class="el-tag"><slot /></span>' },
    ArrowRight: { template: '<i />' },
    Plus: { template: '<i />' },
    Minus: { template: '<i />' },
    Refresh: { template: '<i />' }
  }
}

describe('DocxDiffView', () => {
  it('renders readable filter labels instead of placeholder question marks', () => {
    const wrapper = mount(DocxDiffView, {
      global,
      props: {
        diffData: {
          paragraphs: [{ change_type: 'insert', new_text: '新增段落' }],
          tables: [],
          images: {}
        }
      }
    })

    const labels = wrapper.findAll('.filter-chip').map((button) => button.text())
    expect(labels).toEqual(['全部', '文字', '表格', '图片', '新增', '删除', '修改', '移动', '替换', '尺寸'])
    expect(labels).not.toContain('??')
  })

  it('tolerates legacy table diffs without optional arrays or shape metadata', () => {
    const wrapper = mount(DocxDiffView, {
      global,
      props: {
        diffData: {
          paragraphs: [],
          tables: [
            {
              table_index: 0,
              old_rows: [['A1']],
              new_rows: [['A1', 'B1']],
              added_rows: [1],
              deleted_rows: [2],
              added_cols: [1],
              deleted_cols: [0]
            }
          ],
          images: {}
        }
      }
    })

    expect(wrapper.find('.excel-diff-table').exists()).toBe(true)
    expect(wrapper.text()).toContain('表格 #1')
    expect(wrapper.text()).toContain('+ 行 2')
    expect(wrapper.text()).toContain('- 行 3')
    expect(wrapper.text()).toContain('+ 列 B')
    expect(wrapper.text()).toContain('- 列 A')
  })

  it('renders move descriptions, Excel-style table diff, and image thumbnails', () => {
    const wrapper = mount(DocxDiffView, {
      global,
      props: {
        diffData: {
          paragraphs: [
            {
              change_type: 'move',
              old_text: '需要调序的段落',
              new_text: '需要调序的段落',
              metadata: {
                move_id: 1,
                from: 1,
                to: 3,
                description: '第 2 段移动到第 4 段之后'
              }
            }
          ],
          tables: [
            {
              table_index: 0,
              old_shape: [2, 2],
              new_shape: [2, 2],
              old_rows: [['作物', '旧值'], ['玉米', '12']],
              new_rows: [['作物', '新值'], ['玉米', '18']],
              cell_changes: [
                { row: 1, col: 1, old_value: '12', new_value: '18', change_type: 'replace' }
              ],
              row_moves: [{ from: 1, to: 0 }],
              col_moves: [{ from: 1, to: 0 }]
            }
          ],
          images: {
            added: 1,
            deleted: 1,
            replaced: 1,
            resized: 1,
            added_items: [
              { display_name: 'new-map.png', data_uri: dataUri, short_hash: 'add123456789', width_cm: 3.2, height_cm: 1.8, paragraph_index: 8 }
            ],
            deleted_items: [
              { display_name: 'old-chart.png', short_hash: 'del123456789', width_cm: 2.1, height_cm: 1.4, paragraph_index: 5 }
            ],
            replaced_list: [
              {
                filename: 'hero.png',
                old: { display_name: 'hero.png', data_uri: dataUri, short_hash: 'oldhero12345', width_cm: 3, height_cm: 2 },
                new: { display_name: 'hero.png', data_uri: dataUri, short_hash: 'newhero12345', width_cm: 3, height_cm: 2 }
              }
            ],
            resized_list: [
              {
                filename: 'logo.png',
                old_width_cm: 1,
                new_width_cm: 2,
                old: { display_name: 'logo.png', data_uri: dataUri, short_hash: 'samehash1234', width_cm: 1, height_cm: 1 },
                new: { display_name: 'logo.png', data_uri: dataUri, short_hash: 'samehash1234', width_cm: 2, height_cm: 2 }
              }
            ]
          }
        }
      }
    })

    expect(wrapper.text()).toContain('第 2 段移动到第 4 段之后')
    expect(wrapper.find('.excel-diff-table').exists()).toBe(true)
    expect(wrapper.find('.excel-cell--replace').exists()).toBe(true)
    expect(wrapper.text()).toContain('行 2 → 1')
    expect(wrapper.text()).toContain('列 B → A')

    expect(wrapper.find('img[alt="new-map.png"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('删除占位')
    expect(wrapper.text()).toContain('图片替换')
    expect(wrapper.text()).toContain('尺寸调整')
    expect(wrapper.text()).toContain('add123456789')
  })

  it('filters by image/table/text type and highlights text search matches', async () => {
    const wrapper = mount(DocxDiffView, {
      global,
      props: {
        diffData: {
          paragraphs: [
            { change_type: 'insert', new_text: '新增无人机施肥策略' },
            { change_type: 'delete', old_text: '删除旧版作物描述' }
          ],
          tables: [
            {
              table_index: 0,
              old_rows: [['作物', '旧值']],
              new_rows: [['作物', '新值']],
              cell_changes: [{ row: 0, col: 1, old_value: '旧值', new_value: '新值', change_type: 'replace' }]
            }
          ],
          images: {
            added: [{ display_name: 'drone-map.png', data_uri: dataUri, short_hash: 'img123456789' }]
          }
        }
      }
    })

    await wrapper.find('[data-testid="docx-filter-image"]').trigger('click')
    expect(wrapper.find('img[alt="drone-map.png"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('新增无人机施肥策略')
    expect(wrapper.find('.excel-diff-table').exists()).toBe(false)

    await wrapper.find('[data-testid="docx-filter-table"]').trigger('click')
    expect(wrapper.find('.excel-diff-table').exists()).toBe(true)
    expect(wrapper.find('img[alt="drone-map.png"]').exists()).toBe(false)

    await wrapper.find('[data-testid="docx-filter-text"]').trigger('click')
    await wrapper.find('[data-testid="docx-diff-search"]').setValue('无人机')
    expect(wrapper.text()).toContain('新增无人机施肥策略')
    expect(wrapper.text()).not.toContain('删除旧版作物描述')
    expect(wrapper.find('.search-hit').exists()).toBe(true)
  })

  it('filters operation-specific changes including move, replace, and resize', async () => {
    const wrapper = mount(DocxDiffView, {
      global,
      props: {
        diffData: {
          paragraphs: [
            { change_type: 'move', old_text: '移动段落', new_text: '移动段落', metadata: { from: 0, to: 2 } },
            { change_type: 'insert', new_text: '新增段落' }
          ],
          tables: [
            {
              table_index: 0,
              old_rows: [['A']],
              new_rows: [['B']],
              cell_changes: [{ row: 0, col: 0, old_value: 'A', new_value: 'B', change_type: 'replace' }]
            }
          ],
          images: {
            resized: [
              {
                filename: 'logo.png',
                old_width_cm: 1,
                old_height_cm: 1,
                new_width_cm: 2,
                new_height_cm: 2,
                new: { display_name: 'logo.png', data_uri: dataUri }
              }
            ]
          }
        }
      }
    })

    await wrapper.find('[data-testid="docx-filter-move"]').trigger('click')
    expect(wrapper.text()).toContain('移动段落')
    expect(wrapper.text()).not.toContain('新增段落')

    await wrapper.find('[data-testid="docx-filter-replace"]').trigger('click')
    expect(wrapper.find('.excel-cell--replace').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('移动段落')

    await wrapper.find('[data-testid="docx-filter-resize"]').trigger('click')
    expect(wrapper.text()).toContain('尺寸调整')
    expect(wrapper.find('img[alt="logo.png"]').exists()).toBe(true)
    expect(wrapper.find('.excel-diff-table').exists()).toBe(false)
  })

  it('renders large paragraph diffs in chunks and can load more', async () => {
    const paragraphs = Array.from({ length: 350 }, (_, index) => ({
      change_type: 'insert',
      new_text: `新增段落 ${index + 1}`
    }))

    const wrapper = mount(DocxDiffView, {
      global,
      props: {
        diffData: {
          paragraphs,
          tables: [],
          images: {}
        }
      }
    })

    expect(wrapper.findAll('.diff-line')).toHaveLength(600)
    expect(wrapper.text()).toContain('再显示 50 段')

    await wrapper.find('[data-testid="docx-load-more"]').trigger('click')
    expect(wrapper.findAll('.diff-line')).toHaveLength(700)
    expect(wrapper.text()).not.toContain('再显示 50 段')
  })
})
