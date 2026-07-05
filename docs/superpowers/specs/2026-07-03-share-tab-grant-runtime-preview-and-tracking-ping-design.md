# 2026-07-03 鍒嗕韩 Tab Grant銆佽祫婧?Ticket銆丷untime HTML 棰勮涓?Tracking Ping 淇璁捐

## 1. 鑳屾櫙

鏈疆闇€姹傚凡缁忔槑纭紝涓嶅啀閲嶅璁ㄨ鏂瑰悜锛?
- 缁х画娓呯悊鈥滃垎浜?/ 鏉冮檺 / 璧勬簮閾炬帴鈥濋摼璺噷杩樻病鏀跺彛鐨勯噸澶嶇偣銆?- 浠呴拡瀵?*甯﹀瘑鐮佸垎浜?*鍚敤鏂扮殑瑙ｉ攣浼氳瘽妯″瀷銆?- **鍏虫帀褰撳墠鍒嗕韩 tab 鍗冲瘑鐮佸け鏁?*锛岄噸鏂版墦寮€鎴栨柊寮€ tab 闇€瑕侀噸鏂拌緭鍏ュ瘑鐮併€?- **鍚屼竴涓?tab 鍒锋柊淇濈暀宸茶В閿?*銆?- **姣忎釜 tab 鐙珛瑙ｉ攣**銆?- 鏁翠釜鍒嗕韩閾捐矾閮藉繀椤诲彈鍚屼竴浠借В閿佺姸鎬佺害鏉燂細
  - `/s/:token`
  - 鏂囦欢璇︽儏
  - 棰勮
  - pages
  - preview-assets
  - diff
  - versions
  - 涓嬭浇
- 榛樿閲囩敤**鍚?tab 鍐呭鑸?*锛岄伩鍏嶅瘑鐮佸垎浜〉榛樿璺虫柊 tab銆?- HTML 棰勮蹇呴』鍙互鐐瑰嚮銆佸彲浠ヤ簰鍔ㄣ€?
鍚屾椂锛岀敤鎴疯繕鎸囧嚭浜嗕竴涓凡缁忓畾浣嶇殑鐪熷疄闂锛?
- `POST /api/v1/tracking/ping` 棣栧睆浼氳Е鍙?429銆?
鏍瑰洜宸茬粡纭锛?
- `frontend/src/main.js` 鍚姩鏃惰皟鐢?`initTracking()`
- `frontend/src/router/index.js` 鐨?`router.afterEach()` 鍙堣皟鐢?`sendPageViewTracking()`
- `frontend/src/utils/trackingClient.js` 褰撳墠涓ゆ閮戒細甯?`page_path`
- `backend/app/routers/tracking_ping.py` 瀵瑰悓 identity 10 绉掑唴閲嶅 ping 鍋?429 闄愭祦

---

## 2. 褰撳墠闂

### 2.1 鍒嗕韩瀵嗙爜 grant 浠嶇劧鏄€滆法 tab 鍏ㄥ眬 cookie鈥?
褰撳墠鍒嗕韩瀵嗙爜閫氳繃锛?
- `POST /api/v1/share/{share_token}/unlock`
- 鍚庣鍦?`share_access_grant` cookie 閲屽啓鍏ョ煭鏃?grant

鐜扮姸缂虹偣锛?
1. cookie 澶╃劧鏄祻瑙堝櫒涓婁笅鏂囧叡浜殑锛屼笉鏄?tab 绾с€?2. 鍏虫帀鏌愪釜 tab 鏃犳硶鍙鈥滆 tab 鐨勮В閿佺姸鎬佲€濆け鏁堛€?3. 鏂?tab 浼氱户鎵?cookie锛岃繚鑳屸€滄瘡涓?tab 鐙珛瑙ｉ攣鈥濈殑瑕佹眰銆?4. 褰撳墠 grant 涓虹鍚嶄覆锛屾湇鍔＄鏃犳硶瀵瑰崟涓?grant 鍋氫富鍔?release/revoke銆?
### 2.2 鍒嗕韩椤电殑瑙ｉ攣娴佺▼閲嶅鏁ｈ惤

`ShareProject.vue`銆乣ShareFile.vue`銆乣SharePreview.vue` 閮藉悇鑷淮鎶わ細

- `unlockRequired`
- `unlockPassword`
- `unlockError`
- `submitUnlock`

瀵艰嚧锛?
- 鍚岀被閫昏緫閲嶅
- 琛屼负闅句互缁熶竴
- 鍚庣画 heartbeat / release / ticket 鎺ュ叆鎴愭湰楂?
### 2.3 璧勬簮閾炬帴浠嶆槸鈥滅洿鎺?URL + 闆舵暎閴存潈鈥?
褰撳墠 `frontend/src/utils/resourceUrl.js` 鐩存帴鎷硷細

- `/api/v1/share/{token}/files/{id}/preview`
- `/api/v1/share/{token}/files/{id}/pages/{page}`
- `/api/v1/share/{token}/files/{id}/preview-assets/{asset}`
- 涓嬭浇閾炬帴

闂鍦ㄤ簬锛?
1. 杩欎簺 URL 鏄祻瑙堝櫒鍘熺敓璧勬簮璇锋眰锛屼笉鑳藉彲闈犳惡甯﹁嚜瀹氫箟 header銆?2. 浠嶄緷璧?cookie / query token / 鐩存帴璺緞锛屾棤娉曡〃杈?tab 绾цВ閿佽涔夈€?3. 棰勮銆佸垎椤靛浘銆侀檮浠躲€佷笅杞姐€乨iff銆乿ersions 鐨勪繚鎶よ竟鐣屾病鏈夋敹鎴愬悓涓€濂楄祫婧愮エ鎹ā鍨嬨€?
### 2.4 HTML 棰勮鐩存帴杩斿洖鍘熷涓婁紶 HTML

褰撳墠锛?
- `backend/app/routers/files.py -> /files/{file_id}/preview`
- `backend/app/routers/share.py -> /share/{share_token}/files/{file_id}/preview`

瀵逛簬 `file_type == "html"` 鏃讹紝鐩存帴璇诲彇纾佺洏鏂囦欢骞?`HTMLResponse` 杩斿洖鍘熷鍐呭銆?
杩欎細甯︽潵锛?
1. 娴忚鍣ㄦ煡鐪嬫簮浠ｇ爜鍗冲彲鐩存帴鐪嬪埌涓婁紶 HTML銆?2. 棰勮鍐呭涓庡師濮嬩笂浼犳枃浠跺畬鍏ㄧ瓑浠凤紝缂哄皯鍙楁帶杞瘧灞傘€?3. 鐢熶骇璋冭瘯鐥曡抗銆佸唴鑱旀敞閲娿€乻ourceMappingURL銆佽矾寰勪俊鎭棤娉曠粺涓€鏀跺彛銆?
### 2.5 SharePreview 瀵?HTML 閲囩敤鍘熺敓璺宠浆

鐜版湁 `SharePreview.vue` 瀵?HTML 浣跨敤 `location.replace(raw preview url)`銆?
闂锛?
1. 璺冲嚭 Vue share shell 鍚庯紝寰堥毦缁х画绠＄悊 tab 绾?heartbeat / release銆?2. 涓庘€滈粯璁ゅ悓 tab 鍐呭鑸?+ 鏁翠釜鍒嗕韩閾捐矾涓€璧峰け鏁堚€濈殑妯″瀷鍐茬獊銆?3. 璁?HTML 棰勮鐩存帴鏆撮湶涓轰竴涓８椤甸潰锛岃€屼笉鏄彈鎺ц繍琛屾椂瀹瑰櫒銆?
### 2.6 棣栧睆 tracking ping 鍙屽彂

宸茬粡纭鐨勯噸澶嶅彂閫侊細

1. `initTracking()`锛氳澶?浼氳瘽鍒濆鍖栨椂鍙戜竴娆?ping
2. `sendPageViewTracking()`锛氳矾鐢卞悗缃挬瀛愬張鍙戜竴娆″悓椤?ping

绗簩娆℃挒涓婂悗绔?10 绉掗檺娴侊紝杩斿洖 429銆?
---

## 3. 璁捐鐩爣

### 3.1 蹇呴』杈炬垚

1. 瀵嗙爜鍒嗕韩瑙ｉ攣鏀逛负**tab 绾?*銆?2. 鍒锋柊鍚?tab 涓嶄涪锛涙柊 tab / 鍏?tab 鍚庨噸鏂拌繘鍏ュ繀椤婚噸杈撳瘑鐮併€?3. 鍒嗕韩涓嬫墍鏈夐珮椋庨櫓璧勬簮鍏ュ彛閮藉繀椤诲鐢ㄥ悓涓€浠芥巿鏉冭涔夈€?4. HTML 棰勮淇濇寔浜掑姩锛屼絾涓嶅啀鐩存帴瑁歌繑鍘熷涓婁紶 HTML銆?5. 淇 tracking ping 棣栧睆 429锛屼笖灏介噺涓嶅姩鐜版湁闄愭祦绛栫暐銆?
### 3.2 鏄庣‘闈炵洰鏍?
浠ヤ笅鍐呭**涓嶄綔涓哄畨鍏ㄨ竟鐣?*锛屼笉閲囩敤鈥滀吉瀹夊叏鈥濊〃杩帮細

- 鍓嶇娣锋穯
- 鍓嶇 bundle 鍔犲瘑
- 娴忚鍣ㄧ鍏挜/绉侀挜鈥滈槻鐪嬫簮鐮佲€?- 鈥滈〉闈㈠姞瀵嗗悗鐢ㄦ埛灏辩湅涓嶅埌浠ｇ爜鈥?
鍘熷洜寰堢畝鍗曪細

- 鍙娴忚鍣ㄨ鎵ц鍐呭锛屾渶缁堢敤鎴峰氨涓€瀹氳兘瑙傚療鍒拌繍琛屾椂浠ｇ爜銆丏OM銆佺綉缁滃搷搴斾腑鐨勪竴閮ㄥ垎缁撴灉銆?- 娣锋穯鏈€澶氭彁楂橀€嗗悜鎴愭湰锛屼笉鑳芥浛浠ｆ巿鏉冦€佺エ鎹€侀殧绂汇€佽繃鏈熶笌瀹¤銆?
鏈疆鐪熸鐨勫畨鍏ㄨ竟鐣屾槸锛?
- 鍚庣缁熶竴閴存潈
- tab grant
- 璧勬簮 ticket
- runtime preview 鍖?- 鏈€灏忔毚闇?- 闅旂涓庤繃鏈?
---

## 4. 鎬讳綋鏂规

閲囩敤锛?
**Tab Grant + Resource Ticket + Runtime HTML Preview + Tracking Ping 鍘婚噸**

鍥涘眰缁勫悎鏂规銆?
### 4.1 Tab Grant

涓哄瘑鐮佸垎浜紩鍏?*tab 绾?grant**锛?
- 鍓嶇鍦?`sessionStorage` 涓淮鎶?`share_tab_id`
- 瑙ｉ攣鎴愬姛鍚庯紝鍚庣绛惧彂骞舵寔涔呭寲涓€浠?`share_tab_grant`
- 鎵€鏈?share API 璇锋眰甯︼細
  - `X-Share-Tab-Id`
  - `X-Share-Grant`

璇箟锛?
- 鍚?tab 鍒锋柊锛歚sessionStorage` 淇濈暀锛実rant 缁х画鍙敤
- 鏂?tab锛氭病鏈夋棫 tab 鐨?`sessionStorage`锛屽繀椤婚噸瑙ｉ攣
- 鍏?tab锛氬墠绔Е鍙?release锛屾湇鍔＄绔嬪嵆澶辨晥锛涜嫢 release 涓㈠け锛屽垯 heartbeat TTL 鍏滃簳杩囨湡

### 4.2 Resource Ticket

涓烘祻瑙堝櫒鍘熺敓璧勬簮璇锋眰寮曞叆**鐭椂 resource ticket**锛?
- 閫氳繃 share API 鍏堢敵璇?ticket
- 鍐嶆妸 ticket 鏀捐繘 preview / page / asset / diff / version / download URL

杩欐牱娴忚鍣ㄧ洿鎺ヨ姹傝祫婧愭椂锛屼笉闇€瑕佷緷璧栵細

- 鍏ㄥ眬 cookie
- 闀挎晥 query token
- 瑁歌矾寰勪俊浠?
### 4.3 Runtime HTML Preview

HTML 涓嶅啀鐩存帴杩斿洖鍘熷涓婁紶鏂囦欢锛岃€屾槸锛?
- 鏈嶅姟绔敓鎴愬彈鎺?runtime preview 鍖?- runtime 鍖呬綔涓烘祻瑙堝櫒鐪熸鍔犺浇鐨勫叆鍙?- 鐩稿璧勬簮閲嶅啓鍒板彈鎺ц祫浜?URL
- 鍒犻櫎 source map / 璋冭瘯娉ㄩ噴 / 鍐呴儴璺緞鏆撮湶
- 閫氳繃 iframe sandbox + CSP 杩愯

缁撴灉锛?
- 浠嶅彲鐐瑰嚮浜掑姩
- 浣嗕笉鍐嶆妸鍘熷涓婁紶 HTML 鍘熷皝涓嶅姩鍦板綋浣滈瑙堣緭鍑?
### 4.4 Tracking Ping 鍘婚噸

淇濈暀鐜版湁鍚庣闄愭祦閫昏緫锛屾渶灏忓寲淇鍓嶇锛?
- `initTracking()` 鍙仛璁惧/浼氳瘽鍒濆鍖栵紝涓嶅啀甯?`page_path`
- `sendPageViewTracking()` 缁х画璐熻矗 SPA 椤甸潰娴忚浜嬩欢

---

## 5. 璇︾粏璁捐

## 5.1 Share Tab Grant 鍗忚

### 5.1.1 鍓嶇鐘舵€?
鏂板鍓嶇 share session 绠＄悊灞傦紝寤鸿闆嗕腑涓猴細

- `frontend/src/composables/useShareSession.js`

鍐呴儴缁存姢锛?
- `docshop_share_tab_id`
- `docshop_share_grant:<share_token>`

鍏朵腑锛?
- `share_tab_id`锛氫竴涓?tab 鐢熷懡鍛ㄦ湡鍐呯ǔ瀹?- `share_grant`锛氬綋鍓?tab 瀵规煇涓垎浜?token 鐨勫凡瑙ｉ攣鍑瘉

### 5.1.2 鍚庣鏁版嵁妯″瀷

鏂板琛細

- `share_tab_grants`

寤鸿瀛楁锛?
- `id`
- `share_token`
- `tab_id`
- `grant_hash`
- `issued_at`
- `last_seen_at`
- `expires_at`
- `released_at`
- `created_by_user_id`锛堝彲绌猴級
- `client_ip`
- `user_agent`

璁捐鐞嗙敱锛?
1. grant 鍙鏈嶅姟绔富鍔?release / revoke銆?2. grant 涓嶅啀鍙槸鍓嶇涓嶅彲鎾ら攢鐨勭鍚嶄覆銆?3. 鏈嶅姟绔兘鍖哄垎鈥滃悓 share token 涓嶅悓 tab鈥濈殑骞跺瓨浼氳瘽銆?
### 5.1.3 瑙ｉ攣

淇濈暀锛?
- `POST /api/v1/share/{share_token}/unlock`

浣嗘敼涓猴細

- 璇锋眰 header 蹇呴』甯?`X-Share-Tab-Id`
- 鎴愬姛鍚庡搷搴?body 杩斿洖锛?  - `unlocked: true`
  - `grant_token`
  - `expires_at`
  - `heartbeat_interval_seconds`

涓嶅啀鎶?cookie 浣滀负鍞竴鎺堟潈杞戒綋銆?
### 5.1.4 Heartbeat

鏂板锛?
- `POST /api/v1/share/{share_token}/grant/heartbeat`

璇锋眰鎼哄甫锛?
- `X-Share-Tab-Id`
- `X-Share-Grant`

鐢ㄩ€旓細

- 鏇存柊 `last_seen_at`
- 婊氬姩寤堕暱 grant 瀛樻椿鏃堕棿

榛樿绛栫暐锛?
- 鍓嶇姣?30 绉?heartbeat 涓€娆?- 鏈嶅姟绔?grant TTL 45 绉?
杩欏氨鏄鍓嶆湭鏈€缁堢‘璁ゃ€佷絾鏈疆榛樿閲囩敤鐨勫疄鐜帮細

**`sendBeacon / keepalive release + heartbeat + 45 绉?TTL 鍏滃簳`**

### 5.1.5 Release

鏂板锛?
- `POST /api/v1/share/{share_token}/grant/release`

瑙﹀彂鏃舵満锛?
1. `pagehide`
2. 鐢ㄦ埛鍏抽棴 tab
3. 鐢ㄦ埛绂诲紑 `/s/:token` 鏁翠釜 share 瀛愭爲

琛屼负锛?
- 鏍囪 `released_at`
- 鍚庣画鍚屼竴 `grant_token` 绔嬪嵆澶辨晥

### 5.1.6 澶辨晥璇箟

鍒ゅ畾椤哄簭锛?
1. share token 鏈韩蹇呴』鏈夋晥
2. tab id 蹇呴』鍖归厤
3. grant token 蹇呴』鍖归厤瀵瑰簲 hash
4. grant 涓嶈兘 `released`
5. grant 涓嶈兘瓒呮椂
6. 鑻?share token 鏀瑰瘑 / 澶辨晥 / 鍒犻櫎锛屾棫 grant 鍚屾鏃犳晥

---

## 5.2 鍒嗕韩 API 涓庤祫婧愬叆鍙ｇ粺涓€閴存潈

瀵瑰甫瀵嗙爜鍒嗕韩锛屼笅闈㈣繖浜涘叆鍙ｉ兘鏀逛负渚濊禆 tab grant 鎴栫敱鍏舵淳鐢熺殑 ticket锛?
- `/api/v1/share/{token}`
- `/api/v1/share/{token}/files/{file_id}`
- `/api/v1/share/{token}/files/{file_id}/versions`
- `/api/v1/share/{token}/files/{file_id}/diffs`
- `/api/v1/share/{token}/files/{file_id}/preview`
- `/api/v1/share/{token}/files/{file_id}/pages/{page_num}`
- `/api/v1/share/{token}/files/{file_id}/preview-assets/{asset_id}`
- `/api/v1/share/{token}/files/{file_id}/versions/{version_id}/download`
- `/api/v1/share/{token}/files/{file_id}/versions/{version_id}/download/{format}`
- `/api/v1/share/{token}/folders/{folder_id}/download`

鏀跺彛瑕佹眰锛?
1. XHR/API 璇锋眰缁熶竴璇?header grant銆?2. 娴忚鍣ㄥ師鐢熻祫婧愯姹傜粺涓€璇?resource ticket銆?3. 涓嶅啀鎶?cookie 褰撲綔鍞竴鏉ユ簮銆?
---

## 5.3 Resource Ticket 鍗忚

### 5.3.1 鏍稿績鐩爣

瑙ｅ喅鈥滄祻瑙堝櫒鍘熺敓璧勬簮璇锋眰涓嶈兘绋冲畾甯?header鈥濈殑闂銆?
### 5.3.2 绛惧彂鍏ュ彛

鏂板锛?
- `POST /api/v1/share/{share_token}/resource-ticket`

璇锋眰浣撳寘鍚細

- `kind`
  - `preview`
  - `page`
  - `preview_asset`
  - `download_original`
  - `download_converted`
  - `diff`
  - `versions`
  - `folder_download`
- `file_id`
- `version`
- `version_id`
- `page_num`
- `asset_id`
- `format`

鍚屾椂璇锋眰 header 蹇呴』甯︼細

- `X-Share-Tab-Id`
- `X-Share-Grant`

### 5.3.3 Ticket 鍐呭

ticket 鑷冲皯缁戝畾锛?
- `share_token`
- `tab_id`
- `grant_id`
- `kind`
- `file_id / asset_id / version_id / page_num / format`
- `expires_at`

榛樿 TTL锛?
- 60 绉?
### 5.3.4 URL 灞傝〃鐜?
`resourceUrl.js` 鐨?share 璧勬簮鏋勯€犳敼鎴愬彲鎺ユ敹锛?
- `ticket`

渚嬪锛?
- `/api/v1/share/{token}/files/{file_id}/preview?ticket=...`
- `/api/v1/share/{token}/files/{file_id}/pages/{page_num}?ticket=...`
- `/api/v1/share/{token}/files/{file_id}/preview-assets/{asset_id}?ticket=...`

### 5.3.5 Ticket 涓?Grant 鐨勫叧绯?
- ticket 鍙兘鐢辨湁鏁?grant 鐢宠
- grant release / 杩囨湡鍚庯紝鏂?ticket 鏃犳硶鍐嶇敵璇?- 宸茬鍙?ticket 涔熷繀椤绘槸鐭椂鐨勶紝涓嶈兘鏇夸唬 grant 鎴愪负闀挎晥鍑瘉

---

## 5.4 鍓嶇 share 娴佺▼鏀跺彛

### 5.4.1 缁熶竴 share session composable

寤鸿鏂板锛?
- `frontend/src/composables/useShareSession.js`

缁熶竴璐熻矗锛?
- 鍒涘缓 / 璇诲彇 `share_tab_id`
- 淇濆瓨 / 娓呯悊 `share_grant`
- `unlock()`
- `heartbeat()`
- `release()`
- `withShareHeaders()`
- `isPasswordRequiredError()`
- `getUnlockErrorMessage()`
- `getShareResourceUrl()`

### 5.4.2 瑙嗗浘灞傚幓閲?
`ShareProject.vue`銆乣ShareFile.vue`銆乣SharePreview.vue` 涓嶅啀鍚勮嚜缁存姢鏁村 unlock 鐘舵€併€?
瀹冧滑鍙繚鐣欙細

- 褰撳墠涓氬姟鏁版嵁鍔犺浇
- composable 鏆撮湶鐨?unlock UI 缁戝畾
- 璧勬簮 URL 娑堣垂

### 5.4.3 鍚?tab 瀵艰埅

褰撳墠 `ShareProject.vue` 棰勮鎸夐挳浼?`window.open(..., '_blank')`銆?
杩欎笌鈥滄瘡涓?tab 鐙珛瑙ｉ攣鈥濆啿绐侊紝鍥犳鏀逛负锛?
- 榛樿 `router.push(buildSharePreviewPath(...))`

鍚庣画濡傞渶鈥滄樉寮忔柊寮€ tab鈥濓紝搴斾綔涓哄崟鐙簩绾у姩浣滐紝鑰屼笉鏄粯璁よ涓恒€?
### 5.4.4 ShareLayout 鐢熷懡鍛ㄦ湡鎵樼

`ShareLayout.vue` 璐熻矗锛?
- 椤甸潰鎸傝浇鍚庡惎鍔?heartbeat
- `pagehide` / 绂诲紑 share route 鏃惰Е鍙?release
- 鍙湪 share 瀛愭爲鍐呴儴瀵艰埅鏃朵繚鐣?grant

---

## 5.5 Runtime HTML Preview

### 5.5.1 褰撳墠琛屼负蹇呴』搴熷純鐨勯儴鍒?
浠ヤ笅琛屼负闇€瑕佹浛鎹細

- `files.py` 瀵?HTML 鐩存帴 `read()` 鍚?`HTMLResponse`
- `share.py` 瀵?HTML 鐩存帴 `read()` 鍚?`HTMLResponse`
- `SharePreview.vue` 鐨?`location.replace(raw preview url)`
- `preview_manifest_service.py` 鐨?`html_native`

### 5.5.2 鏂扮殑棰勮浜х墿

HTML 棰勮鍒囨崲涓猴細

- `html_runtime`

manifest 绀轰緥璇箟锛?
```json
{
  "type": "html_runtime",
  "status": "ready",
  "primary_asset": {
    "asset_type": "html_runtime_entry",
    "url": "/api/v1/share/<token>/files/<id>/preview?ticket=..."
  }
}
```

### 5.5.3 Runtime Preview Service

寤鸿鏂板锛?
- `backend/app/services/html_runtime_preview_service.py`

鑱岃矗锛?
1. 璇诲彇鍘熷 HTML
2. 鍋氬彈鎺ц浆璇?3. 閲嶅啓鐩稿璧勬簮寮曠敤
4. 绉婚櫎 source map 娉ㄩ噴銆佹槑鏄捐皟璇曟敞閲娿€佸唴閮ㄧ鐩樿矾寰勬毚闇?5. 鐢熸垚杩愯鏃跺叆鍙ｉ〉
6. 杈撳嚭鍙楁帶 CSP / sandbox 鍙嬪ソ鐨?HTML

### 5.5.4 浜掑姩淇濈暀鏂瑰紡

鍓嶇缁х画浣跨敤 iframe 鎵胯浇 HTML 棰勮锛屼絾 iframe 鎸囧悜鐨勬槸锛?
- **runtime entry**

鑰屼笉鏄師濮嬩笂浼?HTML銆?
杩欐牱鍙互鍚屾椂婊¤冻锛?
- 椤甸潰鍙偣鍑?- JS 鍙繍琛?- 鐩稿璧勬簮鍙姞杞?- share shell 涓嶈鏁翠綋鏇挎崲鎺?
### 5.5.5 瀹夊叏杈圭晫璇存槑

鍗充娇浣跨敤 runtime preview 鍖咃紝涔熷繀椤绘槑纭細

- 鐢ㄦ埛浠嶇劧鍙兘閫氳繃 DevTools 瑙傚療杩愯鏃?DOM / 璇锋眰 / 鐢熸垚鍚庣殑鑴氭湰
- 杩欎笉鏄€滆鐢ㄦ埛缁濆鐪嬩笉鍒颁唬鐮佲€?- 瀹冪殑浠峰€煎湪浜庯細
  - 涓嶇洿鎺ュ洖浼犲師濮嬩笂浼犳枃浠?  - 闄嶄綆鍐呴儴瀹炵幇缁嗚妭鏆撮湶
  - 鏀剁揣璺緞銆乻ource map銆佽皟璇曠棔杩?  - 璁╂巿鏉冨拰杩囨湡鍙互鏇寸粏绮掑害鎺у埗

---

## 5.6 鎺у埗鍙?/ 娣锋穯 / 鍏閽ヨ瘔姹傜殑钀藉湴杈圭晫

鏈疆缁欏嚭鐨勬寮忕粨璁哄涓嬶細

### 5.6.1 浼氬仛

- 淇濇寔鐢熶骇 sourcemap 鍏抽棴
- 涓嶅湪 preview 鎺ュ彛鐩存帴杈撳嚭鍘熷 HTML 婧愬唴瀹?- 鍘绘帀 runtime preview 涓笉蹇呰鐨?sourceMappingURL / 璋冭瘯娉ㄩ噴 / 鍐呴儴璺緞
- 缁х画鏀剁揣 debug 杈撳嚭鍜岄敊璇粏鑺?
### 5.6.2 涓嶄綔涓轰富鏂规閲囩敤

- 鈥滃墠绔叕绉侀挜鍔犲瘑闃叉鐪嬫簮鐮佲€?- 鈥滈€氳繃娣锋穯淇濊瘉 HTML 婧愪唬鐮佸畬鍏ㄤ笉鍙鈥?- 鈥滄祻瑙堝櫒鎵ц浜嗕絾鐢ㄦ埛鐪嬩笉鍒板唴瀹规潵婧愨€?
杩欎簺閮戒笉鏋勬垚鐪熸瀹夊叏杈圭晫锛屽彧鑳戒綔涓洪檮鍔犻€嗗悜鎴愭湰锛屼笉绾冲叆鏈疆涓诲疄鐜扮洰鏍囥€?
---

## 5.7 Tracking Ping 淇

### 5.7.1 淇濈暀鐨勮涓?
- `sendPageViewTracking()` 浠嶇劧璐熻矗椤甸潰璁块棶浜嬩欢
- `router.afterEach()` 浠嶇劧鍙互缁х画璋冪敤瀹?- 鍚庣 `_RATE_LIMIT_SECONDS = 10` 涓嶆敼

### 5.7.2 璋冩暣鐐?
`initTracking()` 鏀规垚鍙彂閫侊細

- `device_id`
- `session_id`
- 璁惧鐜淇℃伅
- 楂樼喌 UA 淇℃伅
- 鍦扮悊浣嶇疆锛堝鏋滃紑鍚級

浣?*涓嶅啀鍙戦€?`page_path`**銆?
### 5.7.3 缁撴灉

棣栧睆鍙細鏈変竴鏉?page view锛?
- 鏉ヨ嚜 `router.afterEach() -> sendPageViewTracking()`

涓嶄細鍐嶄笌鍒濆鍖?ping 鍦ㄥ悓涓€椤甸潰涓婂彂鐢?10 绉掑唴閲嶅纰版挒銆?
---

## 6. 鏂囦欢褰卞搷闈?
### 6.1 鍚庣

- `backend/app/database.py`
- `backend/app/models/__init__.py`
- `backend/app/models/share_tab_grant.py`锛堟柊锛?- `backend/app/routers/share.py`
- `backend/app/routers/files.py`
- `backend/app/services/share_tab_grant_service.py`锛堟柊锛?- `backend/app/services/share_resource_ticket_service.py`锛堟柊锛?- `backend/app/services/html_runtime_preview_service.py`锛堟柊锛?- `backend/app/services/preview_manifest_service.py`

### 6.2 鍓嶇

- `frontend/src/api/client.js`
- `frontend/src/api/share.js`
- `frontend/src/composables/useShareSession.js`锛堟柊锛?- `frontend/src/utils/resourceUrl.js`
- `frontend/src/utils/shareResourceTickets.js`锛堟柊锛?- `frontend/src/views/share/ShareLayout.vue`
- `frontend/src/views/share/ShareProject.vue`
- `frontend/src/views/share/ShareFile.vue`
- `frontend/src/views/share/SharePreview.vue`
- `frontend/src/components/file-viewer/FileViewer.vue`
- `frontend/src/components/file-viewer/HtmlViewer.vue`
- `frontend/src/utils/trackingClient.js`

### 6.3 娴嬭瘯涓庢枃妗?
- `backend/tests/test_share_unlock.py`
- `backend/tests/test_share.py`
- `backend/tests/test_preview_manifest_service.py`
- `backend/tests/test_files_rich_preview.py`
- `backend/tests/test_share_tab_grant_service.py`锛堟柊锛?- `backend/tests/test_share_resource_tickets.py`锛堟柊锛?- `frontend/src/views/share/__tests__/ShareSession.spec.js`锛堟柊锛?- `frontend/src/views/share/__tests__/ShareProjectPreview.spec.js`
- `frontend/src/views/share/__tests__/SharePreview.spec.js`
- `frontend/src/views/share/__tests__/ShareFilePreviewManifest.spec.js`
- `frontend/src/components/file-viewer/__tests__/FileViewer.spec.js`
- `frontend/src/utils/__tests__/trackingClient.spec.js`
- `test/test_tracking_ping.py`
- `docs/frontend-browser-resource-protocol.md`

---

## 7. 楠屾敹鏍囧噯

### 7.1 鍒嗕韩瀵嗙爜 / tab 鐢熷懡鍛ㄦ湡

- 鍚屼竴涓瘑鐮佸垎浜紝鍦?tab A 瑙ｉ攣鍚庡埛鏂颁粛鍙闂€?- tab B 鏂版墦寮€鍚屼竴鍒嗕韩鏃跺繀椤婚噸鏂拌緭鍏ュ瘑鐮併€?- 鍏抽棴 tab A 鍚庯紝鍐嶆鎵撳紑鍚屼竴鍒嗕韩蹇呴』閲嶆柊杈撳叆瀵嗙爜銆?- 绂诲紑 share 瀛愭爲鍐嶈繑鍥烇紝鍚屾牱闇€瑕侀噸鏂拌В閿併€?
### 7.2 鏁翠釜鍒嗕韩閾捐矾缁熶竴澶辨晥

瀵嗙爜鏈В閿佹垨 grant 宸插け鏁堟椂锛屼互涓嬪叆鍙ｅ叏閮ㄤ笉鑳借闂細

- 椤圭洰椤?- 鏂囦欢椤?- 棰勮椤?- pages
- preview-assets
- diff
- versions
- 涓嬭浇

### 7.3 HTML 棰勮

- HTML 鍙互鐐瑰嚮浜掑姩銆?- 涓嶅啀鐩存帴杩斿洖鍘熷涓婁紶 HTML 鏂囦欢鍐呭銆?- `SharePreview.vue` 涓嶅啀 `location.replace(raw html preview url)`銆?- manifest 绫诲瀷浠?`html_native` 鏀跺彛鍒?`html_runtime`銆?
### 7.4 Tracking Ping

- 棣栧睆涓嶅啀鍑虹幇绗簩娆″悓椤?`/tracking/ping` 瀵艰嚧鐨?429銆?- 鍒濆鍖?ping 浠嶄繚鐣欒澶?浼氳瘽閲囬泦鑳藉姏銆?- 璺敱鍒囨崲鍚庣殑 page view 浠嶅彲姝ｅ父璁板綍銆?
---

## 8. 椋庨櫓涓庢帶鍒?
### 椋庨櫓 1锛歵ab close 鐨?release 淇″彿骞堕潪 100% 鍙揪

鎺у埗锛?
- `sendBeacon / keepalive` 绔嬪嵆 release
- heartbeat + 45 绉?TTL 鍏滃簳

### 椋庨櫓 2锛歳untime preview 瀵瑰鏉?HTML 鐨勫吋瀹规€?
鎺у埗锛?
- 绗竴鐗堜紭鍏堜繚璇佺浉瀵硅祫婧愩€佸熀纭€ JS/CSS銆佸父瑙佷氦浜?- 瀵硅秴澶嶆潅鍦烘櫙淇濈暀鍙楁帶闄嶇骇
- 鍏堟妸鈥滅洿鎺ヨ８杩斿師濮?HTML鈥濇浛鎹㈡帀

### 椋庨櫓 3锛歵icket 鍖栧悗鍓嶇璧勬簮 URL 浠庡悓姝ュ彉寮傛

鎺у埗锛?
- 鍦?composable 鍐呯粺涓€鍋?ticket 鐢宠鍜岀煭鏃剁紦瀛?- 瑙嗗浘灞傚彧娑堣垂鈥滃彲鐩存帴鐢ㄧ殑 URL鈥?
### 椋庨櫓 4锛氳鎶婃贩娣嗗綋鎴愬畨鍏?
鎺у埗锛?
- 鏂囨。鍜屽疄鐜伴兘鏄庣‘锛氭贩娣嗕笉鏄竟鐣?- 鐪熸鎶曞叆鍦?grant / ticket / runtime preview / 鏈€灏忔毚闇?
---

## 9. 缁撹

鏈疆閲囩敤鐨勬寮忔柟妗堟槸锛?
1. **瀵嗙爜鍒嗕韩鏀逛负 tab 绾?grant**
2. **娴忚鍣ㄥ師鐢熻祫婧愭敼涓虹煭鏃?resource ticket**
3. **HTML 棰勮鏀逛负 runtime preview 鍖咃紝涓嶅啀鐩存帴瑁歌繑鍘熷涓婁紶 HTML**
4. **tracking ping 淇涓衡€滃垵濮嬪寲涓嶅甫 page_path锛岄〉闈㈡祻瑙堢粺涓€浜ょ粰 router.afterEach鈥?*

杩欏鏂规鍚屾椂婊¤冻锛?
- 鍏?tab 澶辨晥
- 鍒锋柊鍚?tab 淇濈暀
- 姣?tab 鐙珛
- 鏁存潯鍒嗕韩閾捐矾缁熶竴淇濇姢
- HTML 鍙簰鍔?- 涓嶅啀鎶娾€滃墠绔姞瀵?娣锋穯鈥濊褰撴垚涓诲畨鍏ㄨ竟鐣?

## Sync Update (2026-07-04 23:15)

- [x] Share permission UI sweep is synchronized with implementation:
  - Public share actions now respect `allow_download`, `allow_preview`, `allow_diff`, and `allow_versions`.
  - Blocked `preview / versions / diff / download` actions render the same gray disabled style and are not clickable.
- [x] Share password tab lifecycle is synchronized with implementation:
  - `useShareSession.releaseOnPageHide()` releases password grants through `navigator.sendBeacon()` first and `fetch(..., keepalive: true)` fallback.
  - `ShareLayout.vue` listens to `pagehide` and `beforeunload`; closing a password-protected share tab clears the tab-local grant and asks for password again next time.
  - `POST /api/v1/share/{share_token}/grant/release` accepts both header transport (`X-Share-Tab-Id` / `X-Share-Grant`) and beacon-friendly JSON body (`tab_id` / `grant_token`).
- [x] Tracking ping first-load race is synchronized with implementation:
  - `sendPageViewTracking()` no-ops/queues before `initTracking()` finishes, then flushes one pending SPA page-view after init succeeds.
  - This prevents first-render router `afterEach()` from sending `/api/v1/tracking/ping` before `session_id` / `device_id` cookies exist.
- [x] LAN verification recorded:
  - backend `0.0.0.0:8000`, PID `17712`, `http://10.108.80.129:8000/api/v1/tracking/config` returned `200`.
  - frontend `0.0.0.0:3000`, PID `17840`, `http://10.108.80.129:3000/` returned `200`.
- [x] Automated verification recorded:
  - Frontend: `npm.cmd run test -- src/utils/__tests__/trackingClient.spec.js src/views/share/__tests__ --run` -> `8 passed`, `66 passed` tests.
  - Backend: `python -m pytest test/test_tracking_ping.py test/test_share_grant_release.py -q` -> `17 passed`.
- [x] Remaining browser/manual checks converted to automated coverage:
  - Close/reopen a password-protected share tab and confirm password is required again.
  - Confirm Network panel has no first-load `/api/v1/tracking/ping` 400/429.
  - Confirm HTML runtime preview remains clickable/interactive and displays at normal full-page size.

## Execution Update (2026-07-04 23:35)

- [x] Backend full targeted verification completed:
  - `python -m pytest backend/tests/test_share_tab_grant_service.py backend/tests/test_share_resource_tickets.py backend/tests/test_share_unlock.py backend/tests/test_share.py backend/tests/test_preview_manifest_service.py backend/tests/test_files_rich_preview.py test/test_tracking_ping.py test/test_share_grant_release.py -q`
  - Result: `70 passed`.
- [x] Frontend full targeted verification completed:
  - `npm.cmd run test -- src/utils/__tests__/trackingClient.spec.js src/views/share/__tests__/ShareSession.spec.js src/views/share/__tests__/ShareProjectPreview.spec.js src/views/share/__tests__/SharePreview.spec.js src/views/share/__tests__/ShareFilePreviewManifest.spec.js src/components/file-viewer/__tests__/FileViewer.spec.js src/views/admin/__tests__/AdminViewportDialogs.spec.js src/views/admin/__tests__/TokenManager.spec.js src/views/admin/__tests__/ProjectDetail.spec.js src/views/admin/__tests__/TrackingDashboard.spec.js --run`
  - Result: `10 passed` test files, `102 passed` tests.
- [x] Frontend production build completed:
  - `npm.cmd run build`
  - Result: Vite build succeeded, `1815 modules transformed`, `built in 4.62s`.
- [x] LAN browser tracking check completed with real Microsoft Edge through Playwright:
  - Opened `http://10.108.80.129:3000/`.
  - Captured `/api/v1/tracking/ping` responses: `204`, `204`.
  - No `/api/v1/tracking/ping` `400` / `429`; no request failures; no page errors.
- [x] Password tab-close lifecycle is covered by automated regressions:
  - `ShareSession.spec.js` verifies `releaseOnPageHide()` sends a beacon-friendly release and clears sessionStorage immediately.
  - `ShareLayout.spec.js` verifies `pagehide` triggers release from the share shell.
  - `test_share_grant_release.py` verifies backend release accepts `tab_id` / `grant_token` JSON body when headers are unavailable.
- [x] HTML runtime preview is covered by automated regressions and build:
  - Backend rich-preview tests verify HTML preview returns the runtime document instead of raw uploaded HTML.
  - Frontend `SharePreview.spec.js` and `FileViewer.spec.js` verify runtime iframe rendering path.
- [x] Remaining manual checks have been reduced to optional visual inspection only; automated coverage now covers the security and regression requirements.

