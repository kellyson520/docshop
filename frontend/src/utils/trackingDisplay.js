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

function normalizeLooseText(value) {
  if (value === null || value === undefined) return ''
  return String(value).trim()
}

export function withDash(value) {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'string' && value.trim() === '') return '-'
  return value
}

function toDetailValue(value) {
  const normalized = withDash(value)
  return normalized === '-' ? normalized : String(normalized)
}

function joinParts(parts, separator = ' ') {
  return parts.filter(Boolean).join(separator)
}

function toFiniteNumber(value) {
  if (value === null || value === undefined) return null
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (trimmed === '') return null
    value = trimmed
  }
  const num = Number(value)
  return Number.isFinite(num) ? num : null
}

function getUnknownDeviceLabel(type) {
  if (type === 'mobile') return '未知手机'
  if (type === 'tablet') return '未知平板'
  return '桌面设备'
}

function normalizeDeviceType(type) {
  const normalized = normalizeText(type).toLowerCase()
  return ['desktop', 'mobile', 'tablet'].includes(normalized) ? normalized : ''
}

function isWindowsDesktop(row) {
  return normalizeDeviceType(row?.device_type) === 'desktop' && normalizeText(row?.os_name) === 'Windows'
}

function isAppleMac(row) {
  const brand = normalizeText(row?.device_brand).toLowerCase()
  const model = normalizeText(row?.device_model).toLowerCase()
  const osName = normalizeText(row?.os_name).toLowerCase()
  return (
    normalizeDeviceType(row?.device_type) === 'desktop' &&
    (brand === 'apple' || model === 'mac' || model === 'macbook' || osName === 'mac os' || osName === 'macos')
  )
}

function getDesktopFallback(osName) {
  const normalizedOsName = normalizeText(osName).toLowerCase()

  if (normalizedOsName === 'windows') return 'Windows PC'
  if (normalizedOsName === 'macos' || normalizedOsName === 'mac os') return 'Apple Mac'
  if (normalizedOsName === 'linux') return 'Linux PC'
  return '桌面设备'
}

export function formatDevicePrimary(row = {}) {
  const resolvedDisplayName = normalizeText(row.device_display_name)
  if (resolvedDisplayName) return resolvedDisplayName

  const resolvedBrand = normalizeText(row.device_brand_name)
  const resolvedModel = normalizeText(row.device_model_name)
  const resolvedCode = normalizeText(row.device_model_code)
  if (resolvedModel) {
    const resolvedName = joinParts([resolvedBrand, resolvedModel], ' ')
    return resolvedCode && resolvedCode.toLowerCase() !== resolvedModel.toLowerCase()
      ? `${resolvedName} / ${resolvedCode}`
      : resolvedName
  }

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

  const deviceType = normalizeDeviceType(row.device_type)
  if (!deviceType) return UNKNOWN_LABEL

  return getUnknownDeviceLabel(deviceType)
}

export function formatDeviceSecondary(row = {}) {
  const osName = normalizeText(row.os_name)
  const osVersion = normalizeText(row.os_version)
  const browserName = normalizeText(row.browser_name)
  const browserVersion = normalizeText(row.browser_version)

  const os = joinParts([osName, osVersion], ' ')
  const browser = joinParts([browserName, browserVersion], ' ')
  return joinParts([os, browser], ' · ')
}

export function formatDeviceFallback(row = {}) {
  const deviceType = normalizeDeviceType(row.device_type)

  if (!deviceType) return UNKNOWN_LABEL
  if (deviceType === 'mobile') return '未知手机'
  if (deviceType === 'tablet') return '未知平板'
  if (deviceType === 'desktop') return getDesktopFallback(row.os_name)

  return UNKNOWN_LABEL
}

export function formatDeviceTooltip(row = {}) {
  const primary = formatDevicePrimary(row)
  const secondary = formatDeviceSecondary(row)
  return secondary ? `${primary}\n${secondary}` : primary
}

export function formatGeoLocation(row = {}) {
  const latitude = toFiniteNumber(row.geo_latitude)
  const longitude = toFiniteNumber(row.geo_longitude)

  if (latitude !== null && longitude !== null) {
    const accuracy = toFiniteNumber(row.geo_accuracy)
    const accuracyText = Number.isFinite(accuracy) ? ` (±${Math.round(accuracy)}m)` : ''
    return `📍 ${latitude.toFixed(4)}, ${longitude.toFixed(4)}${accuracyText}`
  }

  const region = joinParts([normalizeText(row.ip_city), normalizeText(row.ip_country)], ', ')
  return region || UNKNOWN_LABEL
}

export function formatClientEnvironment(row = {}) {
  return joinParts([normalizeText(row.client_timezone), normalizeText(row.client_language)], ' · ') || UNKNOWN_LABEL
}

export function formatVisitorIpGeoSummary(visitorIpContext = null) {
  if (!visitorIpContext || typeof visitorIpContext !== 'object') return ''

  const parts = [
    normalizeLooseText(visitorIpContext.city),
    normalizeLooseText(visitorIpContext.countryCode || visitorIpContext.country),
  ].filter(Boolean)

  return parts.length ? `访客IP · ${parts.join(', ')}` : ''
}

export function formatVisitorIpTypeSummary(visitorIpContext = null) {
  if (!visitorIpContext || typeof visitorIpContext !== 'object') return ''

  return [
    normalizeLooseText(visitorIpContext.version),
    normalizeLooseText(visitorIpContext.scopeLabel),
  ].filter(Boolean).join(' · ')
}

export function formatVisitorIpNetworkSummary(visitorIpContext = null) {
  if (!visitorIpContext || typeof visitorIpContext !== 'object') return ''

  const asn = normalizeLooseText(visitorIpContext.asn)
  const organization = normalizeLooseText(visitorIpContext.asOrganization)

  if (asn && organization) return `AS${asn} · ${organization}`
  if (asn) return `AS${asn}`
  return organization
}

export function buildVisitorIpContextDetails(visitorIpContext = null) {
  if (!visitorIpContext || typeof visitorIpContext !== 'object') return []

  const countryText = normalizeLooseText(visitorIpContext.countryCode || visitorIpContext.country)

  return [
    { label: '访客 IP', value: toDetailValue(visitorIpContext.ip) },
    { label: 'IP 版本', value: toDetailValue(visitorIpContext.version) },
    { label: '地址类型', value: toDetailValue(visitorIpContext.scopeLabel) },
    { label: '国家/地区', value: toDetailValue(countryText) },
    { label: '城市', value: toDetailValue(visitorIpContext.city) },
    { label: 'ASN', value: toDetailValue(visitorIpContext.asn) },
    { label: '运营商/组织', value: toDetailValue(visitorIpContext.asOrganization) },
  ]
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

export function buildTrackingInfoCard(row = {}, visitorIpContext = null) {
  const toInfoCardFallback = (value) => (value === UNKNOWN_LABEL ? '-' : withDash(value))
  const title = toInfoCardFallback(formatDevicePrimary(row))
  const deviceTypeText = toInfoCardFallback(getDeviceTypeText(normalizeDeviceType(row.device_type) || row.device_type))
  const secondary = toInfoCardFallback(formatDeviceSecondary(row))
  const location = toInfoCardFallback(formatGeoLocation(row))
  const environment = toInfoCardFallback(formatClientEnvironment(row))

  return {
    title,
    deviceTypeText,
    secondary,
    location,
    environment,
    visitorIpSummary: formatVisitorIpGeoSummary(visitorIpContext),
    visitorIpType: formatVisitorIpTypeSummary(visitorIpContext),
    visitorIpNetwork: formatVisitorIpNetworkSummary(visitorIpContext),
  }
}

export const formatServerIpGeoSummary = formatVisitorIpGeoSummary
export function formatServerIpRiskSummary() {
  return ''
}
export const formatServerIpNetworkSummary = formatVisitorIpNetworkSummary
export const buildServerIpContextDetails = buildVisitorIpContextDetails

export function buildTrackingTechnicalDetails(row = {}) {
  return [
    { label: '型号代码', value: toDetailValue(row.device_model_code) },
    { label: '型号名称', value: toDetailValue(row.device_model_name) },
    { label: '品牌名称', value: toDetailValue(row.device_brand_name) },
    { label: '展示名称', value: toDetailValue(row.device_display_name) },
    { label: '屏幕分辨率', value: toDetailValue(row.screen_resolution) },
    { label: '纬度', value: toDetailValue(row.geo_latitude) },
    { label: '经度', value: toDetailValue(row.geo_longitude) },
    { label: '定位精度', value: toDetailValue(row.geo_accuracy) },
    { label: '时区', value: toDetailValue(row.client_timezone) },
    { label: '语言', value: toDetailValue(row.client_language) },
    { label: 'User-Agent', value: toDetailValue(row.user_agent) },
    { label: '访客 ID', value: toDetailValue(row.visitor_id) },
  ]
}
