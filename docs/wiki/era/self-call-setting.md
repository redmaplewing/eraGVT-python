# 一人稱設定（S47–S48）

## 入口與資料

- SHOP [110] → 狀態畫面 P1 [12] 呼叫 `FIRSTSETTING_CHARA_SELFCALL`；戰鬥中 `FLAG:700` 非零不開放。
- 原作：`ERB/ヒロイン関連/ステータス画面/SHOW_STATUS_CHARA_SELECT_PAGE1.ERB@CMD_STATUS_CHARA_SELECT_PAGE1:195–206` 的 [12] 分支；
  `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_SELFCALL:1203–1492`。
- 實作：`game.self_call_setting.selfcall_gen`；固定顯示與音節表由 `tools/extract_self_call_text.py` 抽取至 `self_call_text.py`。
- 選擇過程只更動函式暫存；[99] 確認才寫 `CFLAG:8` 與 `CSTR:4`。[98] 取消保留角色資料，`RETURN 98`。
- S68已將`ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD:515`接回真實一人稱輸入並移除`selfcall_default`；98／99均回種族／feat提示，取消不提交，詳見[角色編輯](character-editor.md)。

## 操作

- [0]–[8] 選稱呼，[30]–[32] 選漢字／平假名／片假名字形。已選格用綠色純文字，不能點擊；仍可手打數值。
- [21] 取角色 `CALLNAME`，[22] 輸入任意表記；若表記本身可分析，就直接作為讀音，否則另問讀音。
- [50] 性格預設依序：男性且粗暴 → 俺、其他男性 → 僕、古風 → 妾、輕浮 → 私（あたし）、其他 → 私（わたし）。
  已選標準稱呼時保留字形，從 [21]/[22] 回預設才重設字形為 0。
- 讀音輸入 [98] 顯示原作拗音表，空字串或 [99] 返回設定。取消讀音不回復此前暫存，讀音空白時不能 [99] 確認。
- `PRINTW` 用既有文字通道等待 Enter，不寫 `RESULT`／`RESULTS`；實際 Web 支援空白提交。

## 音節與狀態

- 依 `ERB/口上/口上システム関係/SELF_CALL.ERB@SELF_CALL_ANALYSIS:299–356`、
  `@CHECK_SINGLE_SOUND:360–428`、`@CHECK_DIPHTHONG:432–505` 手翻：先檢查 UTF-16 長度 ≤10，再逐字分析，最多四音。
- 平假名／片假名不能混用；「ヴ」「ー」屬中性。全由中性音構成時字形為片假名。原文不接受「ゔ」。
- 原表列出的拗音合併一音；其他合法小字照單獨音計算，不自行擴增組合。
- 自訂編碼為 `(音0 + 音1×1000 + 音2×1000² + 音3×1000³)×100 + 99 − 字形`。
- 分析成功 `RETURN 字形,音0,音1,音2,音3`；錯誤的 `RETURN` 只改 `RESULT:0`，但途中 `CHECK_SINGLE_SOUND` 已可能改寫尾格 1／2，不回復分析前數值。逐字 `SUBSTRINGU` 留下最後分析字元於 `RESULTS:0`。
- 設定的 `PRN_VAR`／`CHR_VAR` 為靜態暫存，跨呼叫保留、不存檔；讀取設定用到的 `SELF_CALL_SUBSTRING.CAL_VAR` 與 catalog 共用暫存。

## S48：自訂重入修正（已授權偏離）

- S47 報告建議查明意圖後修正這兩項，使用者隨後要求選下一步繼續，本階段依該授權處理。
- `FIRSTSETTING_CHARA_SELFCALL:1216–1217` 把自訂碼解為種類 19、字形 3／4，卻在 `:1466–1475` 當標準碼保存，截去高位。
  Python 保存入口原始自訂碼；不改直接 [99] 保留完整 `CFLAG:8` 及 `CSTR:4`，不用顯示讀音重新分析，避免 `CHAR_LIB` 非可逆字形造成資料遺失。
- 自訂重入 [50] 依首次 [21]/[22] 設定後切回預設的成功路徑（`:1324–1326、1399–1400、1304–1322`），先重設字形 0，再依性格選稱呼。
- 選標準稱呼、字形或新自訂稱呼後使用新選擇；取消保持原角色資料。取消手動表記輸入也保留原碼。
- 原作 `SELF_CALL_SUBSTRING:161–165` 直接從自訂碼高位讀取音節，支援保存完整原碼的判斷；不修改全域編碼或非互動預設路徑。
- 定向回歸包括平假名／片假名、四音／拗音、非可逆字形、三次重入、性格優先序、取消及改選、Web 設定與存讀檔後重入。

## 其他原作特殊行為（照原樣保留）

- 主選單無效數值在 `FIRSTSETTING_CHARA_SELFCALL:1488–1490` 跳 `INPUT_PRN_0`，直接等待讀音文字，並非重問主選單。
- `SELF_CALL_SUBSTRING:140–165` 只處理預設 0–6 與自訂 19；7／8 讀音沿用 `CAL_VAR` 靜態殘值。上一回正常呼叫以零次 `FOR CAL_VAR,0,0` 清為 0，因此通常讀音空白。
- `SELF_CALL_LENGTH:293–295` 的 `STRLENFORMU CSTR:SELF_TARGET:4` 缺 `%`，計固定文字長度 18，回傳 6。
  `SELF_CALL_SUBSTRING:124–125` 超過上限時又取同一長度，因此仍讀六碼；正常四音編碼後兩碼為零。
- `CHAR_LIB:700–704` 的平假名「ヴ」組合，直接以 `C_ROW` 索引短字串，部分讀音會保留「ヴ」或漏掉後綴；不自行修正。

## 引擎查證與驗收

- `reference/emuera-1824/Emuera/GameProc/UserDefinedVariable.cs:27`：`#DIM` 預設 static。
- `reference/emuera-1824/Emuera/GameData/Variable/VariableToken.cs:2049–2065`：靜態二維字串依宣告建立陣列並直接索引，越界不回空字串。
- `reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:504–526`：STRLENFORMU 取字串的 .NET 長度。
- `reference/emuera-1824/Emuera/Sub/LexicalAnalyzer.cs:1143–1157`：格式字串只有 `%`／`{` 進入插值。
- `reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:2195–2218`：SUBSTRINGU 依 .NET 索引，起點超界回空字串。
- `Instraction.Child.cs:1733–1743`：FOR 即使零次仍先寫起值；`:1997–2023`：RETURN 只寫傳入的 RESULT 格。
- `reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:497–508、701–734`：等待與輸入；
  `reference/emuera-1824/Emuera/GameProc/Process.cs:249–260`：INPUT／INPUTS 各寫 RESULT:0／RESULTS:0。
- 定向測試涵蓋標準稱呼 27 組、預設讀音重入、四音／拗音編碼解碼、錯誤順序與殘值、確認／取消、靜態暫存、實際 Web／存讀檔。
- S48 兩項已授權偏離見上節與 `../bridge/deviations.md`；無新增查證未決，其餘原作特殊行為保留。
