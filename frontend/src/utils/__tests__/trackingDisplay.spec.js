import { describe, expect, it } from 'vitest'
import {
  formatDeviceFallback,
  formatDevicePrimary,
  formatDeviceSecondary,
  formatDeviceTooltip,
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

  it('returns unknown fallback for unknown or missing device types', () => {
    expect(formatDeviceFallback({ device_type: 'unknown' })).toBe('未识别')
    expect(formatDeviceFallback({ device_type: 'console', os_name: 'Linux' })).toBe('未识别')
    expect(formatDeviceFallback({})).toBe('未识别')
  })

  it('gracefully degrades device secondary output when pieces are missing', () => {
    expect(formatDeviceSecondary({ browser_name: 'Firefox', browser_version: '126' })).toBe('Firefox 126')
    expect(formatDeviceSecondary({ os_name: 'iOS' })).toBe('iOS')
    expect(formatDeviceSecondary({ browser_version: '126' })).toBe('126')
    expect(formatDeviceSecondary({})).toBe('')
  })
})
