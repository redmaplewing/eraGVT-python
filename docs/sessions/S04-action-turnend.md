# S04 — 行動執行 + 回合結束（一回合跑完回到 SHOP）

建議模型：Opus 5.5（effort high）。開場先讀 `AGENTS.md`、`docs/STATUS.md`、`docs/PLAN.md`，
需要時查 `docs/wiki/era/flow.md`（§5–§6）、`docs/wiki/python/state.md`、`docs/wiki/bridge/deviations.md`。

## 目標

SHOP 按 `[100]` 確認後，實際跑完一回合（每名角色的行動 → 回合結束 → 下一回合開始）並回到 SHOP，可重複進行並存讀檔。
路徑相對 `source/earGVP/ERB/`。

## 交付物

1. **`@ACTION_MAIN`**（`ゲーム内_行動実行処理/ACTION.ERB`:6–175）：一次一名角色、經 TURNEND 迴圈輪到下一人（FLAG:799）。
   - 本 session 完整翻寫：`予定_休憩` → `ACTION_REST.ERB@REST`、`予定_鍛錬` → `ACTION_TRAINING.ERB@TRAINING`、
     `IS_ACTION_INCAPABLE` 強制休憩、控え（CFLAG:999 == 0）強制休憩。
   - 其他行動（出撃＝TRAIN 屬 S05；活動／防衛／支援／情報／自由）：先查清楚各自對狀態的影響範圍；
     本 session 不實作者以 `NotImplementedError` 擋下，或在 Web 上不可選（登記 deviations）。
2. **`@EVENTTURNEND`**（`インターミッション画面/SHOP_TURNEND.ERB`:3–139）主幹：`JUMP ACTION_MAIN` 迴圈、`SET_PARTYMEMBER`、
   `ENDING` 判定（先做「是否觸發」的判定骨架；結局畫面本體可 NotImplemented）、`RECALC_PARTYMEMBER`、FLAG 重置、
   `BOSS_TENTACLE_RECOVER`、`DAILY_DEFENCE_CHANGE`、`DAILY_POPULARITY_CHANGE`。
   夜間事件（PRISON、BIRTH_HANTEI、YOBAI、RAID_HANTEI…）依 config（基本セット）判斷是否會觸發；
   開局狀態下不會觸發者寫測試證明「不觸發」，會觸發但未移植者登記 deviations。
3. **`@EVENTSHOP` 一般分岐**（SHOP_TURNEND.ERB:158–215）：晝夜切換、`RECOVERY_OVER_TIME`（:591）、日期推進、
   `CALC_INCOME_EXPEND`（:771）、新聞旗標、`CHECK_SHIELD_ALL`；`PARASITE`／`SMALL_TENTACLE_HANTEI`／`BIRTH_AUTO_RANDOM`
   同上處理（不觸發則測試證明）。
4. **session**：`[100]` → ACTION_MAIN → TURNEND → `BEGIN SHOP`（一般狀態呼叫 → 自動存檔 99）→ SHOW_SHOP。
   行動中的輸出照 Emuera 流程顯示；中途的 INPUT／WAIT 照現有 session 機制處理。
5. **測試**：REST／TRAINING 的數值（體力回復、能力上升等）、一整回合後的關鍵變數（DAY／TIME／MONEY／FLAG／各角色 BASE・CFLAG）
   expected 由 ERB 逐行推導；Web 整合測試加 1 case（開局 → 全員休憩 → [100][9] → 回到 SHOP 且 TIME=1）。

## 原則

- 查證規則同 AGENTS.md：引擎行為附 `reference/...cs:行號`，原作邏輯附 ERB 行號。
- 既有 deviations 維持現狀（使用者 2026-09-29 裁決），除非造成無法推進。

## 不做

- 戰鬥（出撃・防衛・事件戰的 TRAIN，屬 S05／S06）、口上、角色製作完整版、FLASHNEWS。

## 驗收

- `pytest` 全綠；瀏覽器可「開新遊戲 → 設定休憩／鍛錬 → 行動開始 → 回到 SHOP（夜）→ 再一回合（次日晝）」並存讀檔。
- `docs/STATUS.md` 寫好 S05 的具體下一步；`source/`、`reference/` 無變更。
- 結束報告依 AGENTS.md 分三段，明列所有 UNVERIFIED／DEVIATION。
