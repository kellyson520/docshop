import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DiffSummary from '../DiffSummary.vue'

describe('DiffSummary', () => {
  it('shows table and image stats even when there are no paragraph hunks', () => {
    const wrapper = mount(DiffSummary, {
      props: {
        summary: '',
        paragraphs: [],
        tables: [{ table_index: 0 }, { table_index: 1 }],
        images: {
          added: 1,
          deleted: 1,
          replaced: 1,
          resized: 1
        },
        stats: {
          tables_changed: 2,
          images_added: 1,
          images_deleted: 1,
          images_replaced: 1,
          images_resized: 1
        }
      }
    })

    expect(wrapper.find('.diff-summary').exists()).toBe(true)
    expect(wrapper.text()).toContain('表格')
    expect(wrapper.text()).toContain('图片新增')
    expect(wrapper.text()).toContain('图片删除')
    expect(wrapper.text()).toContain('图片替换')
    expect(wrapper.text()).toContain('尺寸调整')
    expect(wrapper.text()).toContain('当前数据没有逐段明细')
  })

  it('shows normalized status and elapsed time metrics', () => {
    const wrapper = mount(DiffSummary, {
      props: {
        summary: '发现 3 处差异',
        status: 'completed',
        metadata: { elapsed_ms: 128, file_type: 'docx' },
        paragraphs: [{ change_type: 'insert', new_text: '新增' }],
        tables: [],
        images: {
          added: [{ filename: 'a.png' }],
          deleted: [],
          replaced: [],
          resized: []
        },
        stats: {
          text_changes: 1,
          image_added: 1,
          total_changes: 2
        }
      }
    })

    expect(wrapper.text()).toContain('状态 completed')
    expect(wrapper.text()).toContain('耗时 128 ms')
    expect(wrapper.text()).toContain('类型 docx')
    expect(wrapper.text()).toContain('图片新增')
  })
})
