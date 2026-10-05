# 角色自動生成設定（S54）

## 來源與入口

- `ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_INITIALIZE:8–164`。
- `ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB@CHARA_MAKE_MAIN:9–21`：
  `GLOBAL:22 → FLAG:824` 自動分配フィート；`GLOBAL:23 → FLAG:825` 限定有口上的性格。
- 沿用全域設定載入；未開啟時不增加輸入。手動設定 UI 留待完整角色製作階段。
- 原作 `CHARA_MAKE_INITIALIZE` 呼叫者：同檔 `@CHARA_MAKE_FINALIZE:232` 與
  `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:22`。
  Python 已接通開局的 finalize；後者完整手動 UI 仍未移植。
- 開局共用現有 `Ctx` 的 `TextOutput` 與 `NarrationService`；非互動 helper 未指定服務時按需載入原作 catalog。

## 種族與フィート

先查種族；已有種族時連自動分配都不執行。無種族才按原有 `FLAG:823` 或隨機抽選生成，
然後再查種族，只有 `FLAG:824 == 1` 才呼叫 `SET_FEAT_DEFAULT`；其他非零值也不啟用。
兩次 `SYUZOKU_CHECK` 的整數回傳都寫入共用 RESULT:0。

`ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@SET_FEAT_DEFAULT:1500–1776`
已於既有 `firstsetting.set_feat_default` 完整手翻，S54 直接復用：

- 先 `RAND:8`，需要時才 `RAND:4`，決定 1／2／3 格；吸血鬼減一格。
- `RAND:4 != 0` 時選各族預設組合；短路判斷的亂數順序與原作相同。
- 剩餘格數大於零時，以 `FEAT_ABLE_F` 與未取得條件建立 1100–1299 區間候選。
  原作迴圈以開始時候選總數作終點，因此取得**所有剩餘候選**，不是只取得剩餘格數。
  每次抽取後移除該候選，亂數上限依序遞減；既有素質非零者不重抽、不覆寫。
- `ERB/ヒロイン関連/CHARA_SYUZOKU.ERB@FEAT_ABLE_F:92–239` 定義各族候選。
- 原作鬼的某組合拿兩項只扣一格（:1663–1665）、妖精預設能給一般候選外的エアマスター（:1682），均沿用原文。
- 最後 `SET_PROFILE` 重算身體資料，RESULT:0 = 0；其多值回傳殘值也沿用既有實作。
  依據 `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_TALENT.ERB@SET_PROFILE:4–19`。

全部 `SET_FEAT_DEFAULT` 呼叫者共四處：本次初始化 :71、
`ERB/ゲーム内_行動実行処理/ACTIONsub_TSUIKAYOUSEI_NORMAL.ERB@TSUIKAYOUSEI_NORMAL:132`、
`ERB/ゲーム内_行動実行処理/ACTIONsub_DRUG_PREPARATION.ERB@DRUG_PREPARATION:412`、
`ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD:633`。後三者沿用既有接線。

## 性格抽選與原作特性

已有性格時全部略過；無性格時每輪 `RAND:18 + 10` 設一個素質。
`FLAG:825 == 0` 立即接受；任意非零值才嘗試 `KOJO_0_COLOR_{本輪抽值}`。
不是按性別／角色口上編號選，也不是查最終生效性格。

- 有該函式：實際執行，RESETCOLOR，立即接受；無函式才繼續抽。
- 有效 `.ERB` 定義為 10、12、13、14、16、17、20、21、22、24、25、27。
  `.ERB.org` 備份不另算；不在 Python 維護硬編碼存在表，判斷交 catalog。
- `ERB/口上/女性汎用口上/★KOJO_0_16_真面目/■メニュー.ERB@KOJO_0_COLOR_16:24–34`
  除設色外，還清空 `真面目_フラグ_シチュ`。註解掉的函式標頭不會切開這項副作用。
- 原作重抽**不清除先前素質**；最終 `SEIKAKU_CHECK` 取最小編號，所以可能保留多種性格，
  生效性格也可能是沒有口上的較小編號。按現有「依原作」裁決保留，不自行修正。
- 嘗試計數初始 1，最多在計數 ≤100 時進入迴圈。前面索引 1 到 SELECT−1 每個相同性格都加一；
  缺少 COLOR 再加一。內層 CONTINUE 不會重抽，同輪成功仍直接接受。
- 達上限時保留已設定的素質，沒有 RESETCOLOR。最後按生效性格補正七項 BASE／MAXBASE 與一人稱；
  `CALL SEIKAKU_CHECK` 寫 RESULT:0，其他 RESULT／RESULTS 格保留。
- 無 catalog 或明確 Null 服務時停止；函式存在卻不可執行也停止，不冒充缺少口上重抽。

## 引擎依據

- TRYCCALLFORM 的註冊：`reference/emuera-1824/Emuera/GameProc/Function/FunctionIdentifier.cs:335`；
  動態求函式名、只有找不到才跳 CATCH：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:2297–2332`。
- CONTINUE 配對最近迴圈：`reference/emuera-1824/Emuera/GameProc/ErbLoader.cs:1040–1059`。
- FOR 終點只在進入時求值：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1731–1743`。
- RESETCOLOR 恢復設定前景色：同檔 :1056–1067；本次不清除背景或其他樣式。
- 普通函式自然終端只寫 RESULT:0 = 0：`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`。

## 驗收

`tests/test_generation_settings.py` 覆蓋 11 族、預設／自由抽選、既有資料、旗標邊界、全部 12 個有效 COLOR、
六種缺少口上的重抽、計數上限、輸出與共用結果、COLOR 的暫存副作用、兩種 Web 開局與存讀檔。
無新增 UNVERIFIED／DEVIATION；完整 pytest 與標準 500 局摘要見 STATUS。
