import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import HtmlDiffView from '../HtmlDiffView.vue'

function mountView(diffData) {
  return mount(HtmlDiffView, {
    props: { diffData },
  })
}

describe('HtmlDiffView', () => {
  it('renders semantic html diff sections and escapes snippets', async () => {
    const wrapper = mountView({
      stats: {
        text_modified: 1,
        nodes_added: 1,
        nodes_deleted: 0,
        nodes_moved: 1,
        attributes_changed: 1,
        resources_changed: 1,
        tables_changed: 1,
        total_changes: 6,
      },
      text: [{
        change_type: 'modified',
        tag: 'p',
        path: 'document/html[1]/body[1]/p[1]',
        old_text: 'Hello',
        new_text: '<img src=x onerror=alert(1)>Hello world',
      }],
      nodes: [{
        change_type: 'moved',
        tag: 'li',
        old_path: 'document/html[1]/body[1]/ul[1]/li[2]',
        new_path: 'document/html[1]/body[1]/ul[1]/li[1]',
        text: 'Second',
      }],
      attributes: [{
        change_type: 'attribute_changed',
        tag: 'p',
        path: 'document/html[1]/body[1]/p[1]',
        attribute: 'class',
        old_value: 'lead',
        new_value: 'lead strong',
      }],
      resources: [{
        change_type: 'resource_changed',
        tag: 'img',
        path: 'document/html[1]/body[1]/img[1]',
        attribute: 'src',
        old_value: '/old.png',
        new_value: '/new.png',
      }],
      tables: [{
        change_type: 'modified',
        tag: 'tr',
        path: 'document/html[1]/body[1]/table[1]/tr[2]',
        old_text: 'Basic 10',
        new_text: 'Basic 12',
      }],
      payload: {
        old_preview_url: '/old-preview',
        new_preview_url: '/new-preview',
      },
    })

    expect(wrapper.text()).toContain('HTML 语义对比')
    expect(wrapper.text()).toContain('文本')
    expect(wrapper.text()).toContain('结构')
    expect(wrapper.text()).toContain('属性')
    expect(wrapper.text()).toContain('资源')
    expect(wrapper.text()).toContain('表格')
    expect(wrapper.html()).not.toContain('<img src=x onerror=alert(1)>')
    expect(wrapper.text()).toContain('<img src=x onerror=alert(1)>Hello world')

    const frames = wrapper.findAll('iframe.html-diff-view__frame')
    expect(frames).toHaveLength(2)
    expect(frames[0].attributes('src')).toBe('/old-preview')
    expect(frames[1].attributes('src')).toBe('/new-preview')

    await wrapper.find('[data-testid="html-diff-filter-resources"]').trigger('click')
    expect(wrapper.text()).toContain('/old.png')
    expect(wrapper.text()).toContain('/new.png')
    expect(wrapper.text()).not.toContain('Basic 12')
  })
})
