# S10：開局改回原作預設路徑（3 名汎用キャラ的完整隨機生成）

## 背景
S03 把開局寫死成「初期セット・特装戦隊（301–303）」，但原作預設是 EVENTFIRST:111–135 的 3 名 `ADDCHARA 0`（汎用キャラ）
→ `CHARA_MAKE_MAIN` → `CHARA_MAKE_FINALIZE`。初期セットは角色製作畫面裡的選項，不是預設。
這使身體資料不生成（CHARA_MAKE_DEFAULT.ERB:498 的 `NO == 0` 條件）→ 戰鬥中女性敏捷 0、攻擊 2 倍。
AGENTS.md 已新增規則：跳過 UI 時必須走原作預設路徑。路徑相對 `source/earGVP/ERB/`。

## 目標
新遊戲的預設結果＝原作中「玩家在模式選擇、角色製作、HEROINE_PRESET、序章等所有選單都不改設定、直接確定」的狀態。
初期セット（特装戦隊）保留為可選的開局選項（照 `SHOKISET.ERB@CHARA_MAKE_FINALIZE_KAI` 的路徑）。

## 範圍
1. **確認預設路徑**：逐步追 `EVENTFIRST`（flow.md 表）→ `CHARA_MAKE.ERB@CHARA_MAKE_MAIN` 在「不改設定直接 [1000]」時
   實際執行的函式與順序，特別是汎用キャラ何時、以何種順序呼叫 `CHARA_MAKE_INITIALIZE`（CHARA_MAKE_DEFAULT.ERB:5–220）
   與 `CHARA_MAKE_FINALIZE`（:221）。把追到的順序寫進 `docs/wiki/era/flow.md`（表格加註）。
   任何「預設值」都要從原文或 config 預設取得（例如 FLAG:825 口上限定ガチャ、GAME_OPTION 的預設），不可自選。
2. **汎用キャラ隨機生成**：`CHARA_MAKE_INITIALIZE` 全體（性格ガチャ、口上檢查、SEIKAKU_HOSEI、一人稱等）、
   `CHARA_MAKE_BASE_PROFILE` 的汎用分岐（:507–980）、`CHARA_MAKE_STATUS_TALENT`／`_FLAVOR`／`_SEIKAKU`、
   `CHARA_MAKE_AGE_SETTING` 的完整版（含 CSTR:204–206 年齢指定、`RANDOM_AGE_F`）、`SET_FEAT_DEFAULT`、
   名字生成（`FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_NAME_RANDOM` 等，若預設路徑會走到）。
   S09 已移植的身體生成函式（`eragvt.game.body`）直接重用。
3. **開局接線**：`eragvt.game.opening` 的預設改為上述路徑；初期セット改成選項（Web 新遊戲畫面提供
   「預設開始」與「初期セット：特装戦隊」兩個按鈕即可，其餘選單仍以預設值跳過）。
   EVENTFIRST:143–166 的 `CFLAG:6` 口上番號（汎用キャラ依 `TALENT:口上設定`）要照原文，讓 S07 的汎用口上派發真的走到。
4. **亂數**：一律注入 `GameRng`、依 ERB 求值順序抽。開局亂數序列會大幅改變：既有 seed 測試若依賴開局狀態，
   **改為明確指定開局路徑**（例如測試固定用初期セット選項以保留原 expected），或依 ERB 重新推導 expected 並附行號；
   不可照 Python 輸出改。
5. **偏離收尾**：deviations.md「開局固定路徑」改寫（剩下的：跳過 UI 顯示本身）；S09「原作行為」條目改為說明
   「僅初期セット路徑如此」；STATUS 的已知問題同步更新。

## 查證要點
- `ADDCHARA 0` 產生的角色 `NO`、CALLNAME（"汎用キャラ"）來源：`CSV/Chara/Chara000汎用キャラ(女性).CSV`＋引擎 `CharacterData.cs`。
- 用到的內建函式（RAND、字串函式、EXISTCSV、CSVNAME 等）語意附 `reference/emuera-1824/...cs:行號`。
- GAME_OPTION／CONFIG 的預設值取自 `CONFIG_INIT` 與原文，不得推測。

## 測試（table-driven，expected 由 ERB 推導）
- 預設開局（FixedRng 或固定 seed 的手算片段）：角色數、NO、CALLNAME、性格 TALENT、CFLAG:6、BASE:40–48 非 0 且在原文範圍內。
- CHARA_MAKE_STATUS_TALENT 系、AGE_SETTING 各分岐的代表 case。
- 戰鬥：預設開局角色的胸部重量補正後敏捷為正常值（以 `battle.hantei` 既有式手算）。
- 初期セット選項仍產生 S03–S09 的既有狀態（既有測試改走此選項）。
- Web 整合：兩種開局都能進 SHOP。

## 模擬
隨機方針 250 場（seed 0–249，預設開局）：停止原因頻度、敗北後存活半日數，並與 S09（初期セット）對照，寫進 STATUS。

## 完成條件
pytest 全綠；STATUS、flow.md、deviations、unresolved 更新；新的 DEVIATION／UNVERIFIED 登記。
