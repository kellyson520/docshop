# Access Control Matrix

## Visibility Modes

| visibility | anonymous | logged-in | group-member | unlocked-share | admin |
| --- | --- | --- | --- | --- | --- |
| `public` | allow by action flags | allow by action flags | allow by action flags | allow by action flags | allow |
| `login_required` | deny | allow by action flags | allow by action flags | deny | allow |
| `password_required` | deny unless unlock grant | deny unless unlock grant | deny unless unlock grant | allow by action flags | allow |
| `groups_required` | deny | deny unless member | allow by action flags | deny | allow |
| `private` | deny | deny unless owner / inherited project member | deny unless owner / inherited project member | deny | allow |
| `inherit` | resolve from parent project policy | resolve from parent project policy | resolve from parent project policy | resolve from parent project policy | allow |

## Action Flags

| action | meaning |
| --- | --- |
| `view_metadata` | 查看文件或项目基础信息 |
| `view_preview` | 查看预览页 / html / text |
| `view_page_asset` | 查看分页图 / preview assets |
| `view_diff` | 查看 diff 列表与详情 |
| `view_versions` | 查看版本列表 |
| `download_original` | 下载原文件 |
| `download_converted` | 下载转换后格式 |
| `manage_share` | 管理 share token |
| `manage_policy` | 管理访问策略 |

## Notes

- `admin` 始终放行。
- `share token` 只决定外链范围、次数、有效期，不替代统一授权判断。
- `password_required` 的首版通过短时 `share_access_grant` cookie 解锁。
- `groups_required` 首版仅服务端强制校验，不依赖前端显隐。
