export const DEFAULT_SHARE_POLICY_MODE = 'override_with_token_policy'

export const SHARE_POLICY_MODE_OPTIONS = [
  {
    value: 'override_with_token_policy',
    label: '分享权限独立生效',
    hint: '分享权限仅作用于分享链接，不继承公开浏览权限。',
    summary: '分享权限独立生效',
  },
]

function findSharePolicyModeOption(value) {
  return SHARE_POLICY_MODE_OPTIONS.find((option) => option.value === value) || null
}

function booleanAccessLabel(value, enabledText, disabledText) {
  return value === false ? disabledText : enabledText
}

export function normalizeSharePolicyMode(value) {
  return findSharePolicyModeOption(value)?.value || DEFAULT_SHARE_POLICY_MODE
}

export function getSharePolicyModeMeta(value) {
  const normalized = normalizeSharePolicyMode(value)
  return findSharePolicyModeOption(normalized) || SHARE_POLICY_MODE_OPTIONS[0]
}

export function buildShareAccessSummaryItems(source = {}) {
  const passwordHint = String(source?.password_hint || '').trim()

  const items = [
    {
      key: 'require_login',
      text: source?.require_login ? '需要登录' : '免登录访问',
    },
  ]

  if (passwordHint) {
    items.push({
      key: 'password_hint',
      text: `密码提示：${passwordHint}`,
    })
  }

  items.push(
    {
      key: 'allow_download',
      text: booleanAccessLabel(source?.allow_download, '允许下载', '禁止下载'),
    },
    {
      key: 'allow_preview',
      text: booleanAccessLabel(source?.allow_preview, '允许预览', '禁用预览'),
    },
    {
      key: 'allow_diff',
      text: booleanAccessLabel(source?.allow_diff, '允许 Diff', '禁用 Diff'),
    },
    {
      key: 'allow_versions',
      text: booleanAccessLabel(source?.allow_versions, '允许版本历史', '禁用版本历史'),
    },
    {
      key: 'policy_mode',
      text: getSharePolicyModeMeta(source?.policy_mode).summary,
    },
  )

  return items
}

export function formatShareAccessSummary(source = {}) {
  return buildShareAccessSummaryItems(source)
    .map((item) => item.text)
    .join(' · ')
}
