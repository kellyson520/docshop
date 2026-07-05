# Share and Public Permission Full Decoupling Design

## Context

The current implementation already separates two runtime entry types:

1. **Legacy public browse** via project public routes (`Project.share_token`, `/s/:token`, legacy public shell)
2. **Managed share links** via `ShareToken`

However, managed share links still partially inherit resource public-browse policy through `_resolve_share_effective_policy()`. This means a link that should be governed only by share permissions can still be blocked by resource public policy.

The required target behavior is stricter:

- If a request enters through **public browse**, it must be governed only by **public-browse permissions**
- If a request enters through a **managed share link**, it must be governed only by **share permissions**
- The two permission systems must coexist, but must not affect each other at runtime

## Goals

1. Fully decouple managed share-link access from resource public-browse policy
2. Keep legacy public browse governed exclusively by resource access policy
3. Keep share-password and public-resource-password flows separated
4. Update admin UI copy so the behavior matches the runtime semantics

## Non-Goals

- No route redesign
- No migration removing `policy_mode` from the database in this round
- No changes to legacy public password-tab lifecycle beyond what already shipped

## Chosen Design

### 1. Runtime authority split

#### Legacy public browse

Requests resolved as:

- `resolved["legacy"] == True`
- `resolved["share_token"] is None`

continue to use:

- resource visibility (`public / private / password_required / groups_required / login_required`)
- resource action flags (`allow_preview / allow_diff / allow_versions / allow_download`)
- resource-scoped public access grant (`X-Access-*`)

#### Managed share links

Requests resolved as:

- `resolved["share_token"] is not None`

must use only:

- share login requirement
- share password grant
- share action flags (`allow_preview / allow_diff / allow_versions / allow_download`)
- share view/download quotas

Managed share links must no longer inherit, merge with, or be blocked by resource public-browse visibility or resource action flags.

### 2. Backend policy resolution

`backend/app/routers/share.py::_resolve_share_effective_policy()` will change behavior:

- when `token_model is None`: keep returning resource public policy
- when `token_model exists`: return a synthetic share-only policy with:
  - `visibility = "public"`
  - `required_group_codes = set()`
  - action flags sourced only from `ShareToken`

Share login and share password remain enforced by the existing dedicated functions:

- `_require_share_login()`
- `_require_share_password_grant()`

This keeps responsibility clear:

- **visibility / groups / resource passwords** => public browse only
- **share login / share password / share capabilities** => managed share only

### 3. `policy_mode` compatibility strategy

The `ShareToken.policy_mode` field remains in the schema for compatibility, but the runtime no longer uses it.

This round treats managed shares as always equivalent to the previous:

- `override_with_token_policy`

Compatibility behavior:

- backend create/update normalizes saved `policy_mode` to `override_with_token_policy`
- frontend form state also normalizes to `override_with_token_policy`
- admin UI no longer presents inherit-vs-override as a runtime choice

### 4. Admin UI behavior

#### Public browse controls

Public browse editors stay where they are now:

- project public-browse dialog
- file public-browse section

These continue controlling only legacy public browse behavior.

#### Share controls

Managed share dialogs remain independent and explicitly communicate:

- share permissions apply only to share links
- they do not inherit public-browse restrictions

The previous “policy mode” selector is replaced with a fixed explanatory note.

### 5. Error semantics

No mixed error mode should appear across the two tracks.

Managed share links continue to use:

- `share_password_required`
- `login_required`

Legacy public browse continues to use:

- `resource_password_required`
- `group_required`
- `login_required`

## Testing Strategy

### Backend

Add regression coverage for:

1. managed share token can access a file even when the file public policy is `password_required`
2. managed share token preview ticket can be issued without public-access grant even when resource public policy is protected
3. share token create/update normalizes `policy_mode` to `override_with_token_policy`

### Frontend

Add/update coverage for:

1. share token form helpers normalize any incoming `policy_mode` to the decoupled canonical value
2. ProjectDetail managed share dialog shows fixed independent-permission copy instead of runtime policy-mode switching
3. TokenManager managed share editor/detail summary reflects independent share permissions

## Risks and Mitigations

1. **Old share tokens stored with inherit mode**
   - Mitigation: runtime ignores inherit semantics; form save rewrites to canonical independent mode

2. **Admin confusion if UI still shows old strategy selector**
   - Mitigation: remove selector from share dialogs and replace with explicit decoupling copy

3. **Accidental regression for legacy public browse**
   - Mitigation: keep legacy tests untouched and add explicit managed-share-vs-public-decoupling regressions

## Final Decision

Adopt **Scheme A**:

- public entry => only public-browse permissions
- share entry => only share permissions
- coexistence without runtime coupling


## Implementation Status (2026-07-05 18:36 CST)

Implemented as designed:

- managed share routes now resolve a share-only runtime policy
- public-browse resource visibility, group, and password policy no longer block managed share links
- `ShareToken.policy_mode` is retained only as a compatibility field and now normalizes to `override_with_token_policy`
- admin UI now states explicitly that share permissions apply only to share links and do not inherit public-browse restrictions
