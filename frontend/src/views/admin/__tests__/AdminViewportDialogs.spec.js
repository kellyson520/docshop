import fs from 'node:fs'

function readSource(relativePath) {
  return fs.readFileSync(new URL(relativePath, import.meta.url), 'utf-8')
}

function countToken(source, token) {
  return source.split(token).length - 1
}

describe('admin viewport dialog regressions', () => {
  it('applies the shared viewport dialog contract across affected admin pages', () => {
    const projectList = readSource('../ProjectList.vue')
    expect(projectList).toContain("import { ADMIN_VIEWPORT_DIALOG_PROPS } from '@/utils/adminDialog'")
    expect(countToken(projectList, 'v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"')).toBe(1)

    const tokenManager = readSource('../TokenManager.vue')
    expect(tokenManager).toContain("import { ADMIN_VIEWPORT_DIALOG_PROPS } from '@/utils/adminDialog'")
    expect(countToken(tokenManager, 'v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"')).toBe(4)

    const trackingDashboard = readSource('../TrackingDashboard.vue')
    expect(trackingDashboard).toContain("import { ADMIN_VIEWPORT_DIALOG_PROPS } from '@/utils/adminDialog'")
    expect(countToken(trackingDashboard, 'v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"')).toBe(2)

    const projectDetail = readSource('../ProjectDetail.vue')
    expect(projectDetail).toContain("import { ADMIN_VIEWPORT_DIALOG_PROPS } from '@/utils/adminDialog'")
    expect(countToken(projectDetail, 'v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"')).toBeGreaterThanOrEqual(5)

    const cardManage = readSource('../CardManage.vue')
    expect(cardManage).toContain("import { ADMIN_VIEWPORT_DIALOG_PROPS } from '@/utils/adminDialog'")
    expect(countToken(cardManage, 'v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"')).toBe(3)

    const announcementManager = readSource('../AnnouncementManager.vue')
    expect(announcementManager).toContain("import { ADMIN_VIEWPORT_DIALOG_PROPS } from '@/utils/adminDialog'")
    expect(countToken(announcementManager, 'v-bind="ADMIN_VIEWPORT_DIALOG_PROPS"')).toBe(1)
  })

  it('defines reusable viewport dialog body sizing rules in global styles', () => {
    const styleSource = readSource('../../../style.css')
    expect(styleSource).toContain('.admin-viewport-dialog')
    expect(styleSource).toContain('.admin-viewport-dialog .el-dialog__body')
  })
})
