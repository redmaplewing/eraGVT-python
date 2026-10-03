# S34：裏プロフィール與戰鬥狀態顯示

原作路徑相對 `source/earGVP/`，引擎路徑相對 `reference/emuera-1824/Emuera/`。

## 資料生成與保存

- `ERB/ヒロイン関連/SEXUAL_PROFILE.ERB@MAKESEXUALPROFILE:12–108` 手翻至 `game.sexual_profile`。
  `tools/extract_profile_text.py` 只抽取 `STRDATA` 的原文候選到 `game.profile_text.TABLES`；不解譯條件、迴圈或遊戲規則。
- `ERB/ヒロイン関連/ABL_UP_CHECK.ERB@_ABLUP:150–207、270–330`：普通／超過 Lv5 的提升兩段均接通。
  能力實際提高且 `CONFIG_CHECK_OTHER_F(6)==1` 才覆寫 `CSTR:45–48`；設定關閉或等級不變時保留舊字串、不抽亂數。
  C 類別依 `ERB/汎用関数/SEX_GENDER.ERB@ISPENIS:9–15` 選 P／C，其他依序 V、A、B。
- 顯示顏色按能力值夾於 0–10 計算；輸出後恢復預設色。角色狀態頁既有的 `CSTR:45–48` 顯示直接沿用。
- CSTR 原本就屬角色存檔資料，無須修改 JSON 格式：`GameData/Variable/VariableCode.cs:169` 的 `__SAVE_EXTENDED__`，
  `GameData/Variable/CharacterData.cs:313–332` 寫入角色字串陣列。新增測試涵蓋生成後存讀檔保留。

### 亂數順序

| 等級 | 形容詞／修飾詞 |
|---|---|
| < 3 | 基礎候選一個 |
| 3–4 | 中間候選一個 |
| 5–6 | 高階候選一個 |
| 7 | 高階候選 → 部位 → ADV_1 |
| 8 | 高階候選 → 擬聲 → 部位 → ADV_1 |
| 9 | 高階候選 → 擬聲 → 部位 → ADV_2 |
| 10 | 高階候選 → 擬聲 → 第二高階候選（相同就重抽）→ 部位 → ADV_2 |
| ≥ 11 | 擬聲 → 一個高階候選 → BAD_REPUTATION → 部位 → ADV_2（沒有 Adj:1）|

最後才抽動詞。B 部位固定，其他部位使用各自候選表。最終串接順序是 Adj:3、2、1、0、部位、助詞、Adv、動詞、結尾。

- 候選中冠名僅 `FLAG:6==1` 可替換，口號僅 `FLAG:7==1` 可替換；否則在**完整原候選表**重抽，沒有排除後再抽。
  依據：`ERB/ヒロイン関連/SEXUAL_PROFILE.ERB@MAKE_ADJ_BC:160–167`、`@MAKE_ADJ_VA:225–232`、
  `@MAKE_VERB_V:365–372`、`@MAKE_VERB_A:430–437`。
- `STRDATA` 每次消耗一次 `GetNextRand(候選數)`，選中後才計算字串：`GameProc/Process.ScriptProc.cs:730–754`。
- 所有隨機選擇透過 `state.rng`；測試驗證每次上限與呼叫次數，包含重抽及 Lv10→11 邊界。

## 戰鬥列表與控制

`game.battle.palam_display` 接在 `train.show_status` 的原作上下位置；沿用既有 898／899 指令。
依據：`ERB/ヒロイン関連/CHARA_STATUS.ERB@SHOW_STATUS_BASE_DISPBATTLE:41`、
`@SHOW_TRAIN_PALAM_STATUS:1715–1750`、`ERB/ゲーム内_戦闘処理/BATTLE_SHOW_STATUS.ERB@SHOW_STATUS:223`、
`ERB/ゲーム内_戦闘処理/BATTLE_COM.ERB@USERCOM:636–639`。

| FLAG:801 bit | 行為 |
|---|---|
| 1 | 參數上升計算顯示（設定 [11]） |
| 5 | 戰鬥列表開關（設定 [15]） |
| 6 | 0 上部、1 下部（設定 [16]；指令899反轉） |
| 7 | 0 固定展開；1 可折疊、可移動（設定 [17]） |
| 8 | 只在可變模式有效：1 收起、0 展開（指令898反轉） |

- 列表依 `ERB/ゲーム内_戦闘処理/BATTLE_SHOW_STATUS.ERB@SHOW_STATUS_PALAM:353–426` 的 12 項順序與分行呈現。
  前4項有結界時使用原 `COLOR_BAR`、其餘使用數值及原門檻等級；沿用已有文字輸出與Web樣式。
- `CFLAG:34>0` 且 MANIAC(16) 打開才呼叫 `PRINTFORM_GAPING_NOW`；MANIAC(16) 是 `1-GETBIT(FLAG:850,16)`。
  依據：`ERB/SYSTEM/コンフィグ/CONFIG_GLOBAL_MANIAC.ERB@CONFIG_CHECK_MANIAC_F:43–47`。
  第一次顯示若 CFLAG:35／36 為0，會初始化並依經驗消耗亂數；固定模式不受 bit8 影響，收起的可變模式不初始化。
  原作依據：`ERB/ゲーム内_戦闘処理/GAPING.ERB@PRINTFORM_GAPING_NOW:789–845`；詳見 `../era/gaping.md`。

## 上升計算與共享狀態

- `ERB/ゲーム内_戦闘処理/PALAM_UP.ERB@PALAM_UP:74、302–309` 在加算前保存數值，`SUMARRAY(UP)` 非0且 bit1 開啟時，
  依序 WAIT、SHORTLINE、計算列表、SHORTLINE、空行；原有個別上升提示沿用。
- `@PALAM_UP_DISPLAY_CALCULATION:1338–1399` 保留原作排版寬度計算的索引差異：1356用 `PALAM:LCOUNT`，1375輸出才用
  `PALAM:調教PALAM:LCOUNT`。顯示上限也照原公式，不反過來改動原本的參數加算規則。
- 原作 `BEFORE_PALAM_CVAB` 是 static `#DIM`，只有 `UP:PCOUNT>0` 才覆寫對應欄位；其他欄位保留，會影響下次寬度。
  使用既有 `state.temp.locals` 保存；引擎預設 static：`GameProc/UserDefinedVariable.cs:27`；
  `GameData/Variable/VariableData.cs:450–473`、`VariableToken.cs:1847–1875`。
- `STRLENFORM` 更新 RESULT:0：`GameProc/Function/Instraction.Child.cs:504–526`；COLOR_BAR 的 RETURN 1 也寫 RESULT:0。
  **三個一般顯示函式結束後都歸0**，包含列表關閉的出口；RESULT:1以後保留。
  引擎依據：`GameProc/Process.ScriptProc.cs:61–67`。字串生成的 `#FUNCTIONS` 不改共用 RESULT。
- 898／899 的 bit 反轉沿用既有實作；引擎 `INVERTBIT` 的 XOR：`GameProc/Function/Instraction.Child.cs:538–555`。

## 驗收

新增72個測試：資料表與原文一致、生成順序與亂數上限、重抽、能力升級雙階段、保留／存讀檔、各設定開關、
列表初始化的200次亂數、數值／結界／等級、計算原文寬度、共享RESULT終端，以及實際戰鬥呼叫與控制。
完整pytest與最終模擬結果以 `docs/STATUS.md` 為準。無新增未決或偏離；既有市民戰／命名等停止維持。
