import { normalizeSharePolicyMode } from '@/utils/shareAccess'

function numberOrZero(value) {
  const normalized = Number(value ?? 0)
  return Number.isFinite(normalized) ? normalized : 0
}

function booleanWithDefault(value, defaultValue) {
  return value === undefined || value === null ? defaultValue : value !== false
}

export function normalizeShareTokenDateTimeInput(value) {
  return value ? String(value).replace(/Z$/, '') : ''
}

export function buildShareTokenFormState({ token = null, defaults = {} } = {}) {
  const source = token || {}

  return {
    name: source.name || defaults.name || '',
    resource_type: source.resource_type || defaults.resource_type || 'project',
    resource_id: source.resource_id || defaults.resource_id || '',
    max_views: numberOrZero(source.max_views ?? defaults.max_views),
    max_downloads: numberOrZero(source.max_downloads ?? defaults.max_downloads),
    allow_download: booleanWithDefault(source.allow_download ?? defaults.allow_download, true),
    require_login: Boolean(source.require_login ?? defaults.require_login),
    password: '',
    clear_password: false,
    password_hint: source.password_hint || defaults.password_hint || '',
    allow_preview: booleanWithDefault(source.allow_preview ?? defaults.allow_preview, true),
    allow_diff: booleanWithDefault(source.allow_diff ?? defaults.allow_diff, true),
    allow_versions: booleanWithDefault(source.allow_versions ?? defaults.allow_versions, true),
    policy_mode: normalizeSharePolicyMode(source.policy_mode || defaults.policy_mode),
    expires_at: normalizeShareTokenDateTimeInput(source.expires_at ?? defaults.expires_at),
  }
}

export function buildShareTokenMutationPayload(
  form = {},
  {
    preservePasswordWhenBlank = false,
    includeResourceIdentifiers = true,
  } = {},
) {
  const payload = {
    name: form.name || '',
    max_views: numberOrZero(form.max_views),
    max_downloads: numberOrZero(form.max_downloads),
    allow_download: form.allow_download !== false,
    require_login: Boolean(form.require_login),
    password_hint: form.password_hint || '',
    allow_preview: form.allow_preview !== false,
    allow_diff: form.allow_diff !== false,
    allow_versions: form.allow_versions !== false,
    policy_mode: normalizeSharePolicyMode(form.policy_mode),
    expires_at: form.expires_at ? `${normalizeShareTokenDateTimeInput(form.expires_at)}Z` : null,
  }

  if (includeResourceIdentifiers) {
    if (form.resource_type) payload.resource_type = form.resource_type
    if (form.resource_id) payload.resource_id = form.resource_id
  }

  if (preservePasswordWhenBlank) {
    if (form.password) {
      payload.password = form.password
    } else if (form.clear_password) {
      payload.password = ''
    }
    return payload
  }

  payload.password = form.password || ''
  return payload
}
