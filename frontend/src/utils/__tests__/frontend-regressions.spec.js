
import { describe, it, expect, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

vi.mock('element-plus', () => ({
  ElMessage: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn()
  }
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ logout: vi.fn() })
}))

const frontendRoot = process.cwd()
const readSource = (relativePath) => readFileSync(resolve(frontendRoot, relativePath), 'utf-8')

describe('frontend issue regression guards', () => {
  it('UserProfile clears the verification-code countdown interval on unmount', () => {
    const source = readSource('src/views/user/UserProfile.vue')

    expect(source).toMatch(/onUnmounted/)
    expect(source).toMatch(/(code|countdown).*Timer/i)
    expect(source).toMatch(/onUnmounted\(\(\) => \{[\s\S]*clearCountdownTimer[\s\S]*\}\)/)
    expect(source).toMatch(/function clearCountdownTimer\(\) \{[\s\S]*clearInterval[\s\S]*\}/)
  })

  it('HomePage clears pending search debounce timeout on unmount', () => {
    const source = readSource('src/views/HomePage.vue')

    expect(source).toMatch(/onUnmounted/)
    expect(source).toMatch(/onUnmounted\(\(\) => \{[\s\S]*clearSearchTimer[\s\S]*\}\)/)
    expect(source).toMatch(/function clearSearchTimer\(\) \{[\s\S]*clearTimeout[\s\S]*\}/)
  })

  it('TokenManager toggles token state only after the API succeeds and handles failures', () => {
    const source = readSource('src/views/admin/TokenManager.vue')
    const toggleStart = source.indexOf('async function toggleToken')
    const toggleEnd = source.indexOf('async function regenerateToken', toggleStart + 1)
    const toggleBody = source.slice(toggleStart, toggleEnd)

    expect(toggleBody).toMatch(/try/)
    expect(toggleBody).toMatch(/catch/)
    expect(toggleBody.indexOf('await put')).toBeGreaterThanOrEqual(0)
    expect(toggleBody.indexOf('row.is_active = next')).toBeGreaterThan(toggleBody.indexOf('await put'))
    expect(toggleBody).toMatch(/ElMessage\.error/)
  })

  it('TokenManager keeps readable labels and copyable access-link logic for site access tokens', () => {
    const source = readSource('src/views/admin/TokenManager.vue')
    const layout = readSource('src/layouts/ResponsiveLayout.vue')

    expect(source).not.toContain('????')
    expect(layout).not.toContain('????')
    expect(source).toContain('name="sharePolicy"')
    expect(layout).toMatch(/index="\/admin\/tokens"/)
    expect(source).toMatch(/function accessLink\(token\)/)
    expect(source).toMatch(/function copyAccessLink\(row\)/)
    expect(source).not.toContain(':disabled="!row.token" @click="copyAccessLink(row)"')
    expect(source).toMatch(/get\(`\/access-tokens\/\$\{row\.id\}`\)/)
    expect(source).toMatch(/copyToClipboard\(accessLink\(token\)\)/)
    expect(source).toContain('name="shareTokens"')
  })

  it('TokenManager lazy-loads non-default tabs and restores the share-token management tab', () => {
    const source = readSource('src/views/admin/TokenManager.vue')

    expect(source).toContain('name="users" lazy')
    expect(source).toContain('name="tokens" lazy')
    expect(source).toContain('name="shareTokens" lazy')
    expect(source).toContain('name="sharePolicy" lazy')
    expect(source).toMatch(/fetchShareTokens\(/)
    expect(source).toMatch(/if \(tab === 'shareTokens' && !shareTokensLoaded\.value\) await fetchShareTokens\(\)/)
    expect(source).toMatch(/onMounted\(\(\) => \{[\s\S]*fetchRegistrationSwitch\(\)[\s\S]*fetchUsers\(\)[\s\S]*\}\)/)
    expect(source).not.toMatch(/onMounted\(\(\) => \{[\s\S]*fetchTokens\(\)/)
    expect(source).not.toMatch(/onMounted\(\(\) => \{[\s\S]*fetchShareTokens\(\)/)
    expect(source).not.toMatch(/onMounted\(\(\) => \{[\s\S]*fetchSharePolicy\(\)/)
  })

  it('ProjectDetail removes the share-link display block but keeps the share-project action', () => {
    const source = readSource('src/views/admin/ProjectDetail.vue')

    expect(source).not.toContain('分享链接:')
    expect(source).not.toMatch(/class="share-section"/)
    expect(source).toContain('分享项目')
    expect(source).toMatch(/openShareDialog\('project'\)/)
  })

  it('UserActivities loads real API data and revokes export blob URLs', () => {
    const source = readSource('src/views/user/UserActivities.vue')

    expect(source).not.toMatch(/mockActivities/)
    expect(source).not.toMatch(/setTimeout\(\(\) => \{[\s\S]*activities\.value/)
    expect(source).toMatch(/import \{ get \} from ['"]@\/api\/client['"]/) 
    expect(source).toMatch(/async function loadActivities/)
    expect(source).toMatch(/await get\(/)
    expect(source).toMatch(/URL\.createObjectURL/)
    expect(source).toMatch(/URL\.revokeObjectURL/)
  })

  it('AdminSettings surfaces security load errors and saves only canonical security fields', () => {
    const source = readSource('src/views/admin/AdminSettings.vue')

    expect(source).not.toContain('catch { /* ignore */ }')
    expect(source).toContain('请求限速')
    expect(source).not.toContain('API 限速')
    expect(source).not.toMatch(/rate_api:\s*1000/)
    expect(source).not.toMatch(/securityConfig\.rate_api\s*=\s*data\.rate_api/)
    expect(source).not.toMatch(/rate_api:\s*securityConfig\.rate_api/)
    expect(source).toMatch(/rate_upload:\s*securityConfig\.rate_upload/)
    expect(source).toMatch(/cors_origins:\s*parseCommaList\(securityConfig\.cors_origins_str\)/)
    expect(source).toMatch(/file_types:\s*parseCommaList\(securityConfig\.file_types_str\)/)
    expect(source).not.toMatch(/await put\('\/settings',[\s\S]*cors_origins_str:/)
    expect(source).not.toMatch(/await put\('\/settings',[\s\S]*file_types_str:/)
  })

  it('AdminSettings catches save-profile and change-password failures with user feedback', () => {
    const source = readSource('src/views/admin/AdminSettings.vue')
    const saveStart = source.indexOf('async function handleSaveProfile')
    const saveEnd = source.indexOf('/**', saveStart + 1)
    const saveProfile = source.slice(saveStart, saveEnd)
    const changeStart = source.indexOf('async function handleChangePassword')
    const changeEnd = source.indexOf('/**', changeStart + 1)
    const changePassword = source.slice(changeStart, changeEnd)

    expect(saveProfile).toMatch(/catch \(error\)/)
    expect(saveProfile).toMatch(/showError|ElMessage\.error/)
    expect(changePassword).toMatch(/catch \(error\)/)
    expect(changePassword).toMatch(/showError|ElMessage\.error/)
  })

  it('AdminDashboard upcoming exams uses the exam list endpoint instead of one-shot reminder triggers', () => {
    const source = readSource('src/views/admin/AdminDashboard.vue')

    expect(source).toContain("import { getProjects } from '@/api/project'")
    expect(source).toContain("import { getExams } from '@/api/exam'")
    expect(source).not.toContain('getUpcomingExams')
    expect(source).toMatch(/getExams\(\{\s*status:\s*'upcoming'[\s\S]*page_size:\s*100/)
  })

  it('AdminDashboard auto-refreshes upcoming exam data and clears timers on unmount', () => {
    const source = readSource('src/views/admin/AdminDashboard.vue')

    expect(source).toContain('onUnmounted')
    expect(source).toContain('DASHBOARD_EXAM_REFRESH_MS')
    expect(source).toMatch(/function refreshUpcomingExamData\(\)/)
    expect(source).toMatch(/function startDashboardAutoRefresh\(\) \{[\s\S]*setInterval\(\(\) => \{[\s\S]*refreshUpcomingExamData\(\)/)
    expect(source).toMatch(/function stopDashboardAutoRefresh\(\) \{[\s\S]*clearInterval\(dashboardRefreshTimer\)/)
    expect(source).toMatch(/document\.addEventListener\('visibilitychange',\s*handleDashboardVisibilityChange\)/)
    expect(source).toMatch(/document\.removeEventListener\('visibilitychange',\s*handleDashboardVisibilityChange\)/)
    expect(source).toMatch(/onUnmounted\(\(\) => \{[\s\S]*stopDashboardAutoRefresh\(\)[\s\S]*\}\)/)
  })

  it('HomePage auto-refreshes public exams and clears the exam timer on unmount', () => {
    const source = readSource('src/views/HomePage.vue')

    expect(source).toContain('PUBLIC_EXAM_REFRESH_MS')
    expect(source).toMatch(/let examRefreshTimer = null/)
    expect(source).toMatch(/function startExamRefreshTimer\(\) \{[\s\S]*setInterval\(\(\) => \{[\s\S]*fetchExams\(\)/)
    expect(source).toMatch(/function clearExamRefreshTimer\(\) \{[\s\S]*clearInterval\(examRefreshTimer\)/)
    expect(source).toMatch(/document\.addEventListener\('visibilitychange',\s*handleExamVisibilityChange\)/)
    expect(source).toMatch(/document\.removeEventListener\('visibilitychange',\s*handleExamVisibilityChange\)/)
    expect(source).toMatch(/onUnmounted\(\(\) => \{[\s\S]*clearSearchTimer\(\)[\s\S]*clearExamRefreshTimer\(\)[\s\S]*\}\)/)
  })

  it('rank pages show user-facing error feedback when API calls fail', () => {
    for (const file of ['src/views/admin/RankDownload.vue', 'src/views/admin/RankVisit.vue']) {
      const source = readSource(file)
      expect(source).toMatch(/ElMessage/)
      expect(source).toMatch(/catch \(error\) \{[\s\S]*ElMessage\.error/)
    }
  })

  it('NotFound does not send unauthenticated users to /admin by default', () => {
    const source = readSource('src/views/NotFound.vue')

    expect(source).not.toContain("router.push('/admin')")
    expect(source).toMatch(/router\.push\(target\)|router\.push\('\/'\)/)
  })

  it('mobile navigation exposes the announcements management route', () => {
    const source = readSource('src/layouts/ResponsiveLayout.vue')

    const matches = source.match(/index="\/admin\/announcements"/g) || []
    expect(matches.length).toBeGreaterThanOrEqual(2)
  })

  it('AnnouncementManager edit dialog is appended to body and scroll-safe', () => {
    const source = readSource('src/views/admin/AnnouncementManager.vue')

    expect(source).toMatch(/<el-dialog[\s\S]*append-to-body/)
    expect(source).toMatch(/<el-dialog[\s\S]*class="announcement-dialog"/)
    expect(source).toMatch(/body-class="announcement-dialog__body"|class="announcement-editor"/)
    expect(source).toMatch(/(\.announcement-dialog__body|\.announcement-editor)[\s\S]*max-height:\s*calc\(100vh - 220px\)/)
    expect(source).toMatch(/(\.announcement-dialog__body|\.announcement-editor)[\s\S]*overflow-y:\s*auto/)
  })

  it('TrackingDashboard uses tracking display helpers without fetching MobileModels CSV directly', () => {
    const source = readSource('src/views/admin/TrackingDashboard.vue')

    expect(source).toContain('formatDevicePrimary')
    expect(source).not.toMatch(/MobileModels|models\.csv|mobile_models\.csv/)
  })

  it('TrackingDashboard CSV export revokes object URLs in finally and tolerates DOM cleanup failures', () => {
    const source = readSource('src/views/admin/TrackingDashboard.vue')

    expect(source).toMatch(/const urlApi = window\.URL \|\| URL/)
    expect(source).toMatch(/urlApi\.createObjectURL\(blob\)/)
    expect(source).toMatch(/try \{[\s\S]*link\.click\(\)[\s\S]*\} finally \{[\s\S]*urlApi\.revokeObjectURL\(url\)/)
    expect(source).toMatch(/try \{[\s\S]*document\.body\.removeChild\(link\)[\s\S]*\} catch/)
  })

  it('TrackingDashboard renders monitoring sections as clickable modules while preserving logs table', () => {
    const source = readSource('src/views/admin/TrackingDashboard.vue')
    const logsTableStart = source.indexOf('<el-table :data="logRows"')
    const logsTableEnd = source.indexOf('</el-table>', logsTableStart)
    const logsTable = logsTableStart >= 0 && logsTableEnd >= 0
      ? source.slice(logsTableStart, logsTableEnd)
      : source

    expect(source).toContain('class="tracking-module-grid"')
    expect(source).toContain('class="tracking-module-card"')
    expect(source).toContain('openTrackingModule(module.key)')
    expect(source).toContain('trackingModuleDialogVisible')
    expect(source).toContain('activeTrackingModule')
    expect(source).toContain('class="tracking-module-dialog"')
    expect(logsTable).toContain('class="logs-table"')
    expect(logsTable).toContain('openAccessInfoDialog(row)')
    expect(logsTable).toContain('label="访问信息"')
  })

  it('TrackingDashboard keeps the merged access-info card/dialog and avoids legacy os/browser columns', () => {
    const source = readSource('src/views/admin/TrackingDashboard.vue')
    const logsTableStart = source.indexOf('<el-table :data="logRows"')
    const logsTableEnd = source.indexOf('</el-table>', logsTableStart)
    const logsTable = logsTableStart >= 0 && logsTableEnd >= 0
      ? source.slice(logsTableStart, logsTableEnd)
      : source

    expect(source).toContain('label="访问信息"')
    expect(source).toContain('class="tracking-info-card"')
    expect(source).toContain('openAccessInfoDialog(row)')
    expect(source).toContain('title="访问信息详情"')
    expect(source).toContain('技术详情')
    expect(source).toContain('selectedAccessInfoTechnicalDetails')
    expect(logsTable).toContain('label="访问信息"')
    expect(logsTable).not.toMatch(/label="操作系统"|label="浏览器"|prop="os_name"|prop="browser_name"/)
    expect(source).not.toMatch(/<el-table-column[^>]+prop="os_name"[\s\S]*<el-table-column[^>]+prop="browser_name"/)
  })

  it('TrackingDashboard renders visitor_ip_context enrichment separate from base access log fields', () => {
    const source = readSource('src/views/admin/TrackingDashboard.vue')

    expect(source).toContain('visitor_ip_context')
    expect(source).toContain('buildVisitorIpContextDetails')
    expect(source).toContain('selectedAccessInfoVisitorContextDetails')
    expect(source).toContain('visitorIpSummary')
    expect(source).not.toContain('server_ip_context')
  })

  it('global workspace skin does not force every logo text to near-white', () => {
    const source = readSource('src/style.css')

    expect(source).not.toMatch(/(^|\n)\.logo-text,\s*\n\.layout-sidebar\s+\.username\s*\{[\s\S]*color:\s*#f8fafc\s*!important/i)
    expect(source).toMatch(/\.layout-sidebar\s+\.logo-text,\s*\n\.layout-sidebar\s+\.username\s*\{[\s\S]*color:\s*#f8fafc\s*!important/i)
  })

  it('low-cost motion polish uses CSS-only transform/opacity animations and respects reduced motion', () => {
    const source = readSource('src/style.css')

    expect(source).toContain('DocShop low-cost motion polish')
    expect(source).toContain('@keyframes docshop-rise')
    expect(source).toMatch(/transform:\s*translate3d\(0,\s*-2px,\s*0\)\s*!important/)
    expect(source).toMatch(/\.el-button:not\(\.is-disabled\):active[\s\S]*translate3d\(0,\s*1px,\s*0\)/)
    expect(source).toMatch(/@media \(prefers-reduced-motion:\s*reduce\)[\s\S]*animation-duration:\s*1ms\s*!important/)
    expect(source).not.toMatch(/framer-motion|@vueuse\/motion/i)
  })

  it('route transitions are unified and GPU-friendly', () => {
    const app = readSource('src/App.vue')
    const responsiveLayout = readSource('src/layouts/ResponsiveLayout.vue')
    const publicLayout = readSource('src/layouts/PublicLayout.vue')
    const style = readSource('src/style.css')

    expect(app).toContain('<transition name="docshop-route" mode="out-in" appear>')
    expect(responsiveLayout).toContain('<transition name="fade-slide" mode="out-in" appear>')
    expect(publicLayout).toContain('<transition name="fade-slide" mode="out-in" appear>')
    expect(style).toContain('.docshop-route-enter-active')
    expect(style).toMatch(/\.docshop-route-enter-from,[\s\S]*opacity:\s*0[\s\S]*translate3d\(0,\s*10px,\s*0\)/)
    expect(style).toMatch(/\.fade-slide-enter-from,[\s\S]*opacity:\s*0[\s\S]*translate3d\(0,\s*8px,\s*0\)/)
  })

  it('global motion polish covers overlays, tables, progress, uploads and loading states', () => {
    const source = readSource('src/style.css')

    expect(source).toContain('--motion-ui-slow')
    expect(source).toContain('--motion-ui-soft')
    expect(source).toContain('@keyframes docshop-breathe')
    expect(source).toContain('@keyframes docshop-pop')
    expect(source).toMatch(/\.el-overlay-dialog,[\s\S]*\.el-dialog,[\s\S]*\.el-drawer/)
    expect(source).toMatch(/\.el-table__row[\s\S]*transition:[\s\S]*background-color[\s\S]*box-shadow/)
    expect(source).toMatch(/\.el-progress-bar__inner[\s\S]*transition:[\s\S]*width/)
    expect(source).toMatch(/\.el-upload-dragger[\s\S]*transition:[\s\S]*border-color[\s\S]*box-shadow[\s\S]*transform/)
    expect(source).toMatch(/\.el-loading-spinner[\s\S]*animation:\s*docshop-breathe/)
    expect(source).toMatch(/will-change:\s*transform,\s*opacity/)
  })

  it('GSAP is used only as a lazy-loaded accent layer with cleanup and reduced-motion support', () => {
    const packageJson = JSON.parse(readSource('package.json'))
    const motion = readSource('src/composables/useGsapMotion.js')
    const dashboard = readSource('src/views/admin/AdminDashboard.vue')

    expect(packageJson.dependencies.gsap).toBeTruthy()
    expect(motion).toContain("await import('gsap')")
    expect(motion).toContain('prefers-reduced-motion: reduce')
    expect(motion).toMatch(/gsap\.context/)
    expect(motion).toMatch(/ctx\?\.revert\(\)/)
    expect(motion).not.toMatch(/ScrollTrigger/)
    expect(dashboard).toContain('ref="dashboardRoot"')
    expect(dashboard).toContain('useGsapScoped')
    expect(dashboard).toContain('data-count-to')
    expect(dashboard).toContain('playDashboardIntro')
  })

  it('motion preference can be adjusted from settings and applied globally', () => {
    const app = readSource('src/App.vue')
    const settingsStore = readSource('src/stores/settings.js')
    const adminSettings = readSource('src/views/admin/AdminSettings.vue')
    const motionPreference = readSource('src/utils/motionPreference.js')
    const style = readSource('src/style.css')

    expect(app).toContain('initMotionPreference')
    expect(app).toContain('bindMotionPreferenceSync')
    expect(app).toContain('onBeforeUnmount')
    expect(settingsStore).toContain("motion_mode: 'system'")
    expect(settingsStore).toContain('applyMotionPreference')
    expect(adminSettings).toContain('motion-mode-select')
    expect(adminSettings).toContain('handleMotionModeChange')
    expect(adminSettings).toContain('motion_mode')
    expect(motionPreference).toContain('MOTION_STORAGE_KEY')
    expect(motionPreference).toContain('docshop_motion_mode')
    expect(motionPreference).toContain('data-motion-mode')
    expect(motionPreference).toContain('bindMotionPreferenceSync')
    expect(motionPreference).toContain('storage')
    expect(style).toContain('DocShop motion iteration v2')
    expect(style).toMatch(/html\[data-motion-mode="off"\][\s\S]*animation-duration:\s*1ms\s*!important/)
    expect(style).toMatch(/html\[data-motion-mode="reduced"\][\s\S]*--motion-ui-base:\s*120ms/)
  })

  it('motion iteration v2 improves key page feedback without static GSAP imports', () => {
    const style = readSource('src/style.css')
    const files = [
      'src/composables/useGsapMotion.js',
      'src/views/admin/AdminDashboard.vue',
      'src/views/HomePage.vue',
      'src/views/LoginView.vue',
      'src/views/admin/ProjectList.vue',
      'src/views/share/ShareProject.vue'
    ]

    expect(style).toContain('@keyframes docshop-button-sheen')
    expect(style).toMatch(/\.el-button\.is-loading[\s\S]*overflow:\s*hidden/)
    expect(style).toMatch(/\.motion-field[\s\S]*\.el-input__wrapper/)
    expect(style).toMatch(/\.motion-empty[\s\S]*\.el-empty__image/)
    expect(readSource('src/views/LoginView.vue')).toContain('motion-page--login')
    expect(readSource('src/views/HomePage.vue')).toContain('motion-page--catalog')
    expect(readSource('src/views/admin/ProjectList.vue')).toContain('motion-page--projects')
    expect(readSource('src/views/admin/AdminSettings.vue')).toContain('motion-page--settings')
    expect(readSource('src/views/share/ShareProject.vue')).toContain('motion-page--share')

    for (const file of files) {
      const source = readSource(file)
      expect(source, file).not.toMatch(/^import\s+.*['"]gsap['"]/m)
      expect(source, file).not.toMatch(/from\s+['"]gsap['"]/)
    }
  })

  it('route navigation exposes a lightweight CSS-only top progress indicator', () => {
    const router = readSource('src/router/index.js')
    const routeProgress = readSource('src/utils/routeProgress.js')
    const style = readSource('src/style.css')

    expect(router).toContain('startRouteProgress')
    expect(router).toContain('finishRouteProgress')
    expect(router).toContain('resetRouteProgress')
    expect(routeProgress).toContain('data-route-progress')
    expect(routeProgress).toContain('setRouteProgressState')
    expect(style).toContain('DocShop route progress feedback')
    expect(style).toContain('data-route-progress="loading"')
    expect(style).toContain('@keyframes docshop-route-progress-pulse')
  })

  it('NotFound is a friendly error page without forced auto-redirect', () => {
    const source = readSource('src/views/NotFound.vue')

    expect(source).toContain('not-found-illustration')
    expect(source).toContain('currentPath')
    expect(source).toContain('返回上一页')
    expect(source).toContain('回到首页')
    expect(source).not.toMatch(/setInterval|countdown|自动跳转/)
  })

  it('AccessDenied and ErrorBoundary use readable copy and safe Vite dev checks', () => {
    const accessDenied = readSource('src/views/AccessDenied.vue')
    const boundary = readSource('src/components/common/ErrorBoundary.vue')

    expect(accessDenied).not.toContain('????')
    expect(accessDenied).toContain('当前访问未通过门禁')
    expect(accessDenied).toContain('@media (prefers-reduced-motion: reduce)')
    expect(boundary).not.toContain('process.env.NODE_ENV')
    expect(boundary).toContain('import.meta.env.DEV')
    expect(boundary).toContain('error-boundary__mascot')
  })

  it('AccessDenied only accepts internal redirect targets', () => {
    const source = readSource('src/views/AccessDenied.vue')

    expect(source).toMatch(/function safeRedirectTarget\(/)
    expect(source).toMatch(/\/\^\\\/\[\^\\\/\]\//)
    expect(source).not.toContain('return typeof value === \'string\' && value ? value : \'/\'')
    expect(source).not.toContain('router.replace(redirectTarget.value)')
  })

  it('HTML fallback downloads do not inject blob content with document.write', () => {
    const source = readSource('src/utils/index.js')

    expect(source).not.toContain('document.write')
    expect(source).toMatch(/URL\.createObjectURL\(blob\)/)
    expect(source).toMatch(/window\.open\(url,\s*'_blank'/)
    expect(source).toMatch(/URL\.revokeObjectURL\(url\)/)
  })

  it('ShareProject source keeps canonical closed-download copy without UTF-8 BOM', () => {
    const files = [
      'src/components/common/AnnouncementBar.vue',
      'src/views/admin/ProjectDetail.vue',
      'src/views/share/ShareFile.vue',
      'src/views/share/ShareProject.vue'
    ]

    for (const file of files) {
      expect(readSource(file), file).not.toContain('????')
    }

    expect(readSource('src/views/share/ShareFile.vue')).toContain('禁止下载')
    const shareProjectSource = readSource('src/views/share/ShareProject.vue')
    expect(shareProjectSource.charCodeAt(0)).not.toBe(0xfeff)
    expect(shareProjectSource).toContain('当前分享未开放下载')
    expect(shareProjectSource).toContain('禁止下载')
    expect(readSource('src/components/common/AnnouncementBar.vue')).toContain('我知道了')
  })

  it('ExamReminder surfaces upcoming/start exam check failures instead of only logging', () => {
    const source = readSource('src/components/exam/ExamReminder.vue')

    expect(source).toMatch(/error:\s*showError/)
    expect(source).toMatch(/catch \(error\) \{[\s\S]*showError/)
  })

  it('download helpers release generated object URLs even when DOM cleanup fails', () => {
    const source = readSource('src/utils/index.js')
    const createCount = (source.match(/createObjectURL/g) || []).length
    const revokeCount = (source.match(/revokeObjectURL/g) || []).length

    expect(createCount).toBeGreaterThan(0)
    expect(revokeCount).toBeGreaterThanOrEqual(createCount)
    expect(source).toMatch(/try \{[\s\S]*removeChild\(a\)[\s\S]*\} finally \{[\s\S]*revokeObjectURL\(url\)/)
  })

  it('CardDetail releases generated download object URLs after triggering downloads', () => {
    const source = readSource('src/views/CardDetail.vue')

    expect(source).toMatch(/URL\.createObjectURL/)
    expect(source).toMatch(/try \{[\s\S]*a\.click\(\)[\s\S]*\} finally \{[\s\S]*URL\.revokeObjectURL\(url\)/)
  })

  it('ExamDialog supports custom segmented reminder offsets with legacy compatibility fields', () => {
    const source = readSource('src/components/exam/ExamDialog.vue')

    expect(source).not.toContain('????')
    expect(source).toContain('新增考试')
    expect(source).toContain('编辑考试')
    expect(source).toContain('考试名称')
    expect(source).toContain('所属项目')
    expect(source).toContain('开始时间')
    expect(source).toContain('结束时间')
    expect(source).toContain('考试说明')
    expect(source).toContain('提醒时间')
    expect(source).toContain('分段提醒')
    expect(source).toContain('添加提醒')
    expect(source).toContain('恢复默认')
    expect(source).toContain('保存考试')
    expect(source).toContain('reminder_offsets_minutes')
    for (const offset of ['5', '10', '15', '30', '60', '120', '1440', '0']) {
      expect(source).toContain(`value: ${offset}`)
    }
    expect(source).toMatch(/function addCustomReminder\(/)
    expect(source).toContain('REMINDER_MAX_DAYS')
    expect(source).toContain('reminderCustomMax')
    expect(source).not.toContain(':max="30"')
    expect(source).toMatch(/function removeReminderOffset\(/)
    expect(source).toMatch(/function normalizeReminderOffsets\(/)
    expect(source).toMatch(/reminder_15min:\s*form\.value\.reminder_offsets_minutes\.includes\(15\)\s*\?\s*1\s*:\s*0/)
    expect(source).toMatch(/reminder_5min:\s*form\.value\.reminder_offsets_minutes\.includes\(5\)\s*\?\s*1\s*:\s*0/)
    expect(source).toMatch(/reminder_start:\s*form\.value\.reminder_offsets_minutes\.includes\(0\)\s*\?\s*1\s*:\s*0/)
  })

  it('exam store reminder lead text uses readable Chinese labels', () => {
    const source = readSource('src/stores/exam.js')

    expect(source).not.toContain('????')
    expect(source).toContain('考试即将开始')
    expect(source).toContain('天后开始')
    expect(source).toContain('小时后开始')
    expect(source).toContain('分钟后开始')
  })


  it('ProjectList batch actions use isolated progress feedback and preserve failed selections', () => {
    const source = readSource('src/views/admin/ProjectList.vue')

    expect(source).toContain('runBatchOperation')
    expect(source).toContain('batchLoading')
    expect(source).toContain('batchProgress')
    expect(source).toContain('batch-action-progress')
    expect(source).toMatch(/:loading="batchLoading && batchAction === 'public'"/)
    expect(source).toMatch(/:disabled="batchLoading"/)
    expect(source).toMatch(/selectedProjects\.value = result\.failures\.map\(\(failure\) => failure\.item\)/)
    expect(source).not.toContain("for (const id of selectedProjects.value)")
  })


  it('ProjectDetail preview management shows detailed queue and storage diagnostics', () => {
    const source = readSource('src/views/admin/ProjectDetail.vue')

    expect(source).toContain('previewStorageBreakdown')
    expect(source).toContain('previewLargestFiles')
    expect(source).toContain('previewFileTypeStats')
    expect(source).toContain('previewQueueState')
    expect(source).toContain('preview-storage-breakdown')
    expect(source).toContain('preview-largest-files')
  })

  it('ProjectDetail supports project folders and moving files without changing file table behavior', () => {
    const viewSource = readSource('src/views/admin/ProjectDetail.vue')
    const apiSource = readSource('src/api/project.js')

    expect(apiSource).toContain('getProjectFolders')
    expect(apiSource).toContain('createProjectFolder')
    expect(apiSource).toContain('renameProjectFolder')
    expect(apiSource).toContain('deleteProjectFolder')
    expect(apiSource).toContain('moveProjectFileToFolder')
    expect(viewSource).toContain('resource-toolbar')
    expect(viewSource).toContain(':data="resourceItems"')
    expect(viewSource).toContain('currentFolderId')
    expect(viewSource).toContain('filteredFiles')
    expect(viewSource).toContain('openMoveFileDialog')
    expect(viewSource).toContain('moveFileDialogVisible')
    expect(viewSource).toContain('resource-folder-item-${row.resourceId}')
    expect(viewSource).toContain('resource-folder-item-${item.resourceId}')
    expect(viewSource).toContain('openFolder(row.resourceId)')
    expect(viewSource).not.toContain('folder-toolbar')
    expect(viewSource).not.toContain('folder-grid')
    expect(viewSource).not.toContain('folder-card')
    expect(viewSource).toContain('folder_id: currentFolderId.value')
    expect(viewSource).toContain('moveProjectFileToFolder')
  })

})

describe('ErrorHandler fetch-style error parsing', () => {
  it('maps fetch-style 401 errors to auth logout behavior', async () => {
    const { ErrorHandler, ErrorTypes } = await import('../error.js')
    const error = new Error('HTTP 401')
    error.status = 401
    error.data = { message: 'Session expired' }

    const info = ErrorHandler.parseError(error)

    expect(info.type).toBe(ErrorTypes.AUTH)
    expect(info.code).toBe(20002)
    expect(info.action).toBe('logout')
    expect(info.message).toBe('Session expired')
  })

  it('uses fetch-style response data codes for mapped validation errors', async () => {
    const { ErrorHandler, ErrorTypes } = await import('../error.js')
    const error = new Error('HTTP 422')
    error.status = 422
    error.data = { code: 40001, message: 'Invalid field' }

    const info = ErrorHandler.parseError(error)

    expect(info.type).toBe(ErrorTypes.VALIDATION)
    expect(info.code).toBe(40001)
    expect(info.message).toBe('Invalid field')
    expect(info.data).toEqual(error.data)
  })
})
