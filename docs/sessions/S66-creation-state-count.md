# S66：W02 主製作初始狀態與人數

## 完整成果
- 承接S65，接通creation_menu尚未完成的個別初始狀態及角色人數操作，屬W02／B02，複驗W01的GLOBAL解鎖消費端。
- 以CHARA_MAKE_MAIN實際分派為準，完成相關可達選項、返回／重入、清單更新與完成至SHOP；原文人數2–6直接生效、狀態循環，不新增確認；不能只新增helper。
- 核對開局、引繼、模式／解鎖條件與角色增刪後索引；既有未設定角色的原作預設路徑保持一致。
- 不擴充W03生命週期或W04套組，原作未完成保留；[8]經歷範圍阻塞沿S65既有查證，不重查／重派。

## 查證與實作
- 依序讀AGENTS、STATUS、PLAN及本規格；只查主製作相關分派、子函式、GLOBAL消費與必要引擎依賴。
- 原作引用完整路徑@函式:行號，引擎引用reference完整路徑:行號，不用慣例推測ADDCHARA／DELCHARA或索引更新。
- 從原文推導table-driven前態／expected，先紅後綠；涵蓋權限上下界、無效手輸、取消／確認、模式與GLOBAL組合、增減角色、非目標角色保持、初始化／完成次序。
- 固定文字優先抽取，手寫原生Python流程；共享RESULT(S)、RNG、角色索引與bonus依原文；ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB@CHARA_MAKE_MAIN:149的ARG=RESULT-500會覆寫後續編輯bonus，須保留並測試，不增自動確認／回滾。
- 全部新測試及瀏覽器使用全新25歲人工定義，沿fresh-adult-25-v1，不修改產品年齡規則、原作或既存角色。
- 若原文分支需尚未移植功能，先查實際必要依賴，不能發明替代效果；只有真正阻塞才報具體裁決事項，一般可獨立操作持續完成。
- 不新增敘事情節；實際受影響操作有新疑慮時限最小資料流查證，沿用既有結果，不概括整個專案。

## 驗收與交付
- 定向先紅後綠，少量真GameSession/Web邊界，確認清單顯示、重入及最終角色／初始狀態到SHOP一致。
- 提供tmp/s66/browser_fixture.py：全新25歲人工資料、臨時存檔、Null敘事與只讀一般數值端點；需要解鎖前態明確標示人工GLOBAL，不能當自然取得成就。
- 真catalog與Null範圍分開，不用常數0冒充失敗計數。
- 定向通過即通知產品凍結及瀏覽器操作步驟；主代理獨立跑全pytest、真瀏覽器與500，子代理不重複啟動500。
- 正式500沿tools/sim_adult.py：default／tokusou各seed0–249、max-shop200、actions101–108，每50局前景一批；比較tmp/s65/adult25-v1完整JSON。
- 子代理更新PLAYABILITY、相關wiki與必要bridge；STATUS／PLAN由主代理收口，文件繁體中文、LF／UTF-8無BOM。
- 子代理不commit/push；核對git status／diff、source/reference未動，最後回報成果／依據／裁決。

## 主代理驗收
- 全pytest：`4221 passed, 1 warning in 104.82s (0:01:44)`；產品凍結後執行。
- 真瀏覽器：預設全狀態循環、人數增減／取消／無效輸入／舊尾索引；未解鎖、SOLO、人工SOLO＋SANDBOX權限；真引繼保留NO302、改狀態1與人數2後到SHOP。全員25歲，未設定形態-1保留，console錯誤0。
- 引繼FLAG8前值5，增至6人加3、減至2人扣4，結果4；此為角色編號累計，不是人數。`ERB/ゲーム内_イベント発生/エンディング/SUCCESSION.ERB@SUCCESSION:1052–1069、1375–1398、1478–1484`保留8、刪未選角色不扣、補角色才累加；不是S66缺陷。
- 正式500：default247上限／3回標題，tokusou250上限；catalog與fixture失敗皆0，十批退出0，seed／參數／log核對通過，完整JSON逐seed與S65一致。
- 證據：`tmp/s66/adult25-v1/audit.json`、`tmp/s66/browser-*.json`與`tmp/s66/creation-states-verified.jpg`。人工GLOBAL／模式／Null與自然流程區分；source/reference未動，無新增UNVERIFIED／DEVIATION。
