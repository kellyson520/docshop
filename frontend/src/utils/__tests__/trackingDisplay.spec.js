import { describe, expect, it } from 'vitest'
import {
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
    expect(formatDeviceSecondary(row)).toBe('Windows · Edge 149')
    expect(formatDeviceTooltip(row)).toContain('Windows PC')
    expect(getDeviceTypeText('desktop')).toBeTruthy()
  })

  it('falls back to unknown mobile label when brand and model are absent', () => {
    const row = {
      device_type: 'mobile',
      os_name: 'Android',
      browser_name: 'Chrome',
    }

    expect(formatDevicePrimary(row)).toBe('未知手机')
    expect(formatDeviceSecondary(row)).toBe('Android · Chrome')
  })
})
