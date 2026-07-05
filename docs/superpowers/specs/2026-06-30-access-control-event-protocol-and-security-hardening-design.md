# 2026-06-30 璁块棶鎺у埗鍐呮牳銆佹祻瑙堝櫒璧勬簮鍗忚銆佷簨浠堕€氶亾浜屾湡涓庡畨鍏ㄥ姞鍥鸿璁?
## 1. 鑳屾櫙涓庣洰鏍?
鏈疆璁捐鎵挎帴鍓嶄竴杞凡瀹屾垚鐨勪袱椤瑰熀纭€宸ヤ綔锛?
1. 宸插缓绔嬬粺涓€ SSE 浜嬩欢閫氶亾锛屽苟瀹屾垚 `config` 涓婚鎺ュ叆銆?2. 宸插缓绔?`frontend/src/utils/resourceUrl.js`锛屽垵姝ョ粺涓€娴忚鍣ㄨ祫婧?URL 鎷兼帴鍏ュ彛銆?
鐢ㄦ埛鏈疆鏂板鐩爣鏈?4 涓細

1. 鎶?`resourceUrl` 杩涗竴姝ヤ笅娌夋垚鈥滃墠绔祻瑙堝櫒璧勬簮鍗忚灞傗€濈殑璇存槑涓庤鑼冦€?2. 鎶婂悗鍙扮粺涓€浜嬩欢閫氶亾鍐嶆帴鍏ヤ竴绫荤湡瀹炰笟鍔′簨浠讹紝褰㈡垚绗簩涓惤鍦扮偣銆?3. 缁嗗寲鏂囦欢璁块棶鏉冮檺锛屾敮鎸佸瘑鐮佹煡鐪嬨€佺櫥褰曟煡鐪嬨€佺敤鎴风粍鏌ョ湅绛夋ā寮忥紝骞惰ˉ榻愰槻瓒婃潈銆?4. 瀵圭郴缁熸暣浣撳仛杩涗竴姝ュ畨鍏ㄥ姞鍥猴紝鍖呮嫭鍙嶆墥銆侀棬绂併€佽闂毚闇查潰鏀剁缉銆侀瑙堥摼璺姞瀵嗕笌闃叉互鐢ㄣ€?
鐢变簬杩?4 椤硅法瓒婃潈闄愭ā鍨嬨€佽祫婧愯闂崗璁€佸疄鏃朵簨浠躲€佺郴缁熷畨鍏ㄥ熀绾?4 涓眰闈紝鐩存帴涓€娆℃€у疄鐜伴闄╄繃楂橈紝鍥犳閲囩敤 **涓夋湡閫掕繘寮忔柟妗?*锛?
- **Phase 1锛氭潈闄愪笌闃茶秺鏉冨唴鏍?*
- **Phase 2锛氭祻瑙堝櫒璧勬簮鍗忚灞?+ 浜嬩欢閫氶亾浜屾湡**
- **Phase 3锛氭暣浣撳畨鍏ㄥ姞鍥轰笌鏆撮湶闈㈡敹缂?*

鏈璁℃枃妗ｈ緭鍑虹殑鏄笁鏈熸€荤翰銆佽竟鐣屻€侀噷绋嬬涓庨獙鏀舵爣鍑嗭紝涓嶅湪鏈疆鐩存帴杩涘叆瀹炵幇銆?
## 2. 褰撳墠鐜扮姸

缁撳悎褰撳墠浠撳簱浠ｇ爜锛屽凡鏈夊熀纭€涓庨棶棰樺涓嬨€?
### 2.1 璁よ瘉涓庤鑹?
- `backend/app/deps/auth.py`
  - `get_current_user` 鐩墠鏀寔涓ょ璁よ瘉鏉ユ簮锛?    - `Authorization: Bearer ...`
    - 娴忚鍣ㄥ師鐢熻祫婧愯姹備娇鐢?query token锛歚auth_token` / `access_token` / `token`
  - `get_current_admin` 鐩墠浠呭熀浜?`current_user.role == "admin"` 鍒ゆ柇銆?
鐜扮姸闂锛?
- 閫傚悎褰撳墠鍔熻兘锛屼絾鏃犳硶琛ㄨ揪鈥滅櫥褰曞彲鐪?/ 缁勫唴鍙湅 / 瀵嗙爜鍙湅 / 鏌愬姩浣滃彲鍋氭煇鍔ㄤ綔涓嶅彲鍋氣€濊繖绫荤粏绮掑害鎺堟潈銆?- query JWT 鍙洿鎺ユ毚闇插湪娴忚鍣ㄨ祫婧?URL 涓婏紝鍚庣画搴旈€愭鏀舵暃涓烘洿鐭椂銆佹洿灏忔潈闄愮殑璧勬簮璁块棶绁ㄦ嵁銆?
### 2.2 鍒嗕韩涓庢枃浠惰闂?
- `backend/app/models/share_token.py`
  - 褰撳墠宸叉湁锛歚resource_type`銆乣allow_download`銆乣max_views`銆乣max_downloads`銆乣expires_at`
  - 鐩墠娌℃湁瀹屾暣鐨勶細
    - 鐧诲綍闂ㄧ
    - 鐢ㄦ埛缁勯棬绂?    - 鎸佷箙鍖栧瘑鐮侀棬绂?    - 棰勮 / 涓嬭浇 / diff / versions 缁嗙矑搴﹀姩浣滄潈闄?
- `backend/app/routers/share.py`
  - 鐩墠瀛樺湪 `_legacy_share_passwords: dict[str, str] = {}`
  - 灞炰簬杩涚▼鍐呬复鏃跺瘑鐮佸瓨鍌紝涓嶅彲鎸佷箙鍖栵紝涔熶笉閫傚悎浣滀负鍚庣画姝ｅ紡鏉冮檺妯″瀷鍩虹銆?
鐜扮姸闂锛?
- share 閾捐矾鏄綋鍓嶆渶瀹规槗鍑虹幇瓒婃潈涓庢梺璺闂殑闂鐐广€?- 鏉冮檺鍒ゆ柇鏁ｅ湪澶氫釜 endpoint锛岀己灏戠粺涓€鎺堟潈鍐崇瓥灞傘€?
### 2.3 浜嬩欢閫氶亾

- `backend/app/routers/events.py`
  - 宸叉湁 topic锛歚config`銆乣announcements`銆乣tracking`銆乣tasks`
  - 鍏朵腑 `config` 宸插畬鎴愮湡瀹炴帴鍏ャ€?  - `announcements` / `tracking` 杩樼己灏戝畬鏁翠笟鍔″彂甯冮摼璺€?
鐜扮姸闂锛?
- 缁熶竴浜嬩欢鍗忚宸茬粡鏈変簡锛屼絾涓氬姟灞傝繕鍙湁閰嶇疆鐑悓姝ヤ竴涓惤鍦扮偣銆?- 闇€瑕佷竴涓浜屼笟鍔¤惤鐐癸紝璇佹槑杩欐潯閫氶亾涓嶆槸鈥滆缃〉涓撶敤鏈哄埗鈥濄€?
### 2.4 娴忚鍣ㄨ祫婧?URL

- `frontend/src/utils/resourceUrl.js` 宸插瓨鍦ㄣ€?- 鍘?`assetUrl.js` / `cover.js` / `preview.js` 宸插紑濮嬪悜缁熶竴 helper 鏀跺彛銆?
鐜扮姸闂锛?
- 褰撳墠杩樻槸鈥滅粺涓€ helper鈥濓紝杩樹笉鏄畬鏁寸殑鈥滄祻瑙堝櫒璧勬簮鍗忚灞傗€濄€?- 缂哄皯姝ｅ紡鏂囨。璇存槑锛?  - 鍝簺 URL 灞炰簬娴忚鍣ㄧ洿杩炶祫婧?  - 鍝簺 URL 灞炰簬 XHR / API
  - 涓嶅悓璧勬簮璺緞濡備綍甯﹁璇?  - 鏈潵濡備綍浠?query JWT 杩佺Щ鍒扮煭鏃剁エ鎹?
### 2.5 瀹夊叏鍩虹嚎

- `backend/app/middlewares/security_headers.py` 宸叉湁鍩虹瀹夊叏澶淬€?- 浣嗛瑙?HTML 鍦烘櫙浠嶅彲鑳戒负鍏煎鎬т繚鐣欒緝瀹芥澗绛栫暐銆?
鐜扮姸闂锛?
- 浠嶇己灏戠粺涓€鐨勬枃浠惰闂畨鍏ㄥ熀绾匡細
  - 闃叉棰勮椤垫嬁鍒拌秴鑼冨洿璧勬簮
  - 闃叉涓嬭浇 / 棰勮 / diff / 椤靛浘 / asset 閾捐矾鏉冮檺涓嶄竴鑷?  - 闃叉 query token 琚暱鏈熷鐢?  - 闃叉鎭舵剰鑴氭湰銆佹壒閲忔姄鍙栥€佹參閫熷埛鍙栫瓑婊ョ敤

## 3. 璁捐缁撹

閲囩敤 **鈥滃簳搴у厛琛屻€佸崗璁浜屻€佸鍥村姞鍥虹涓夆€?* 鐨勯『搴忋€?
### 鏂规閫夋嫨鐞嗙敱

#### 鏂规 A锛氬厛鍋氭潈闄愬唴鏍革紝鍐嶅仛鍗忚涓庡畨鍏ㄥ澹筹紙閲囩敤锛?
浼樼偣锛?
- 鍏堣В鍐斥€滆皝鑳界湅銆佽兘鐪嬩粈涔堛€佽兘涓嬭浇浠€涔堛€佸湪鍝簺鍏ュ彛閮戒竴鑷粹€濄€?- 鍚庣画璧勬簮 URL銆佷簨浠舵帹閫併€佸畨鍏ㄥ姞鍥洪兘鏈夌ǔ瀹氳竟鐣屽彲渚濊禆銆?- 鏀归€犻『搴忔竻鏅帮紝鍥炲綊鎴愭湰鍙帶銆?
缂虹偣锛?
- 绗竴闃舵浼氬姩鍒版巿鏉冭竟鐣屽拰閮ㄥ垎鏁版嵁妯″瀷锛岀煭鏈熸劅鐭ヤ笉濡傜洿鎺ュ仛 UI 鎴栧弽鎵掓槑鏄俱€?
#### 鏂规 B锛氬厛鍋氳祫婧愬崗璁眰涓庡墠绔儹鏇存柊

浼樼偣锛?
- 鐢ㄦ埛鑳芥洿蹇湅鍒扳€滄枃妗ｅ寲鈥濆拰鈥滅浜屼笟鍔′簨浠舵帴鍏モ€濈殑缁撴灉銆?
缂虹偣锛?
- 濡傛灉鏉冮檺妯″瀷娌＄珛浣忥紝鍙槸鎶婂綋鍓嶄笉涓€鑷寸殑琛屼负鎹簡涓€涓３缁х画鏆撮湶銆?
#### 鏂规 C锛氬厛鍋氬畨鍏ㄥ澹充笌鍙嶆墥

浼樼偣锛?
- 鐪嬭捣鏉ユ渶鈥滃畨鍏ㄥ己鍖栤€濄€?
缂虹偣锛?
- 娌℃湁缁熶竴鎺堟潈鍐呮牳鏃讹紝澶栧洿闄愬埗寰堝鏄撹鍐呴儴璺緞宸紓缁曡繃銆?- 寰堝鈥滃姞瀵嗛〉闈⑩€濃€滃墠绔繚鎶ゆ簮鐮佲€濈殑鍋氭硶鏀剁泭浣庛€佺淮鎶ゆ垚鏈珮銆?
### 鏈€缁堥『搴?
1. **Phase 1锛氱粺涓€璁块棶鎺у埗涓庨槻瓒婃潈**
2. **Phase 2锛氭祻瑙堝櫒璧勬簮鍗忚灞?+ 鐪熷疄涓氬姟浜嬩欢鎺ュ叆**
3. **Phase 3锛氬畨鍏ㄥ熀绾裤€佸弽鎵掋€侀棬绂併€佺エ鎹寲涓庢毚闇查潰鏀剁缉**

## 4. 鍏ㄥ眬璁捐鍘熷垯

### 4.1 鏈嶅姟绔巿鏉冩槸鐪熸杈圭晫

鍓嶇鎻愮ず銆佹寜閽樉闅愩€侀〉闈㈠姞瀵嗐€佷唬鐮佹贩娣嗛兘涓嶈兘鏇夸唬鏈嶅姟绔巿鏉冦€傜湡姝ｈ竟鐣屽彧鑳藉湪鏈嶅姟绔姹傚叆鍙ｄ笌璧勬簮鍑哄彛涓婂疄鐜般€?
### 4.2 鎺堟潈鎸夆€滃姩浣溾€濊€屼笉鏄寜鈥滈〉闈⑩€濆畾涔?
蹇呴』鎶婃潈闄愭媶鎴愬姩浣滐細

- `view_metadata`
- `view_preview`
- `view_page_asset`
- `view_diff`
- `view_versions`
- `download_original`
- `download_converted`
- `manage_share`
- `manage_policy`

杩欐牱 `/files/*` 鍜?`/share/*` 鎵嶈兘鍏变韩鍚屼竴濂楀垽鏂€昏緫銆?
### 4.3 娴忚鍣ㄨ祫婧?URL 涓?API URL 鍒嗗眰

- `src/api/*` 缁х画璐熻矗涓氬姟 API 璇锋眰銆?- `resourceUrl` 璐熻矗鈥滅粰娴忚鍣ㄧ洿鎺ヨ闂殑璧勬簮鍏ュ彛鈥濄€?- 鍚庣画鍐嶅悜涓婃娊璞′负鈥滄祻瑙堝櫒璧勬簮鍗忚灞傗€濓紝鏄庣‘璧勬簮绫诲瀷銆佽璇佹惡甯︽柟寮忋€佺紦瀛樿鍒欏拰瀹夊叏杈圭晫銆?
### 4.4 浜嬩欢閫氶亾鍙帹閫佸彉鍖栵紝涓嶄紶鏁忔劅瀹炰綋

浜嬩欢鐢ㄤ簬鈥滈€氱煡鍒锋柊鈥濇垨鈥滈€氱煡鍙戠敓浜嗕粈涔堚€濓紝涓嶄綔涓烘晱鎰熷畬鏁存暟鎹笅鍙戦€氶亾銆傛晱鎰熸垨瀹屾暣瀹炰綋浠嶇敱鏅€氭巿鏉?API 鎷夊彇銆?
### 4.5 瀹夊叏寮哄寲浼樺厛鍋氣€滄渶灏忔毚闇测€濆拰鈥滅煭鏃舵巿鏉冣€?
鐢ㄦ埛鎻愬埌鈥滈槻姝㈡簮鐮佽鍒嗘瀽浠庤€屾敾鍑荤綉绔欌€濓紝鐪熷疄鏈夋晥鐨勬柟鍚戜笉鏄墠绔姞瀵嗭紝鑰屾槸锛?
- 涓嶅湪鍓嶇鏆撮湶涓嶈鏆撮湶鐨勫唴閮ㄧ粨鏋?- 缂╃煭璧勬簮鎺堟潈瀵垮懡
- 闄愬埗璧勬簮浣滅敤鍩?- 鍔犲己璁块棶鎺у埗涓庡璁?- 鍏抽棴鐢熶骇 source map / 璋冭瘯鍏ュ彛 / 澶氫綑閿欒缁嗚妭

## 5. 缁熶竴鏋舵瀯钃濆浘

鏈涓夋湡鏈€缁堣钀芥垚 4 涓彲澶嶇敤鍩哄骇銆?
### 5.1 璁块棶鎺у埗鍐崇瓥灞?
鏂板缁熶竴鎺堟潈鏈嶅姟锛屽缓璁懡鍚嶄负锛?
- `backend/app/services/access_control_service.py`

鍏跺澶栨毚闇茬粺涓€鍐崇瓥鎺ュ彛锛?
- 杈撳叆锛歚subject`銆乣resource`銆乣action`銆乣context`
- 杈撳嚭锛歚allow / deny`銆乣reason`銆乣derived_scope`

鍏朵腑锛?
- `subject`锛氬尶鍚嶇敤鎴枫€佺櫥褰曠敤鎴枫€佺鐞嗗憳銆佺敤鎴风粍鎴愬憳銆佸凡閫氳繃瀵嗙爜鎸戞垬鑰呫€佹寔鏈夋晥 share token 鐨勮闂€?- `resource`锛歱roject / file / version / diff / preview_asset / page_asset
- `action`锛氳 4.2
- `context`锛歴hare token銆佸瘑鐮佽В閿佺姸鎬併€佽姹傛潵婧愩€侀€熺巼闄愬埗鐘舵€佺瓑

鎵€鏈夐珮椋庨櫓璧勬簮鍨嬫帴鍙ｆ渶缁堥兘搴旀敹鍙ｅ埌杩欏眰鍐崇瓥锛?
- `/api/v1/files/*`
- `/api/v1/share/*`
- 棰勮椤?- 椤靛浘
- preview asset
- diff
- 鐗堟湰涓嬭浇

### 5.2 娴忚鍣ㄨ祫婧愬崗璁眰

鍓嶇涓嶆槸鍙彁渚涗竴缁?helper锛岃€屾槸瀹氫箟涓€灞傚崗璁細

- 璧勬簮鍒嗙被
- URL 缁撴瀯
- 璁よ瘉鎼哄甫鏂瑰紡
- 娴忚鍣ㄨ闂柟寮?- 澶辨晥澶勭悊
- 鍚庣画杩佺Щ绛栫暐

寤鸿淇濈暀 `frontend/src/utils/resourceUrl.js` 浣滀负瀹炵幇鍏ュ彛锛屽啀琛ヤ竴浠芥寮忚鏄庢枃妗ｏ細

- `docs/frontend-browser-resource-protocol.md`

璇ユ枃妗ｅ湪 Phase 2 瀹為檯浜у嚭銆?
### 5.3 缁熶竴浜嬩欢閫氶亾

鐜版湁 SSE 閫氶亾缁х画浣滀负鍏ㄥ眬鍗曞悜鎺ㄩ€佸叆鍙ｏ細

- topic
- event type
- envelope
- reconnect
- topic 鏉冮檺

绗簩钀藉湴鐐归粯璁ら€夋嫨 **`announcements`**锛屽師鍥狅細

- 鏈夌湡瀹炲墠鍙颁笟鍔′环鍊笺€?- 鏇存柊棰戠巼閫備腑锛屼究浜庨獙璇佷簨浠跺崗璁€?- 涓嶉渶瑕佸紩鍏ラ噸鍨嬮暱浠诲姟妯″瀷銆?
`tracking` 浣滀负 Phase 2 鍚岄€氶亾鍙鐢ㄧ殑涓嬩竴鍊欓€変富棰橈紝涓嶅己琛屼笌鍏憡涓€骞堕鍙戙€?
### 5.4 瀹夊叏鍩虹嚎灞?
鍥寸粫璧勬簮璁块棶缁х画鍙犲姞缁熶竴瀹夊叏鍩虹嚎锛?
- 璁块棶閫熺巼闄愬埗
- 璧勬簮鐭椂绁ㄦ嵁
- 瀹夊叏鍝嶅簲澶翠笌棰勮闅旂
- 瀹¤鏃ュ織
- 鐢熶骇鐜璋冭瘯闈㈡敹缂?- 閿欒杈撳嚭鑴辨晱

## 6. Phase 1锛氭潈闄愪笌闃茶秺鏉冨唴鏍?
### 6.1 鐩爣

寤虹珛鍙互琛ㄨ揪鈥滃瘑鐮佹煡鐪?/ 鐧诲綍鏌ョ湅 / 鐢ㄦ埛缁勬煡鐪?/ 鍔ㄤ綔绾ф潈闄愨€濈殑缁熶竴鎺堟潈搴曞骇锛屽苟鎶婇珮椋庨櫓鏂囦欢璁块棶閾捐矾鏀跺彛鍒板悓涓€濂楀垽鏂€昏緫銆?
### 6.2 璁捐鑼冨洿

#### 绾冲叆鑼冨洿

- 鐢ㄦ埛缁勬ā鍨?- 璧勬簮璁块棶绛栫暐妯″瀷
- share / file / preview / download / diff / versions 缁熶竴鍔ㄤ綔鏉冮檺
- 缁熶竴鎺堟潈鏈嶅姟
- 楂橀闄╄祫婧愭帴鍙ｆ敹鍙?- 瀵嗙爜闂ㄧ鎸佷箙鍖?- 闃茶秺鏉冮敊璇鐞嗕笌瀹¤璁板綍

#### 涓嶇撼鍏ヨ寖鍥?
- 涓嶅湪绗竴闃舵鐩存帴涓婂鏉傚瀹炰緥鍒嗗竷寮忔潈闄愮紦瀛?- 涓嶅仛缁勭粐绾у鏉傚眰绾ф潈闄愮郴缁?- 涓嶅仛鍓嶇澶ц妯℃潈闄愮鐞?UI 閲嶅啓

### 6.3 鏁版嵁妯″瀷

寤鸿鏂板鎴栨墿灞曚互涓嬫ā鍨嬨€?
#### A. 鐢ㄦ埛缁?
- `user_groups`
  - `id`
  - `name`
  - `code`
  - `description`
  - `is_active`
- `user_group_members`
  - `group_id`
  - `user_id`
  - `created_at`

#### B. 璧勬簮璁块棶绛栫暐

寤鸿鏂板 `resource_access_policies`锛?
- `resource_type`锛歚project | file | version`
- `resource_id`
- `visibility`
  - `inherit`
  - `private`
  - `login_required`
  - `password_required`
  - `groups_required`
  - `public`
- `password_hash`
- `password_hint`
- `allow_preview`
- `allow_download_original`
- `allow_download_converted`
- `allow_diff`
- `allow_versions`
- `created_by`
- `updated_by`
- `updated_at`

閰嶅鏂板锛?
- `resource_access_groups`
  - `policy_id`
  - `group_id`

璇存槑锛?
- `inherit` 鍏佽 file/version 榛樿缁ф壙涓婂眰 project 绛栫暐锛岄伩鍏嶆瘡涓枃浠跺崟鐙厤缃€?- `private` 琛ㄧず浠呰祫婧愭嫢鏈夎€?/ 椤圭洰鍐呴儴鏃㈡湁鏉冮檺涓讳綋鍙闂€?- `groups_required` 琛ㄧず蹇呴』鐧诲綍涓斿睘浜庢巿鏉冪粍銆?- `password_required` 鍙笌鐧诲綍鎬佸舰鎴愮粍鍚堢害鏉燂紝鍏蜂綋鐢辩瓥鐣ュ瓧娈垫槑纭€?
#### C. Share token 鎵╁睍

鍦ㄧ幇鏈?`share_tokens` 鍩虹涓婁繚鐣欙細

- `expires_at`
- `max_views`
- `max_downloads`
- `allow_download`

骞舵柊澧?/ 瑙勮寖锛?
- `allow_preview`
- `allow_diff`
- `allow_versions`
- `require_login`
- `password_hash`
- `password_hint`
- `policy_mode`
  - `inherit_resource_policy`
  - `override_with_token_policy`

璁捐鎰忓浘锛?
- **璧勬簮璁块棶绛栫暐** 鍐冲畾璧勬簮榛樿濡備綍琚湅瑙併€?- **share token** 鍐冲畾鏌愪釜澶栭摼瀹炰緥濡備綍闄勫姞鏈夋晥鏈熴€佹鏁般€佽鐩栬鍒欍€?
### 6.4 缁熶竴鎺堟潈鍒ゅ畾妯″瀷

鎺堟潈鍒ゅ畾缁熶竴鎸夛細

`Subject + Resource + Action + Context -> Decision`

鍒ゅ畾椤哄簭寤鸿涓猴細

1. 绠＄悊鍛樼煭璺斁琛?2. 璧勬簮瀛樺湪鎬т笌褰掑睘鏍￠獙
3. 鍐呴儴鎷ユ湁鑰?/ 椤圭洰鎴愬憳鏃㈡湁鏉冮檺鏍￠獙
4. 璧勬簮璁块棶绛栫暐鏍￠獙
5. share token 浣滅敤鍩熶笌閰嶉鏍￠獙
6. 鐧诲綍闂ㄧ鏍￠獙
7. 瀵嗙爜闂ㄧ鏍￠獙
8. 鐢ㄦ埛缁勯棬绂佹牎楠?9. 鍔ㄤ綔绾?allow/deny 鏍￠獙
10. 瀹¤璁板綍涓庢嫆缁濆師鍥犵粺涓€杈撳嚭

### 6.5 Phase 1 棣栨壒蹇呴』鏀跺彛鐨勮矾鐢?
閲嶇偣涓嶆槸涓€娆¤鐩栨墍鏈夋櫘閫?CRUD锛岃€屾槸浼樺厛鏀跺彛鎵€鏈夆€滃彲褰㈡垚璧勬簮娉勯湶鈥濈殑鍑哄彛锛?
- `/api/v1/files/{file_id}/preview`
- `/api/v1/files/{file_id}/pages/{page_num}`
- `/api/v1/files/{file_id}/preview-assets/{asset_id}`
- `/api/v1/files/{file_id}/download`
- `/api/v1/files/{file_id}/versions/{version_id}/download`
- `/api/v1/files/{file_id}/versions/{version_id}/download/{format}`
- `/api/v1/files/{file_id}/versions`
- `/api/v1/files/{file_id}/diffs`
- `/api/v1/share/{share_token}/...` 鍏ㄩ摼璺悓绫昏祫婧愬嚭鍙?
### 6.6 瀵嗙爜闂ㄧ璁捐

褰撳墠 `share.py` 鐨勫唴瀛樺瘑鐮佹柟妗堝繀椤绘窐姹帮紝缁熶竴鏀逛负锛?
- 鎸佷箙鍖?hash 瀛樺偍
- 鏈嶅姟绔?challenge 鏍￠獙
- 鏈夐檺鏈熻В閿佹€?- 灏濊瘯娆℃暟闄愬埗
- 鍙璁?
寤鸿鎺ュ彛褰㈡€侊細

- `POST /api/v1/share/{share_token}/unlock`
- 杩斿洖鐭椂 access grant / unlock session

璇存槑锛?
- 绗竴闃舵鍏堝厑璁歌繖涓?unlock 鐘舵€佷互鏈嶅姟绔?session / 鐭椂 grant 鐨勬柟寮忓伐浣溿€?- 绗簩闃舵璧勬簮鍗忚灞傚啀鍐冲畾娴忚鍣ㄧ洿杩炶祫婧愬浣曞鐢ㄨ繖涓巿鏉冪粨鏋溿€?
### 6.7 閿欒澶勭悊

缁熶竴閿欒璇箟锛?
- `401`锛氶渶瑕佺櫥褰曟垨鍑瘉澶辨晥
- `403`锛氬凡鐧诲綍浣嗘棤鏉冭闂紱鎴?share token 铏芥湁鏁堜絾鍔ㄤ綔涓嶈鍏佽
- `404`锛氬澶栭殣钘忔晱鎰熻祫婧愬瓨鍦ㄦ€ф椂鍙寜绛栫暐闄嶇骇
- `423/429`锛氬瘑鐮佸皾璇曞彈闄愩€侀€熺巼闄愬埗绛夌壒娈婇棬绂?
閿欒杈撳嚭瑕佹眰锛?
- 涓嶆毚闇插唴閮ㄨ矾寰勩€佹枃浠剁墿鐞嗕綅缃€佺瓥鐣ョ粏鑺?- 鍓嶇鍙嬁鍒板彲瑙ｉ噴浣嗕笉杩囧害娉勯湶鐨勪俊鎭?
### 6.8 Phase 1 閲岀▼纰?
#### M1锛氭潈闄愭ā鍨嬩笌鏁版嵁缁撴瀯钀藉畾

- 鐢ㄦ埛缁勮〃
- 璧勬簮璁块棶绛栫暐琛?- share token 鎵╁睍瀛楁
- 鏉冮檺鐭╅樀鏂囨。

#### M2锛氱粺涓€鎺堟潈鏈嶅姟钀藉畾

- 鎺堟潈鍐崇瓥鎺ュ彛
- 鎷掔粷鍘熷洜鍒嗙被
- 瀹¤鍩嬬偣

#### M3锛氶珮椋庨櫓璧勬簮鍑哄彛鏀跺彛

- preview / page / asset / download / diff / versions
- file 涓?share 涓ゆ潯閾捐矾缁熶竴璧版巿鏉冩湇鍔?
#### M4锛氬瘑鐮侀棬绂佷笌缁勯棬绂佸彲鐢?
- 瑙ｉ攣鎺ュ彛
- 鐧诲綍鍙湅 / 缁勫彲鐪?/ 瀵嗙爜鍙湅涓夌被绛栫暐鎵撻€?
### 6.9 Phase 1 楠屾敹鏍囧噯

- 鑳藉璧勬簮閰嶇疆 `login_required`銆乣password_required`銆乣groups_required` 绛夌瓥鐣?- `/files/*` 涓?`/share/*` 瀵瑰悓涓€璧勬簮鍔ㄤ綔缁欏嚭涓€鑷存巿鏉冪粨鏋?- 杩涚▼閲嶅惎鍚庡瘑鐮侀棬绂佷粛鏈夋晥锛屼笉鍐嶄緷璧栧唴瀛樺瓧鍏?- 鏈巿鏉冪敤鎴锋棤娉曢€氳繃 page/asset/download/diff/versions 浠讳竴鏃佽矾鑾峰彇鍐呭
- 鎷掔粷璁块棶鏃跺墠鍚庣琛屼负涓€鑷达紝涓旀湁鍙煡璇㈠璁¤褰?
## 7. Phase 2锛氭祻瑙堝櫒璧勬簮鍗忚灞?+ 浜嬩欢閫氶亾浜屾湡

### 7.1 鐩爣

鍦?Phase 1 鏉冮檺杈圭晫绋冲畾鍚庯紝鎶婃祻瑙堝櫒璧勬簮璁块棶浠庘€滄暎钀?URL helper鈥濆崌绾т负鈥滃崗璁眰鈥濓紝骞舵妸缁熶竴浜嬩欢閫氶亾鎺ュ叆绗簩绫荤湡瀹炰笟鍔′簨浠躲€?
### 7.2 绗簩涓氬姟钀藉湴鐐归€夋嫨

**鏈湡榛樿钀藉湴 `announcements`銆?*

鐞嗙敱锛?
- 鐢ㄦ埛绔兘鐩存帴鎰熺煡鈥滃叕鍛婂彉鏇村疄鏃跺埛鏂扳€濄€?- CRUD 鏄庣‘锛屽彂甯冪偣娓呮櫚锛氬垱寤恒€佹洿鏂般€佸垹闄ゃ€佷笂涓嬬嚎銆?- 浜嬩欢鍐呭鍙繚鎸佽交閲忥紝鍙帹閫佲€滃彂鐢熶簡鍙樺寲鈥濄€?
`tracking` 淇濇寔涓哄悓閫氶亾涓嬩竴鍊欓€夛紝涓嶅湪鏈湡浣滀负纭€у繀閫夈€?
### 7.3 娴忚鍣ㄨ祫婧愬崗璁眰瀹氫箟

鏈湡瑕佹妸鈥滆祫婧?URL 鎬庝箞闀裤€佹€庝箞閴存潈銆佽皝鏉ユ嫾銆佷綍鏃跺埛鏂般€佸け璐ユ€庝箞鍔炩€濇枃妗ｅ寲銆?
姝ｅ紡杈撳嚭鏂囨。锛?
- `docs/frontend-browser-resource-protocol.md`

璇ユ枃妗ｈ嚦灏戝畾涔変互涓嬪唴瀹广€?
#### A. 璧勬簮绫诲瀷鍒嗗眰

1. **API 璇锋眰**
   - 閫氳繃 `src/api/*`
   - 璧?`Authorization` 澶?   - 鐢?Axios / fetch 鎺у埗

2. **娴忚鍣ㄧ洿杩炶祫婧?*
   - iframe / img / pdf / 涓嬭浇閾炬帴 / `<a href>`
   - 鐢?`resourceUrl` 缁熶竴鏋勯€?   - 涓嶈兘鍋囪鑳藉甫 `Authorization` 澶?
3. **鍏紑闈欐€佽祫婧?*
   - avatar / cover 绛?   - 鍗曠嫭瀹氫箟鏄惁闇€瑕佺鍚嶄笌缂撳瓨瑙勫垯

#### B. URL 瀹舵棌

缁熶竴绾﹀畾 `resourceUrl` 璐熻矗鐨?URL 瀹舵棌锛?
- 鏅€氭枃浠堕瑙?- 椤靛浘
- preview asset
- HTML 棰勮
- 鏂囨湰棰勮
- 鍘熶欢涓嬭浇
- 杞崲浠朵笅杞?- share 閾捐矾绛変环璧勬簮
- 鍏憡闄勪欢
- avatar / cover

#### C. 璁よ瘉鎼哄甫瑙勫垯

鏂囨。涓繀椤绘樉寮忓尯鍒嗭細

- **褰撳墠鎬?*
  - API锛歚Authorization`
  - 娴忚鍣ㄧ洿杩炶祫婧愶細鍏佽 query token / 鐭椂 grant

- **鐩爣鎬?*
  - API锛氱户缁?`Authorization`
  - 娴忚鍣ㄧ洿杩炶祫婧愶細閫愭杩佺Щ涓虹煭鏃惰祫婧愮エ鎹?
#### D. 澶辨晥澶勭悊

娴忚鍣ㄨ祫婧愬け璐ユ椂锛?
- 401锛氬紩瀵奸噸鏂扮櫥褰曟垨閲嶆柊鐢宠璧勬簮绁ㄦ嵁
- 403锛氭彁绀烘棤鏉冭闂?- 404锛氭彁绀鸿祫婧愪笉瀛樺湪鎴栧凡澶辨晥

#### E. helper 杈圭晫

- 缁勪欢鍜?view 涓嶅啀鎵嬪啓璧勬簮 URL
- `resourceUrl.js` 鏄敮涓€瀹炵幇鍑哄彛
- 鏂囨。鏄敮涓€鍗忚璇存槑鍑哄彛

### 7.4 浜嬩欢閫氶亾浜屾湡璁捐

#### topic

- `announcements`

#### type

- `announcement.created`
- `announcement.updated`
- `announcement.deleted`
- `announcement.visibility.changed`

#### envelope

娌跨敤缁熶竴缁撴瀯锛?
```json
{
  "id": "evt_20260630_announcement_18",
  "topic": "announcements",
  "type": "announcement.updated",
  "scope": "global",
  "ts": "2026-06-30T12:00:00Z",
  "version": "announcements:18",
  "payload": {
    "announcement_id": 18
  }
}
```

绾︽潫锛?
- 涓嶅湪浜嬩欢閲岀洿鎺ュ箍鎾畬鏁村瘜鏂囨湰姝ｆ枃涓庨檮浠跺垪琛ㄣ€?- 鍓嶇鏀跺埌浜嬩欢鍚庢寜闇€瑕侀噸鏂版媺鍙栨椿鍔ㄥ叕鍛婂垪琛ㄣ€?
### 7.5 鍓嶇閫氱敤璁㈤槄鏈哄埗

鏈湡缁х画鎶婄幇鏈?`config` 璁㈤槄鎶借薄鎴愮湡姝ｉ€氱敤鏈哄埗锛?
- 缁熶竴 topic 娉ㄥ唽
- 缁熶竴鍥炶皟娓呯悊
- 缁熶竴 ready / heartbeat / reconnect 澶勭悊
- 缁熶竴閴存潈澶辫触澶勭悊
- 鍙鐢ㄤ簬鍚庣画 `tracking`銆乣tasks`銆乣audit-status`

### 7.6 Phase 2 閲岀▼纰?
#### M1锛氳祫婧愬崗璁枃妗ｅ畬鎴?
- 杈撳嚭 `docs/frontend-browser-resource-protocol.md`
- 鏄庣‘ URL 鍒嗙被銆佽璇佹柟寮忋€侀敊璇涔夈€佽縼绉昏矾寰?
#### M2锛氬叕鍛婁簨浠跺彂甯冮摼璺帴鍏?
- 鍏憡鍒涘缓 / 鏇存柊 / 鍒犻櫎鏃跺彂甯冧簨浠?- 娲诲姩鍏憡娑堣垂绔帴鍏ヨ闃呭埛鏂?
#### M3锛氬墠绔闃呮満鍒堕€氱敤鍖?
- 缁勪欢鎸?topic 璁㈤槄
- 鏀寔澶氫釜涓氬姟璁㈤槄鐐瑰叡瀛?
#### M4锛歎RL 鍏ュ彛缁х画鏀跺彛

- 鍐嶆壂涓€杞浘鐗?/ 鏂囦欢 / 闄勪欢 / share 璧勬簮鍏ュ彛
- 鎵€鏈夋祻瑙堝櫒鐩磋繛璧勬簮缁熶竴璧板崗璁眰瀹炵幇

### 7.7 Phase 2 楠屾敹鏍囧噯

- 浠撳簱涓瓨鍦ㄦ寮忕殑娴忚鍣ㄨ祫婧愬崗璁枃妗?- 鍓嶇涓昏娴忚鍣ㄨ祫婧愬叆鍙ｄ笉鍐嶅嚭鐜版暎钀界殑纭紪鐮?URL
- 鍏憡鍒涘缓 / 鏇存柊 / 鍒犻櫎鍚庯紝鎵撳紑涓殑鍓嶇瑙嗗浘鍙嚜鍔ㄦ劅鐭ュ埛鏂?- 缁熶竴璁㈤槄鏈哄埗涓嶅彧鏈嶅姟 `config`锛岃嚦灏戞湇鍔?`config + announcements`

## 8. Phase 3锛氭暣浣撳畨鍏ㄥ姞鍥轰笌鏆撮湶闈㈡敹缂?
### 8.1 鐩爣

鍦ㄦ潈闄愪笌鍗忚灞傜ǔ瀹氬悗锛屽澶栨毚闇查潰銆佽祫婧愭巿鏉冨鍛姐€侀瑙堥殧绂汇€佸弽婊ョ敤銆佸璁′笌鐢熶骇鏋勫缓鍩虹嚎鍋氱郴缁熸€ф敹鍙ｃ€?
### 8.2 鏍稿績鏂瑰悜

#### A. 璧勬簮绁ㄦ嵁鍖?
閫愭寮卞寲鈥滄祻瑙堝櫒璧勬簮鐩存帴甯﹂暱鏈?JWT query 鍙傛暟鈥濈殑鏂瑰紡锛屾敼涓猴細

- 鐭椂璧勬簮绁ㄦ嵁
- 鏈€灏忎綔鐢ㄥ煙
- 鍙け鏁?- 鍙璁?
绁ㄦ嵁搴旇嚦灏戠粦瀹氾細

- 璧勬簮 ID / 鑼冨洿
- 鍔ㄤ綔绫诲瀷
- 鐢ㄦ埛鎴?share token 涓婁笅鏂?- 杩囨湡鏃堕棿

#### B. 閫熺巼闄愬埗涓庡弽鎵?
鎸夎祫婧愮被鍒仛鍒嗘《闄愬埗锛?
- 鐧诲綍鎺ュ彛
- share 瑙ｉ攣鎺ュ彛
- preview / pages / assets
- 涓嬭浇鎺ュ彛
- 鍏憡 / 鍒楄〃绛夐珮棰戣鍙栨帴鍙?
寤鸿缁村害锛?
- IP
- user id
- share token
- resource id

鍚屾椂琛ュ厖锛?
- 寮傚父棰戠巼瀹¤
- 澶ч噺椤靛浘鎶撳彇妫€娴?- 瀵嗙爜鐖嗙牬闄愬埗
- 杩炵画澶辫触闂ㄧ

#### C. 棰勮闅旂涓庡畨鍏ㄥご鍔犲己

鍥寸粫 HTML 棰勮 / iframe / 闈欐€佽祫婧愬鍔犳洿涓ユ牸绛栫暐锛?
- 鎸夐瑙堢被鍨嬬粏鍒?CSP
- 鑳界鍐呰仈鑴氭湰鐨勫湴鏂瑰敖閲忕
- 鑳界敤 sandbox iframe 鐨勫湴鏂瑰敖閲忛殧绂?- 闄愬埗璺ㄦ簮宓屽叆绛栫暐
- 缁熶竴 `Referrer-Policy`
- 缁熶竴涓嬭浇鍝嶅簲澶?
#### D. 閿欒澶勭悊涓庝俊鎭劚鏁?
- 绾夸笂鐜涓嶅洖浼犲唴閮ㄥ紓甯告爤
- 璧勬簮璁块棶鎷掔粷涓嶆毚闇插疄鐜扮粏鑺?- 涓嶅湪鍓嶇鎸佷箙鍖栨晱鎰熺粨鏋勪俊鎭?
#### E. 鐢熶骇鏋勫缓鏆撮湶闈㈡敹缂?
瀹為檯鏈夋晥鎺柦鍖呮嫭锛?
- 鍏抽棴鐢熶骇 source map
- 涓嶆妸鏁忔劅閰嶇疆娉ㄥ叆鍓嶇 bundle
- 鍏抽棴澶氫綑 debug route / docs 鍏ュ彛
- 缂╃煭閿欒璇︽儏
- 璧勬簮璺緞鍜岀瓥鐣ヤ笉鍦ㄩ〉闈㈠垵濮嬪寲鏃惰繃搴︿笅鍙?
璇存槑锛?
- 浠ｇ爜娣锋穯鍙互浣滀负鈥滃鍔犻€嗗悜鎴愭湰鈥濈殑闄勫姞鎺柦锛屼絾涓嶆槸鏍稿績瀹夊叏杈圭晫銆?- 鈥滃姞瀵嗛〉闈㈤槻姝㈠埆浜虹湅婧愮爜鈥濅笉鑳芥浛浠ｆ巿鏉冦€佺エ鎹€侀殧绂汇€侀檺閫熴€佸璁°€?
### 8.3 瀹¤涓庡憡璀?
闇€瑕佽ˉ榻愮殑瀹¤浜嬩欢锛?
- share 瑙ｉ攣鎴愬姛 / 澶辫触
- 闈炴硶璧勬簮璁块棶灏濊瘯
- 涓嬭浇棰戠巼寮傚父
- 鍚屼竴 token 澶?IP 楂橀浣跨敤
- 缁勬潈闄愪笉鍖归厤璁块棶灏濊瘯
- 绠＄悊鍛樹慨鏀硅闂瓥鐣?
### 8.4 Phase 3 閲岀▼纰?
#### M1锛氱煭鏃惰祫婧愮エ鎹笂绾?
- 娴忚鍣ㄧ洿杩炶祫婧愪粠闀挎湡 query JWT 杩佺Щ鍒扮煭鏃剁エ鎹?
#### M2锛氬垎妗堕檺閫熶笌鍙嶇垎鐮翠笂绾?
- 鐧诲綍 / 瑙ｉ攣 / 棰勮 / 涓嬭浇鍧囨湁鍒嗙骇闄愰€?
#### M3锛氶瑙堥殧绂讳笌瀹夊叏澶村姞寮?
- 棰勮绫诲搷搴旀寜绫诲瀷鏀剁揣绛栫暐

#### M4锛氱敓浜ф毚闇查潰鏀剁缉

- source map銆侀敊璇粏鑺傘€佽皟璇曞叆鍙ｃ€侀潪蹇呰鍏冧俊鎭敹鍙?
### 8.5 Phase 3 楠屾敹鏍囧噯

- 娴忚鍣ㄧ洿杩炶祫婧愪笉鍐嶄緷璧栭暱鏈熸湁鏁堢殑 query JWT
- 澶ц妯℃姄椤靛浘 / 鐖嗙牬瀵嗙爜 / 楂橀涓嬭浇鍏峰闄愬埗涓庡璁?- 棰勮绫婚〉闈笌璧勬簮鍏峰鏇翠弗鏍肩殑 CSP / sandbox / referrer 绛栫暐
- 鐢熶骇鏋勫缓涓嶅啀鏆撮湶鍙洿鎺ュ埄鐢ㄧ殑澶氫綑璋冭瘯淇℃伅

## 9. 涓夋湡瀹炴柦椤哄簭

### Phase 1 鍏堝仛

鍏堝畾鈥滆皝鑳借闂€佽兘璁块棶鍒板摢涓€姝ャ€佹槸鍚﹁兘涓嬭浇銆佹槸鍚﹁兘鐪?diff銆佹槸鍚﹂渶瑕佺櫥褰?瀵嗙爜/缁勨€濈殑缁熶竴妯″瀷銆?
### Phase 2 鍐嶅仛

鍦ㄦ潈闄愭ā鍨嬬ǔ瀹氬悗锛岃祫婧?URL 鏂囨。鍜岀浜屼簨浠朵笟鍔℃帴鍏ユ墠涓嶄細鍙嶅杩斿伐銆?
### Phase 3 鏈€鍚庡仛

鐭椂绁ㄦ嵁銆侀檺閫熴€丆SP銆佺敓浜ф瀯寤烘敹鍙ｉ兘渚濊禆鍓嶄袱闃舵鐨勭ǔ瀹氳祫婧愯竟鐣屽拰鎺堟潈璇箟銆?
## 10. 娴嬭瘯绛栫暐

### Phase 1

- 鍚庣鍗曞厓娴嬭瘯锛?  - 鎺堟潈鍐崇瓥鐭╅樀
  - 缁勬潈闄?  - 瀵嗙爜闂ㄧ
  - share token 瑕嗙洊绛栫暐
- 鍚庣闆嗘垚娴嬭瘯锛?  - preview / pages / assets / download / diff / versions 鍏ㄩ摼璺槻瓒婃潈

### Phase 2

- 鍓嶇鍗曞厓娴嬭瘯锛?  - `resourceUrl` / 鍗忚灞?URL 鏋勯€?  - 璁㈤槄鏈哄埗 topic 鍒嗗彂涓庨噸杩?- 鍚庣闆嗘垚娴嬭瘯锛?  - 鍏憡 CRUD -> 浜嬩欢鍙戝竷
- 鍓嶇缁勪欢娴嬭瘯锛?  - 鍏憡鑷姩鍒锋柊

### Phase 3

- 闄愰€熶笌鐖嗙牬鍦烘櫙娴嬭瘯
- 绁ㄦ嵁杩囨湡涓庤秺鏉冩祴璇?- 瀹夊叏澶村洖褰掓祴璇?- 鐢熶骇鏋勫缓鏆撮湶闈㈡鏌?
## 11. 椋庨櫓涓庢帶鍒?
### 椋庨櫓 1锛歅hase 1 鏀瑰姩瑙﹁揪闈㈠箍

鎺у埗锛?
- 鍏堜粠璧勬簮鍑哄彛鑰屼笉鏄叏閲忎笟鍔?CRUD 鏀跺彛
- 鍦ㄥ皻鏈厤缃樉寮忚祫婧愮瓥鐣ユ椂锛屽厑璁稿洖钀藉綋鍓嶈涓猴紝閫愭杩佺Щ

### 椋庨櫓 2锛氭潈闄愭ā鍨嬭璁¤繃閲?
鎺у埗锛?
- 棣栫増鍙仛 project / file / version 涓夌被璧勬簮
- 鍏堣鐩?view / preview / asset / diff / versions / download 鍏抽敭鍔ㄤ綔

### 椋庨櫓 3锛氭祻瑙堝櫒璧勬簮閴存潈杩佺Щ褰卞搷鍏煎鎬?
鎺у埗锛?
- Phase 2 鏂囨。鍏堟槑纭綋鍓嶆€佷笌鐩爣鎬佸弻杞?- Phase 3 鍐嶅仛 query JWT -> 璧勬簮绁ㄦ嵁杩佺Щ

### 椋庨櫓 4锛氬弽鎵掓帾鏂借浼ゆ甯哥敤鎴?
鎺у埗锛?
- 闄愰€熸寜妗舵寜绫诲瀷缁嗗垎
- 绠＄悊鍚庡彴涓庢櫘閫氳闂€氶亾鍒嗗紑绛栫暐
- 鎵€鏈夐檺鍒跺姩浣滈渶鏈夊璁″拰鍙皟闃堝€?
## 12. 闈炵洰鏍?
鏈涓夋湡璁捐涓嶅寘鍚互涓嬫柟鍚戯細

- 涓嶅仛澶氱鎴风粍缁囩郴缁?- 涓嶅仛澶嶆潅 ABAC 瑙勫垯缂栬緫鍣?- 涓嶅仛 WebSocket 涓婚€氶亾鏇挎崲 SSE
- 涓嶆妸鈥滃墠绔簮鐮佷笉鍙鈥濅綔涓烘牳蹇冨畨鍏ㄧ洰鏍?- 涓嶄緷璧栧崟绾贩娣嗘垨椤甸潰鍔犲瘑鏉ユ浛浠ｆ湇鍔＄鎺堟潈

## 13. 鏈疆缁撹

鏈疆鎸夌敤鎴疯姹傦紝宸茬粡鎶婃柊澧炵殑 4 涓洰鏍囨敹鏁涗负涓夋湡鎬荤翰锛屽苟缁欏嚭姣忔湡鐨勶細

- 鐩爣
- 璁捐杈圭晫
- 鍏抽敭妯″潡
- 閲岀▼纰?- 楠屾敹鏍囧噯

鍚庣画搴旇繘鍏ョ殑涓嬩竴姝ユ槸锛?
1. 鐢ㄦ埛瀹￠槄鏈璁℃枃妗ｏ紱
2. 濡傛棤淇敼锛屽啀鍩轰簬鏈璁℃枃妗ｅ啓 implementation plan锛?3. 瀹炴柦椤哄簭浠?**Phase 1** 寮€濮嬨€?
## 14. 澶囨敞

- 璁捐鏂囨。浣嶇疆锛歚docs/superpowers/specs/2026-06-30-access-control-event-protocol-and-security-hardening-design.md`
- 鎸夌敤鎴疯姹傦細**鍙湪鏈満钀藉湴锛屼笉鍋?git 鎻愪氦**

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

