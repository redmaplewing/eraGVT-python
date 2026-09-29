# 現況（唯一真相，≤150 行）

更新：2026-09-29（S04）

## 已完成

- 建立 repo，`source/earGVP/` 原作基線入庫（唯讀）；`reference/emuera-1824/` 引擎原始碼（查證用）。
- **S01**：原作分析 wiki（`docs/wiki/era/`）＋ `src/eragvt` 骨架、CSV 載入器。
- **S02**：狀態模型（`eragvt.state`）、版本化 JSON 存讀檔、文字輸出層、`NarrationService`。設計：`docs/wiki/python/state.md`。
- **S03**：查證補課 + 新遊戲 + SHOP Web。
  - Part 0：unresolved「Emuera 規格」全部對照引擎原始碼（僅剩無 BOM 檔編碼一項待實機確認）。修正：CSV 解析（省略／無法解析 → 1、
    不 trim、`;` 不處理、番号重複保留先者、JUEL 名稱查 palam）、存檔範圍（TFLAG 存、TCVARn 不存、遊戲代碼／版本檢查）、
    新遊戲 [0, 999]＋TARGET=1、`_Replace.csv`、自動按鈕（移植 ButtonStringCreator）、DAY 改為陣列、flow.md 引擎流程。
  - Part 1：`eragvt.game.opening`（EVENTFIRST 最小路徑：NORMAL＋特装戦隊 301–303，含 CHARA_MAKE_FINALIZE×2、LEVELSTATUS、
    CSVFIX、武器解碼、SET_LIMIT_DAY、RESEARCH_QUOTA）。
  - Part 2：`eragvt.game.shop`／`session`、`eragvt.web`（FastAPI＋Jinja2）。`python -m eragvt` 可在瀏覽器開新遊戲、
    看 SHOP、預約 101–108、切換操作角色、一括設定、存讀檔（0–19＋自動存檔 99）。測試共 227 個。
- **S04**：行動執行＋回合結束。`[100]` 確認後跑完一回合回到 SHOP（晝→夜→翌日晝），可重複並存讀檔。
  - `eragvt.game.action`：`ACTION_MAIN`（一次一人、FLAG:798/799、支援人數、控え・行動不能 → 強制休憩、
    `ACTION_NGREASON`）、`REST`、`TRAINING`（0–10 全選項、INPUT 以 generator 等待；BASEUP／SEIKAKU_HOSEI_F／
    SENGIUP／GET_EXP＋CHECK_LEVELUP／GET_SYUREN）。
  - `eragvt.game.turnend`：`run_turn`（JUMP／BEGIN 迴圈）、`EVENTTURNEND` 主幹（SET_PARTYMEMBER、ENDING 判定骨架、
    RECALC_PARTYMEMBER、BOSS_TENTACLE_RECOVER、DAILY_DEFENCE／POPULARITY、夜間事件的開始條件）、
    `EVENTSHOP` 一般分岐（PARASITE、SMALL_TENTACLE、BIRTH_AUTO_RANDOM、晝夜、RECOVERY_OVER_TIME、ESTRUS_CYCLE、
    日期、CALC_INCOME_EXPEND、新聞旗標、CHECK_SHIELD_ALL）。session 新增 `turn`／`halted` phase。
  - 各行動影響範圍與開局狀態下的事件觸發表：`docs/wiki/era/actions.md`。測試共 273 個。


## 下一步

- deviations.md 各項：使用者 2026-09-29 裁決「暫時維持現狀，嚴重到無法推進時再評估」。S04 新增 5 項待裁決（見該檔）。
- **S05：戰鬥核心**（規格待寫 `docs/sessions/S05-*.md`）。具體起點：
  1. 出撃：`ACTION.ERB`:74–98 → `ゲーム内_戦闘処理/ENCOUNT.ERB@ENCOUNT`:5（ボス／悪堕ち遭遇）→ 無則
     `@MOB_TENTACLE_ENCOUNT`（:429）→ `BEGIN TRAIN`。目前 `action_main` 對出撃丟 NotImplementedError
     （`src/eragvt/game/action.py` 末尾），`run_turn` 對 `Step.TRAIN` 也是 NotImplementedError。
  2. TRAIN 流程（flow.md §0／§7、battle-overview.md）：`BATTLE_TRAIN.ERB@EVENTTRAIN` → `@SHOW_STATUS` →
     `@COM_ABLEn` → `@SHOW_USERCOM` → 輸入（指令番號直接 DOTRAIN）→ `@EVENTCOM`→`@COMn`→`@SOURCE_CHECK`→`@EVENTCOMEND`
     → `BATTLE_TRAIN_AFTER.ERB@EVENTEND` → `BEGIN TURNEND`（接回 `turnend.event_turnend`）。
     session 需新增 TRAIN 的輸入 phase（沿用 `run_turn` 的 generator 方式：`Step.TRAIN` 時 `yield from` 戰鬥）。
  3. 接上後可解除的偏離：拠点防衛（`ACTION_GUARD.ERB`，未遭遇部分很短）、`RAID_HANTEI`／`SMALL_TENTACLE_ATTACK` 的跳過
     （`turnend._skip_event`，S06 可一併做事件戰）。
  4. 雜魚戰結束路徑（unresolved「原作邏輯」）在 S05 查清。

## 已知問題

- 未決：`docs/wiki/bridge/unresolved.md`；偏離：`docs/wiki/bridge/deviations.md`（尚未經使用者裁決）。
- 無 BOM 的 7 個角色 CSV 在原版 1.824 會以 Shift-JIS 讀（亂碼）；本程式以 UTF-8 讀，可能是 +v10 差異，待實機確認。
- 開局僅支援「NORMAL＋特装戦隊」；其他初期セット／自訂角色會 `NotImplementedError`。
- 可玩範圍：休憩・鍛錬。其他行動、11 日目夜的日數超過結局、救出／妊娠等狀態會進入 Web「停止」畫面（deviations）。
- 襲撃／救援（DAY ≥ 3）與子触手襲来成立時只顯示「スキップ」訊息（deviations）。
