# Tracking Info Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the five tracking log columns for device/system/browser/location/environment with one clickable access-info card column that opens a detail dialog with both readable and technical fields.

**Architecture:** Keep formatting logic in `frontend/src/utils/trackingDisplay.js` and keep page interaction state in `frontend/src/views/admin/TrackingDashboard.vue`. Implement the merged column and dialog in the dashboard first; only extract child components if the template becomes unmanageably large during implementation.

**Tech Stack:** Vue 3, Element Plus, Vitest, Vue Test Utils

---

## File Structure

### Frontend

- Modify: `frontend/src/utils/trackingDisplay.js`
  - Add card-summary helpers and dialog-field builders.
  - Keep null/empty fallback rules centralized.
- Modify: `frontend/src/utils/__tests__/trackingDisplay.spec.js`
  - Add red-green coverage for card summaries and detail-field formatting.
- Modify: `frontend/src/views/admin/TrackingDashboard.vue`
  - Replace the five separate columns with one access-info card column.
  - Add card click handling and the access-info detail dialog.
- Modify: `frontend/src/views/admin/__tests__/TrackingDashboard.spec.js`
  - Verify merged card rendering, clickable interaction, and dialog details.
- Modify: `frontend/src/utils/__tests__/frontend-regressions.spec.js`
  - Add a guard that the dashboard keeps using tracking helpers and does not re-introduce raw five-column rendering.

---

### Task 1: Extend tracking display helpers for card summaries and dialog details

**Files:**
- Modify: `frontend/src/utils/trackingDisplay.js`
- Test: `frontend/src/utils/__tests__/trackingDisplay.spec.js`

- [ ] **Step 1: Write the failing tests for info-card summary helpers**

Add these tests to `frontend/src/utils/__tests__/trackingDisplay.spec.js`:

```javascript
import {
  buildTrackingInfoCard,
  buildTrackingTechnicalDetails,
} from '../trackingDisplay'

it('builds a standard tracking info card summary for a resolved mobile device', () => {
  const row = {
    device_type: 'mobile',
    device_display_name: 'Huawei P40 / ANA-AL00',
    os_name: 'Android',
    os_version: '14',
    browser_name: 'Chrome',
    browser_version: '124',
    ip_city: 'Beijing',
    ip_country: 'CN',
    client_timezone: 'Asia/Shanghai',
    client_language: 'zh-CN',
  }

  expect(buildTrackingInfoCard(row)).toEqual({
    title: 'Huawei P40 / ANA-AL00',
    deviceTypeText: '移动端',
    secondary: 'Android 14 · Chrome 124',
    location: 'Beijing, CN',
    environment: 'Asia/Shanghai · zh-CN',
  })
})

it('builds technical details with raw field preservation and dash fallback', () => {
  const row = {
    device_model_code: 'ANA-AL00',
    device_model_name: 'P40',
    user_agent: 'Mozilla/5.0 test',
    visitor_id: 'visitor-123',
  }

  expect(buildTrackingTechnicalDetails(row)).toEqual([
    { label: '型号代码', value: 'ANA-AL00' },
    { label: '型号名称', value: 'P40' },
    { label: '品牌名称', value: '-' },
    { label: '展示名称', value: '-' },
    { label: '屏幕分辨率', value: '-' },
    { label: '纬度', value: '-' },
    { label: '经度', value: '-' },
    { label: '定位精度', value: '-' },
    { label: '时区', value: '-' },
    { label: '语言', value: '-' },
    { label: 'User-Agent', value: 'Mozilla/5.0 test' },
    { label: '访客 ID', value: 'visitor-123' },
  ])
})
```

- [ ] **Step 2: Run the focused display-helper tests to confirm RED**

Run:

```powershell
cd frontend
npm test -- --run src/utils/__tests__/trackingDisplay.spec.js
```

Expected: FAIL because `buildTrackingInfoCard` and `buildTrackingTechnicalDetails` do not exist yet.

- [ ] **Step 3: Implement minimal summary/detail helper functions**

Add these exports to `frontend/src/utils/trackingDisplay.js` near the existing tracking formatting helpers:

```javascript
function withDash(value) {
  const text = normalizeText(value)
  return text || '-'
}

export function buildTrackingInfoCard(row = {}) {
  return {
    title: formatDevicePrimary(row),
    deviceTypeText: getDeviceTypeText(row.device_type),
    secondary: formatDeviceSecondary(row),
    location: formatGeoLocation(row),
    environment: formatClientEnvironment(row),
  }
}

export function buildTrackingTechnicalDetails(row = {}) {
  return [
    { label: '型号代码', value: withDash(row.device_model_code) },
    { label: '型号名称', value: withDash(row.device_model_name) },
    { label: '品牌名称', value: withDash(row.device_brand_name) },
    { label: '展示名称', value: withDash(row.device_display_name) },
    { label: '屏幕分辨率', value: withDash(row.screen_resolution) },
    { label: '纬度', value: withDash(row.geo_latitude) },
    { label: '经度', value: withDash(row.geo_longitude) },
    { label: '定位精度', value: withDash(row.geo_accuracy) },
    { label: '时区', value: withDash(row.client_timezone) },
    { label: '语言', value: withDash(row.client_language) },
    { label: 'User-Agent', value: withDash(row.user_agent) },
    { label: '访客 ID', value: withDash(row.visitor_id) },
  ]
}
```

- [ ] **Step 4: Re-run the display-helper tests to confirm GREEN**

Run:

```powershell
cd frontend
npm test -- --run src/utils/__tests__/trackingDisplay.spec.js
```

Expected: PASS.

- [ ] **Step 5: Commit the helper-layer change**

```bash
git add frontend/src/utils/trackingDisplay.js frontend/src/utils/__tests__/trackingDisplay.spec.js
git commit -m "feat: add tracking info card display helpers"
```

---

### Task 2: Replace five log columns with one clickable access-info card and dialog

**Files:**
- Modify: `frontend/src/views/admin/TrackingDashboard.vue`
- Test: `frontend/src/views/admin/__tests__/TrackingDashboard.spec.js`

- [ ] **Step 1: Write the failing dashboard interaction test**

Add this test to `frontend/src/views/admin/__tests__/TrackingDashboard.spec.js`:

```javascript
it('renders a merged access-info card column and opens a detail dialog on click', async () => {
  apiMock.getCalls.length = 0
  const wrapper = mount(TrackingDashboard, {
    global: {
      stubs: {
        PageHeader: { template: '<div><slot name="actions" /></div>' },
      },
      components: {
        ElRow: passthrough('ElRow'),
        ElCol: passthrough('ElCol'),
        ElCard,
        ElButton: passthrough('ElButton', 'button'),
        ElRadioGroup: passthrough('ElRadioGroup'),
        ElRadioButton: passthrough('ElRadioButton', 'button'),
        ElSelect: passthrough('ElSelect'),
        ElOption: passthrough('ElOption', 'option'),
        ElTag: passthrough('ElTag', 'span'),
        ElSwitch: passthrough('ElSwitch', 'input'),
        ElSlider: passthrough('ElSlider', 'input'),
        ElInput: passthrough('ElInput', 'input'),
        ElDatePicker: passthrough('ElDatePicker', 'input'),
        ElPagination: passthrough('ElPagination'),
        ElInputNumber: passthrough('ElInputNumber', 'input'),
        ElTable,
        ElTableColumn,
        ElDialog: defineComponent({
          name: 'ElDialog',
          props: ['modelValue'],
          emits: ['update:modelValue'],
          setup(props, { slots }) {
            return () => props.modelValue ? h('div', { class: 'el-dialog' }, slots.default?.()) : null
          },
        }),
        ElDescriptions: passthrough('ElDescriptions'),
        ElDescriptionsItem: passthrough('ElDescriptionsItem'),
        ElDivider: passthrough('ElDivider'),
      },
      directives: { loading: {} },
    },
  })

  await flushPromises()
  await flushPromises()

  expect(wrapper.text()).toContain('访问信息')
  expect(wrapper.text()).not.toContain('浏览器')
  expect(wrapper.find('.tracking-info-card').exists()).toBe(true)
  expect(wrapper.find('.tracking-info-card').text()).toContain('Windows PC')
  expect(wrapper.find('.tracking-info-card').text()).toContain('Windows · Edge 149')
  expect(wrapper.find('.tracking-info-card').text()).toContain('39.9042, 116.4074')
  expect(wrapper.find('.tracking-info-card').text()).toContain('Asia/Shanghai · zh-CN')

  await wrapper.find('.tracking-info-card').trigger('click')

  expect(wrapper.find('.el-dialog').exists()).toBe(true)
  expect(wrapper.text()).toContain('访问信息详情')
  expect(wrapper.text()).toContain('设备')
  expect(wrapper.text()).toContain('系统')
  expect(wrapper.text()).toContain('浏览器')
  expect(wrapper.text()).toContain('位置')
  expect(wrapper.text()).toContain('环境')
  expect(wrapper.text()).toContain('技术信息')
})
```

- [ ] **Step 2: Run the focused dashboard test to confirm RED**

Run:

```powershell
cd frontend
npm test -- --run src/views/admin/__tests__/TrackingDashboard.spec.js
```

Expected: FAIL because the table still renders separate columns and there is no detail dialog.

- [ ] **Step 3: Add minimal dashboard state and helper imports**

In `frontend/src/views/admin/TrackingDashboard.vue`, extend the tracking helper import and add local dialog state:

```javascript
import {
  buildTrackingInfoCard,
  buildTrackingTechnicalDetails,
  formatClientEnvironment,
  formatDevicePrimary,
  formatDeviceSecondary,
  formatDeviceTooltip,
  formatGeoLocation,
  formatTrackingBusiness,
  getDeviceTypeText,
  getDistributionLabel,
} from '@/utils/trackingDisplay'

const selectedAccessInfoLog = ref(null)
const accessInfoDialogVisible = ref(false)

function openAccessInfoDialog(row) {
  selectedAccessInfoLog.value = row
  accessInfoDialogVisible.value = true
}

const selectedAccessInfoCard = computed(() =>
  selectedAccessInfoLog.value ? buildTrackingInfoCard(selectedAccessInfoLog.value) : null,
)

const selectedAccessInfoTechnicalDetails = computed(() =>
  selectedAccessInfoLog.value ? buildTrackingTechnicalDetails(selectedAccessInfoLog.value) : [],
)
```

- [ ] **Step 4: Replace the five columns with one card column and dialog markup**

Replace the current device / system / browser / location / environment columns with one column using this structure:

```vue
<el-table-column label="访问信息" min-width="320" show-overflow-tooltip>
  <template #default="{ row }">
    <button
      type="button"
      class="tracking-info-card"
      :title="formatDeviceTooltip(row)"
      @click="openAccessInfoDialog(row)"
    >
      <div class="tracking-info-card__header">
        <el-tag size="small" :type="getDeviceTypeTag(row.device_type)">
          {{ buildTrackingInfoCard(row).deviceTypeText }}
        </el-tag>
        <strong class="tracking-info-card__title">{{ buildTrackingInfoCard(row).title }}</strong>
      </div>
      <div class="tracking-info-card__line">{{ buildTrackingInfoCard(row).secondary }}</div>
      <div class="tracking-info-card__line">{{ buildTrackingInfoCard(row).location }}</div>
      <div class="tracking-info-card__line">{{ buildTrackingInfoCard(row).environment }}</div>
    </button>
  </template>
</el-table-column>

<el-dialog v-model="accessInfoDialogVisible" title="访问信息详情" width="760px">
  <template v-if="selectedAccessInfoLog && selectedAccessInfoCard">
    <div class="tracking-info-dialog__hero">
      <el-tag size="small" :type="getDeviceTypeTag(selectedAccessInfoLog.device_type)">
        {{ selectedAccessInfoCard.deviceTypeText }}
      </el-tag>
      <strong>{{ selectedAccessInfoCard.title }}</strong>
      <span>{{ formatLogTimestamp(selectedAccessInfoLog.timestamp) }}</span>
    </div>

    <el-descriptions :column="2" border>
      <el-descriptions-item label="设备">{{ selectedAccessInfoCard.title }}</el-descriptions-item>
      <el-descriptions-item label="系统">{{ selectedAccessInfoLog.os_name || '-' }} {{ selectedAccessInfoLog.os_version || '' }}</el-descriptions-item>
      <el-descriptions-item label="浏览器">{{ selectedAccessInfoLog.browser_name || '-' }} {{ selectedAccessInfoLog.browser_version || '' }}</el-descriptions-item>
      <el-descriptions-item label="位置">{{ selectedAccessInfoCard.location }}</el-descriptions-item>
      <el-descriptions-item label="环境" :span="2">{{ selectedAccessInfoCard.environment }}</el-descriptions-item>
    </el-descriptions>

    <el-divider content-position="left">技术信息</el-divider>
    <el-descriptions :column="2" border>
      <el-descriptions-item
        v-for="item in selectedAccessInfoTechnicalDetails"
        :key="item.label"
        :label="item.label"
      >
        {{ item.value }}
      </el-descriptions-item>
    </el-descriptions>
  </template>
</el-dialog>
```

Also add minimal styles near the existing dashboard styles:

```css
.tracking-info-card {
  width: 100%;
  text-align: left;
  border: 1px solid var(--el-border-color-light);
  border-radius: 12px;
  padding: 12px;
  background: var(--el-bg-color-overlay);
  cursor: pointer;
}

.tracking-info-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 8px 20px rgba(64, 158, 255, 0.12);
}

.tracking-info-card__header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.tracking-info-card__line {
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}
```

- [ ] **Step 5: Re-run the focused dashboard test to confirm GREEN**

Run:

```powershell
cd frontend
npm test -- --run src/views/admin/__tests__/TrackingDashboard.spec.js
```

Expected: PASS.

- [ ] **Step 6: Commit the dashboard card/dialog change**

```bash
git add frontend/src/views/admin/TrackingDashboard.vue frontend/src/views/admin/__tests__/TrackingDashboard.spec.js
git commit -m "feat: merge tracking columns into access info card"
```

---

### Task 3: Add regression coverage and run final frontend verification

**Files:**
- Modify: `frontend/src/utils/__tests__/frontend-regressions.spec.js`
- Test: `frontend/src/utils/__tests__/trackingDisplay.spec.js`
- Test: `frontend/src/views/admin/__tests__/TrackingDashboard.spec.js`

- [ ] **Step 1: Write the failing regression guard for the merged card column**

Add this test to `frontend/src/utils/__tests__/frontend-regressions.spec.js`:

```javascript
it('TrackingDashboard keeps a merged access-info card column and detail dialog', () => {
  const source = readSource('src/views/admin/TrackingDashboard.vue')

  expect(source).toContain('label="访问信息"')
  expect(source).toContain('class="tracking-info-card"')
  expect(source).toContain('openAccessInfoDialog(row)')
  expect(source).toContain('title="访问信息详情"')
  expect(source).toContain('技术信息')
  expect(source).not.toMatch(/<el-table-column prop="os_name" label="系统"/)
  expect(source).not.toMatch(/<el-table-column prop="browser_name" label="浏览器"/)
})
```

- [ ] **Step 2: Run the regression guard to confirm RED if the dialog/card text is absent**

Run:

```powershell
cd frontend
npm test -- --run src/utils/__tests__/frontend-regressions.spec.js
```

Expected: PASS if Task 2 is finished correctly; otherwise FAIL and fix before proceeding.

- [ ] **Step 3: Run the complete targeted frontend suite**

Run:

```powershell
cd frontend
npm test -- --run src/utils/__tests__/trackingDisplay.spec.js src/views/admin/__tests__/TrackingDashboard.spec.js src/utils/__tests__/frontend-regressions.spec.js
```

Expected: PASS.

- [ ] **Step 4: Build the frontend to verify the dashboard still compiles**

Run:

```powershell
cd frontend
npm run build
```

Expected: build succeeds.

- [ ] **Step 5: Commit the regression and verification pass**

```bash
git add frontend/src/utils/__tests__/frontend-regressions.spec.js
git commit -m "test: cover tracking info card dashboard regression"
```

---

## Self-Review Notes

- Spec coverage: the plan covers single-column merge, standard summary card, full-card click, dialog with five readable sections, technical details, and the location empty-value fix by reusing central display helpers.
- Placeholder scan: no `TODO`, `TBD`, “similar to Task N”, or generic “add tests” steps remain.
- Type consistency: helper names used across tasks are consistent: `buildTrackingInfoCard`, `buildTrackingTechnicalDetails`, `openAccessInfoDialog`, `selectedAccessInfoTechnicalDetails`.
