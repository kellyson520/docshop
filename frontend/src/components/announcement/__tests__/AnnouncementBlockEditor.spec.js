import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AnnouncementBlockEditor from '../AnnouncementBlockEditor.vue'

describe('AnnouncementBlockEditor', () => {
  it('adds a paragraph block and emits updated blocks', async () => {
    const wrapper = mount(AnnouncementBlockEditor, {
      props: {
        modelValue: [],
      },
    })

    await wrapper.get('[data-testid="add-block-paragraph"]').trigger('click')

    const events = wrapper.emitted('update:modelValue')
    expect(events).toBeTruthy()
    expect(events.at(-1)?.[0]).toEqual([
      expect.objectContaining({ type: 'paragraph' }),
    ])
  })
})
