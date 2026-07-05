function normalizeVisibility(value, { scope = 'project', defaultVisibility } = {}) {
  const projectDefault = defaultVisibility || 'public'
  const fileDefault = defaultVisibility || 'inherit'
  const allowed = scope === 'file'
    ? ['inherit', 'public', 'password_required', 'groups_required', 'private']
    : ['public', 'password_required', 'groups_required', 'private']
  const fallback = scope === 'file' ? fileDefault : projectDefault
  return allowed.includes(value) ? value : fallback
}

function booleanWithDefault(value, defaultValue = true) {
  return value === undefined || value === null ? defaultValue : value !== false
}

function uniqueStrings(values = []) {
  const normalized = []
  for (const value of values || []) {
    const text = String(value || '').trim()
    if (text && !normalized.includes(text)) normalized.push(text)
  }
  return normalized
}

export const PROJECT_PUBLIC_ACCESS_VISIBILITY_OPTIONS = [
  { value: 'public', label: '公开浏览' },
  { value: 'password_required', label: '密码访问' },
  { value: 'groups_required', label: '用户组访问' },
  { value: 'private', label: '禁止公开浏览' },
]

export const FILE_PUBLIC_ACCESS_VISIBILITY_OPTIONS = [
  { value: 'inherit', label: '继承项目配置' },
  ...PROJECT_PUBLIC_ACCESS_VISIBILITY_OPTIONS,
]

export function getResourceAccessVisibilityOptions(scope = 'project') {
  return scope === 'file'
    ? FILE_PUBLIC_ACCESS_VISIBILITY_OPTIONS
    : PROJECT_PUBLIC_ACCESS_VISIBILITY_OPTIONS
}

export function buildResourceAccessFormState({
  policy = null,
  scope = 'project',
  defaultVisibility,
} = {}) {
  const source = policy || {}

  return {
    visibility: normalizeVisibility(source.visibility, { scope, defaultVisibility }),
    allow_preview: booleanWithDefault(source.allow_preview, true),
    allow_download: booleanWithDefault(source.allow_download, true),
    allow_diff: booleanWithDefault(source.allow_diff, true),
    allow_versions: booleanWithDefault(source.allow_versions, true),
    password: '',
    clear_password: false,
    password_hint: source.password_hint || '',
    has_password: Boolean(source.has_password),
    group_codes: uniqueStrings(source.group_codes || []),
  }
}

export function buildResourceAccessMutationPayload(
  form = {},
  { scope = 'project' } = {},
) {
  const payload = {
    visibility: normalizeVisibility(form.visibility, { scope }),
    allow_preview: form.allow_preview !== false,
    allow_download: form.allow_download !== false,
    allow_diff: form.allow_diff !== false,
    allow_versions: form.allow_versions !== false,
    password_hint: form.password_hint || '',
    group_codes: uniqueStrings(form.group_codes || []),
  }

  if (form.password) {
    payload.password = form.password
  } else if (form.clear_password) {
    payload.clear_password = true
  }

  return payload
}
