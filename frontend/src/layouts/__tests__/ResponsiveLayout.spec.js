import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('ResponsiveLayout mobile bottom navigation', () => {
  it('binds bottom navigation icons to imported icon refs instead of unresolved string names', () => {
    const source = readFileSync(resolve(__dirname, '../ResponsiveLayout.vue'), 'utf-8')

    expect(source).toContain("icon: HomeFilled")
    expect(source).toContain("icon: Files")
    expect(source).toContain("icon: Calendar")
    expect(source).toContain("icon: Setting")
    expect(source).not.toContain("icon: 'HomeFilled'")
    expect(source).not.toContain("icon: 'Files'")
    expect(source).not.toContain("icon: 'Calendar'")
    expect(source).not.toContain("icon: 'Setting'")
  })
})
