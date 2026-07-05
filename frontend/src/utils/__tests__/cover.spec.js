import { describe, expect, it } from 'vitest'

import { resolveCoverUrl } from '../cover'

describe('resolveCoverUrl', () => {
  it('maps absolute filesystem cover paths to the public api route', () => {
    expect(resolveCoverUrl('C:\\docshop\\data\\covers\\card-1\\cover.png'))
      .toBe('/api/v1/covers/card-1/cover.png')
  })
})
