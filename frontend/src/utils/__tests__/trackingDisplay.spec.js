import { describe, expect, it } from 'vitest'
import {
  buildVisitorIpContextDetails,
  buildTrackingInfoCard,
  buildTrackingTechnicalDetails,
  formatDeviceFallback,
  formatDevicePrimary,
  formatDeviceSecondary,
  formatDeviceTooltip,
  formatGeoLocation,
  formatClientEnvironment,
  formatTrackingBusiness,
  getDeviceTypeText,
  getDistributionLabel,
  getTrackingActionLabel,
  getTrackingTargetLabel,
} from '../trackingDisplay'

describe('trackingDisplay', () => {
  it('localizes unknown monitoring labels instead of showing raw unknown', () => {
    expect(getDeviceTypeText('unknown')).toBe('未识别')
    expect(getDistributionLabel('unknown')).toBe('未识别')
    expect(getDistributionLabel('')).toBe('未识别')
  })

  it('renders share token business context with masked token preview', () => {
    const row = {
      action_type: 'preview',
      target_type: 'share_file',
      target_id: 'file-123',
      business_context: {
        share_token_preview: 'sens***oken',
        share_token_hash: 'abc123',
      },
    }

    expect(getTrackingActionLabel(row.action_type)).toBe('预览')
    expect(getTrackingTargetLabel(row.target_type)).toBe('分享文件')
    expect(formatTrackingBusiness(row)).toBe('预览 / 分享文件 / file-123 / token sens***oken')
  })

  it('renders share-token management rows without unknown', () => {
    const row = {
      action_type: 'share_token_create',
      target_type: 'share_token',
      target_id: 'new',
    }

    expect(formatTrackingBusiness(row)).toBe('创建分享令牌 / 分享令牌 / 新令牌')
  })

  it('prefers resolved mobile model display name when available', () => {
    expect(formatDevicePrimary({
      device_display_name: 'Huawei P40 / ANA-AL00',
      device_type: 'mobile',
      device_brand: 'Huawei',
      device_model: 'ANA-AL00',
    })).toBe('Huawei P40 / ANA-AL00')
  })

  it('builds readable device name from resolved model fields when display name is absent', () => {
    expect(formatDevicePrimary({
      device_brand_name: 'Huawei',
      device_model_name: 'P40',
      device_model_code: 'ANA-AL00',
      device_type: 'mobile',
      device_brand: 'Huawei',
      device_model: 'ANA-AL00',
    })).toBe('Huawei P40 / ANA-AL00')
  })

  it('formats desktop fallback with normalized windows summary', () => {
    const row = {
      device_type: 'desktop',
      device_brand: 'Microsoft',
      device_model: 'PC',
      os_name: 'Windows',
      browser_name: 'Edge',
      browser_version: '149',
    }

    expect(formatDevicePrimary(row)).toBe('Windows PC')
    expect(formatDeviceFallback(row)).toBe('Windows PC')
    expect(formatDeviceSecondary(row)).toBe('Windows · Edge 149')
    expect(formatDeviceTooltip(row)).toBe('Windows PC\nWindows · Edge 149')
    expect(getDeviceTypeText('desktop')).toBeTruthy()
  })

  it('falls back to unknown mobile label when brand and model are absent', () => {
    const row = {
      device_type: 'mobile',
      os_name: 'Android',
      browser_name: 'Chrome',
    }

    expect(formatDevicePrimary(row)).toBe('未知手机')
    expect(formatDeviceFallback(row)).toBe('未知手机')
    expect(formatDeviceSecondary(row)).toBe('Android · Chrome')
  })

  it('formats apple mac devices with normalized desktop summary', () => {
    const row = {
      device_type: 'desktop',
      device_brand: 'Apple',
      device_model: 'MacBook Pro',
      os_name: 'macOS',
      browser_name: 'Safari',
      browser_version: '17',
    }

    expect(formatDevicePrimary(row)).toBe('Apple Mac')
    expect(formatDeviceFallback(row)).toBe('Apple Mac')
    expect(formatDeviceSecondary(row)).toBe('macOS · Safari 17')
    expect(formatDeviceTooltip(row)).toBe('Apple Mac\nmacOS · Safari 17')
  })

  it('uses linux desktop fallback when desktop details are absent', () => {
    const row = {
      device_type: 'desktop',
      os_name: 'Linux',
      browser_name: 'Firefox',
      browser_version: '126',
    }

    expect(formatDevicePrimary(row)).toBe('桌面设备')
    expect(formatDeviceFallback(row)).toBe('Linux PC')
    expect(formatDeviceSecondary(row)).toBe('Linux · Firefox 126')
    expect(formatDeviceTooltip(row)).toBe('桌面设备\nLinux · Firefox 126')
  })

  it('deduplicates brand and model combinations cleanly', () => {
    const row = {
      device_type: 'mobile',
      device_brand: 'Samsung',
      device_model: 'Samsung Galaxy S24',
      browser_name: 'Chrome',
    }

    expect(formatDevicePrimary(row)).toBe('Samsung Galaxy S24')
    expect(formatDeviceFallback(row)).toBe('未知手机')
    expect(formatDeviceSecondary(row)).toBe('Chrome')
    expect(formatDeviceTooltip(row)).toBe('Samsung Galaxy S24\nChrome')
  })

  it('uses tablet and desktop normalized fallback labels when brand and model are absent', () => {
    const tabletRow = {
      device_type: 'tablet',
      browser_name: 'Safari',
    }
    const desktopRow = {
      device_type: 'desktop',
    }

    expect(formatDevicePrimary(tabletRow)).toBe('未知平板')
    expect(formatDeviceFallback(tabletRow)).toBe('未知平板')
    expect(formatDevicePrimary(desktopRow)).toBe('桌面设备')
    expect(formatDeviceFallback(desktopRow)).toBe('桌面设备')
    expect(formatDeviceTooltip(desktopRow)).toBe('桌面设备')
  })

  it('returns unknown labels for unknown or missing device types in primary and tooltip paths', () => {
    expect(formatDevicePrimary({})).toBe('未识别')
    expect(formatDevicePrimary({ device_type: 'unknown' })).toBe('未识别')
    expect(formatDeviceFallback({ device_type: 'unknown' })).toBe('未识别')
    expect(formatDeviceFallback({ device_type: 'console', os_name: 'Linux' })).toBe('未识别')
    expect(formatDeviceFallback({})).toBe('未识别')
    expect(formatDeviceTooltip({})).toBe('未识别')
  })

  it('gracefully degrades device secondary output when pieces are missing', () => {
    expect(formatDeviceSecondary({ browser_name: 'Firefox', browser_version: '126' })).toBe('Firefox 126')
    expect(formatDeviceSecondary({ os_name: 'iOS' })).toBe('iOS')
    expect(formatDeviceSecondary({ browser_version: '126' })).toBe('126')
    expect(formatDeviceSecondary({})).toBe('')
  })

  it('formats precise browser location with rounded coordinates and accuracy', () => {
    expect(formatGeoLocation({
      geo_latitude: 39.904212,
      geo_longitude: 116.407389,
      geo_accuracy: 8.5,
    })).toBe('📍 39.9042, 116.4074 (±9m)')
  })

  it('falls back to IP region when precise browser location is absent', () => {
    expect(formatGeoLocation({ ip_city: 'Beijing', ip_country: 'CN' })).toBe('Beijing, CN')
    expect(formatGeoLocation({})).toBe('未识别')
  })

  it('does not treat empty coordinates as 0,0 when browser geolocation is missing', () => {
    expect(formatGeoLocation({
      geo_latitude: null,
      geo_longitude: null,
      ip_city: 'Linyi',
      ip_country: 'CN',
    })).toBe('Linyi, CN')

    expect(formatGeoLocation({
      geo_latitude: undefined,
      geo_longitude: undefined,
    })).toBe('未识别')
  })

  it('falls back to IP region when coordinates are whitespace strings', () => {
    expect(formatGeoLocation({
      geo_latitude: '   ',
      geo_longitude: '   ',
      ip_city: 'Beijing',
      ip_country: 'CN',
    })).toBe('Beijing, CN')
  })

  it('formats client timezone and language without leaking empty placeholders', () => {
    expect(formatClientEnvironment({
      client_timezone: 'Asia/Shanghai',
      client_language: 'zh-CN',
    })).toBe('Asia/Shanghai · zh-CN')
    expect(formatClientEnvironment({})).toBe('未识别')
  })

  it('builds a standard info card summary for resolved mobile devices', () => {
    const row = {
      device_display_name: 'Huawei P40 / ANA-AL00',
      device_type: 'mobile',
      device_brand: 'Huawei',
      device_model: 'ANA-AL00',
      os_name: 'Android',
      os_version: '14',
      browser_name: 'Chrome Mobile WebView',
      browser_version: '126',
      geo_latitude: 39.904212,
      geo_longitude: 116.407389,
      geo_accuracy: 8.5,
      client_timezone: 'Asia/Shanghai',
      client_language: 'zh-CN',
    }

    expect(buildTrackingInfoCard(row)).toEqual({
      title: 'Huawei P40 / ANA-AL00',
      deviceTypeText: '移动端',
      secondary: 'Android 14 · Chrome Mobile WebView 126',
      location: '📍 39.9042, 116.4074 (±9m)',
      environment: 'Asia/Shanghai · zh-CN',
      visitorIpSummary: '',
      visitorIpType: '',
      visitorIpNetwork: '',
    })
  })

  it('includes os version in info card secondary summary without extra spaces', () => {
    expect(buildTrackingInfoCard({
      os_name: 'Android',
      os_version: '14',
      browser_name: 'Chrome',
      browser_version: '124',
    }).secondary).toBe('Android 14 · Chrome 124')
  })

  it('adds visitor IP summaries to the tracking info card when context exists', () => {
    const row = {
      device_display_name: 'Huawei P40 / ANA-AL00',
      device_type: 'mobile',
      os_name: 'Android',
      os_version: '14',
      browser_name: 'Chrome',
      browser_version: '126',
      ip_city: 'Beijing',
      ip_country: 'CN',
      client_timezone: 'Asia/Shanghai',
      client_language: 'zh-CN',
    }
    const visitorIpContext = {
      source: 'access_log_visitor_ip',
      ip: '112.224.158.50',
      version: 'IPv4',
      scope: 'public',
      scopeLabel: '公网',
      country: 'CN',
      countryCode: 'CN',
      city: 'Qingdao',
      asn: '4837',
      asOrganization: 'China Unicom Shandong province network',
    }

    expect(buildTrackingInfoCard(row, visitorIpContext)).toEqual({
      title: 'Huawei P40 / ANA-AL00',
      deviceTypeText: '移动端',
      secondary: 'Android 14 · Chrome 126',
      location: 'Beijing, CN',
      environment: 'Asia/Shanghai · zh-CN',
      visitorIpSummary: '访客IP · Qingdao, CN',
      visitorIpType: 'IPv4 · 公网',
      visitorIpNetwork: 'AS4837 · China Unicom Shandong province network',
    })
  })

  it('falls back to dashes for empty info card summaries', () => {
    expect(buildTrackingInfoCard({})).toEqual({
      title: '-',
      deviceTypeText: '-',
      secondary: '-',
      location: '-',
      environment: '-',
      visitorIpSummary: '',
      visitorIpType: '',
      visitorIpNetwork: '',
    })
  })

  it('builds a dedicated visitor IP detail list and degrades cleanly when absent', () => {
    const visitorIpContext = {
      source: 'access_log_visitor_ip',
      ip: '112.224.158.50',
      version: 'IPv4',
      scope: 'public',
      scopeLabel: '公网',
      country: 'CN',
      countryCode: 'CN',
      city: 'Qingdao',
      asn: '4837',
      asOrganization: 'China Unicom Shandong province network',
    }

    expect(buildVisitorIpContextDetails(visitorIpContext)).toEqual([
      { label: '访客 IP', value: '112.224.158.50' },
      { label: 'IP 版本', value: 'IPv4' },
      { label: '地址类型', value: '公网' },
      { label: '国家/地区', value: 'CN' },
      { label: '城市', value: 'Qingdao' },
      { label: 'ASN', value: '4837' },
      { label: '运营商/组织', value: 'China Unicom Shandong province network' },
    ])

    expect(buildTrackingInfoCard({}, null).visitorIpSummary).toBe('')
    expect(buildTrackingInfoCard({}, null).visitorIpType).toBe('')
    expect(buildTrackingInfoCard({}, null).visitorIpNetwork).toBe('')
    expect(buildVisitorIpContextDetails(null)).toEqual([])
  })

  it('returns labeled technical details array with raw values and dash fallbacks', () => {
    expect(buildTrackingTechnicalDetails({
      device_model_code: '',
      device_model_name: 'P40',
      device_brand_name: 'Huawei',
      device_display_name: 'Huawei P40 / ANA-AL00',
      screen_resolution: undefined,
      geo_latitude: 39.904212,
      geo_longitude: null,
      geo_accuracy: 8.5,
      client_timezone: 'Asia/Shanghai',
      client_language: undefined,
      user_agent: 'Mozilla/5.0',
      visitor_id: '',
    })).toEqual([
      { label: '型号代码', value: '-' },
      { label: '型号名称', value: 'P40' },
      { label: '品牌名称', value: 'Huawei' },
      { label: '展示名称', value: 'Huawei P40 / ANA-AL00' },
      { label: '屏幕分辨率', value: '-' },
      { label: '纬度', value: '39.904212' },
      { label: '经度', value: '-' },
      { label: '定位精度', value: '8.5' },
      { label: '时区', value: 'Asia/Shanghai' },
      { label: '语言', value: '-' },
      { label: 'User-Agent', value: 'Mozilla/5.0' },
      { label: '访客 ID', value: '-' },
    ])
  })
})
