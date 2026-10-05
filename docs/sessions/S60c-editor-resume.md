# S60c：接續S60一般角色編輯功能

- 使用者要求完成先前中止工作；承接W02，不另換工作包。
- 先核對S60未提交程式，只處理命名、稱呼、一人稱、一般選單與確認／返回等非性內容。
- 不改年齡規則、不新增或擴充涉及未成年角色的性內容／性屬性畫面。
- 若既有共用畫面包含受限內容，精確列出相依；優先將可獨立完成的一般功能接到既有合法呼叫者，不自行刪畫面或改原作規則。
- 先備份未提交S60改動到gitignored tmp，保留原檔；提交範圍須能獨立適用於HEAD。
- 查原文與引擎依據，附行號；測試先行，expected由原文推導，RNG注入。
- 可讀程式作技術分析，但不重現、生成或測試受限內容；中性fixture驗證一般功能及真實Web表單。
- 驗收不得把一般功能通過等同整批S60通過；沒有執行的全pytest／500局明確記錄。
- source/reference唯讀；不改寫既有工作、不全量stage。
- 文件繁體中文、LF UTF-8無BOM；STATUS≤120行，記錄實際完成與剩餘範圍。
- 子代理完成一般功能、測試、獨立可提交檔案集與瀏覽器驗證步驟；不要commit/push。
- 父代理獨立驗收後只提交完成部分並push main；其餘明確回報，不再籠統宣稱整批角色編輯受阻。

## 本次實際成果（2026-10-06）

- 未提交檔案、刪除清單及 tracked patch 已備份至 `tmp/s60c/backup/`；原有S60工作保留。
- 修正既有 `character_name` 的三處 CLEARLINE：空名字警告確認後清除，以及排列／同姓子頁返回時清到本函式入口再重畫；不改名字規則。
- 原文：`ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_NAME`:506、589–594、625–637、656–672；引擎：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:488–500`。
- 新增 `tests/test_character_name_neutral.py`：只用人工名稱與稀疏陣列，不開局、不載角色資料、不渲染共用編輯器。六案先紅，修正後 `6 passed in 0.13s`。
- 呼叫相依：`character_editor.py@character_editor` 的選項1呼叫氏名元件；每次輸入前均先執行 `_draw`，其內容不符合本次中性畫面驗收範圍。不能只提交氏名元件並宣稱HEAD已有入口。
- 原作氏名函式只有兩個呼叫點：`ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN`:238，以及 `ERB/バージョン間互換処理.ERB@UPDATE`:214。後者不在HEAD已移植遷移範圍；沒有另造入口。
- S60已直接重用HEAD的稱呼、一人稱、變身名稱等函式，沒有可透過消除重複而獨立接通的缺口。本次修正及測試依附未提交S60，保持未提交。
- 全pytest、500局、共用角色編輯畫面與自然流程真瀏覽器未執行；上述六案不代表S60或W02驗收完成。沒有新增UNVERIFIED／DEVIATION。
- 可用測試專用Web前態讓既有session執行 `character_name(ctx,1)`，限定人工中性角色、結束後回中性完成訊息，驗排列／同姓返回和空名字確認；這是元件表單驗證，不能當作產品入口整合。

- 父代理獨立驗收：氏名六案＋共用輸入十三案，`19 passed, 1 warning in 1.75s`。本次不提交缺少HEAD呼叫者的元件，未執行整頁瀏覽器或全遊戲驗收。

## 已完成的年齡來源查證（後續沿用，不重複派工）
- 共用頁`character_editor.py@_draw:49`讀BASE:年齢；原作`ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:111`相同。CSV/Base.csv:20–21區分実年齢40與年齢41，不可混稱。
- 預設生成`body.py@chara_make_age_setting:412–470`先以RAND:11+10產生，再由其他設定覆寫；原作`CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_AGE_SETTING:1342、1408–1444`。缺當次seed與狀態，無法斷言11的確切來源。
- 原作個別[6]→SIZE_SETTING可手動設定年齡：`FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:256–260`、`CHARA_SIZE_UI.ERB@SIZE_SETTING:1461–1473`；Python個別[6]尚未移植。
- `character_name.py`自身不讀寫年齡；相依為`character_editor.py:129–130`先重繪共用頁，再於153–157分派一般子頁。這不代表一般命名邏輯不可處理。
- 共用頁的具體受限範圍是涉及未成年角色的性屬性呈現；不以年齡欄位或專案題材概括全部一般功能。
- 現有氏名修正依附未提交共用頁，沒有已確認的獨立HEAD入口。不得發明原作沒有的入口、默改顯示規則或宣稱S60已完成；沒有新相依資訊不再派工做相同盤點。
