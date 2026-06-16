const UNKNOWN_LABEL = '未识别'

const DEVICE_TYPE_LABELS = {
  desktop: '桌面端',
  mobile: '移动端',
  tablet: '平板',
  unknown: UNKNOWN_LABEL,
}

const ACTION_LABELS = {
  view: '浏览',
  preview: '预览',
  download: '下载',
  diff: '对比',
  delete: '删除',
  get: '读取',
  post: '提交',
  put: '更新',
  share_token_list: '查看分享令牌',
  share_token_create: '创建分享令牌',
  share_token_update: '更新分享令牌',
  share_token_regenerate: '重新生成分享令牌',
  share_token_delete: '删除分享令牌',
}

const TARGET_LABELS = {
  file: '文件',
  project: '项目',
  share_file: '分享文件',
  share_project: '分享项目',
  share_token: '分享令牌',
}

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function joinParts(parts, separator = ' ') {
  return parts.filter(Boolean).join(separator)
}

function getUnknownDeviceLabel(type) {
  if (type === 'mobile') return '未知手机'
  if (type === 'tablet') return '未知平板'
  return '桌面设备'
}

function isWindowsDesktop(row) {
  return row?.device_type === 'desktop' && normalizeText(row?.os_name) === 'Windows'
}

function isAppleMac(row) {
  const brand = normalizeText(row?.device_brand).toLowerCase()
  const model = normalizeText(row?.device_model).toLowerCase()
  const osName = normalizeText(row?.os_name).toLowerCase()
  return (
    row?.device_type === 'desktop' &&
    (brand === 'apple' || model === 'mac' || model === 'macbook' || osName === 'mac os' || osName === 'macos')
  )
}

export function formatDevicePrimary(row = {}) {
  const brand = normalizeText(row.device_brand)
  const model = normalizeText(row.device_model)

  if (isWindowsDesktop(row)) return 'Windows PC'
  if (isAppleMac(row)) return 'Apple Mac'

  if (brand && model) {
    const brandLower = brand.toLowerCase()
    const modelLower = model.toLowerCase()
    if (brandLower === modelLower || modelLower.includes(brandLower)) return model
    return `${brand} ${model}`
  }

  if (brand || model) return brand || model

  return getUnknownDeviceLabel(row.device_type)
}

export function formatDeviceSecondary(row = {}) {
  const osName = normalizeText(row.os_name)
  const browserName = normalizeText(row.browser_name)
  const browserVersion = normalizeText(row.browser_version)

  const browser = joinParts([browserName, browserVersion], ' ')
  return joinParts([osName, browser], ' · ')
}

export function formatDeviceFallback(row = {}) {
  return formatDevicePrimary(row)
}

export function formatDeviceTooltip(row = {}) {
  const primary = formatDevicePrimary(row)
  const secondary = formatDeviceSecondary(row)
  return secondary ? `${primary}\n${secondary}` : primary
}

export function getDistributionLabel(value) {
  if (!value || value === 'unknown') return UNKNOWN_LABEL
  return value
}

export function getDeviceTypeText(type) {
  return DEVICE_TYPE_LABELS[type] || getDistributionLabel(type)
}

export function getTrackingActionLabel(actionType) {
  return ACTION_LABELS[actionType] || getDistributionLabel(actionType)
}

export function getTrackingTargetLabel(targetType) {
  return TARGET_LABELS[targetType] || getDistributionLabel(targetType)
}

export function formatTrackingTargetId(targetId) {
  if (!targetId) return ''
  if (targetId === 'new') return '新令牌'
  if (targetId === 'list') return '列表'
  return targetId
}

export function formatTrackingBusiness(row = {}) {
  const parts = []
  if (row.action_type) parts.push(getTrackingActionLabel(row.action_type))
  if (row.target_type) parts.push(getTrackingTargetLabel(row.target_type))
  const targetId = formatTrackingTargetId(row.target_id)
  if (targetId) parts.push(targetId)
  const tokenPreview = row.business_context?.share_token_preview
  if (tokenPreview) parts.push(`token ${tokenPreview}`)
  return parts.join(' / ') || '普通访问'
}
