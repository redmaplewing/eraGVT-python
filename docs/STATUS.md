# 現況（唯一真相，≤150 行）

更新：2026-09-29

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

## 下一步

- **使用者決定**：`docs/wiki/bridge/deviations.md` 各項（特別是「亂數」「身體資料生成」「FLASHNEWS」「[1]はい 會中斷」）。
- **S04**：行動執行 + 回合結束（規格待寫）。建議範圍：
  1. `ゲーム内_行動実行処理/ACTION.ERB@ACTION_MAIN`:6–175（一次處理一名角色）＋`REST`、`TRAINING` 兩種行動先做；
     其餘行動（出撃→TRAIN 屬 S05；活動／防衛／支援／情報／自由）先以 `NotImplementedError` 或 DEVIATION 佔位。
  2. `インターミッション画面/SHOP_TURNEND.ERB@EVENTTURNEND`:3–139 的主幹（`JUMP ACTION_MAIN` 迴圈、SET_PARTYMEMBER、
     ENDING 判定骨架、RECALC_PARTYMEMBER、夜間事件依 config 開關；未移植者列 deviations）。
  3. `@EVENTSHOP` 的一般分岐（:158–215：晝夜切換、RECOVERY_OVER_TIME、日期推進、CALC_INCOME_EXPEND、新聞 FLAG:60、
     CHECK_SHIELD_ALL）。session 需支援「行動 → TURNEND → BEGIN SHOP（一般狀態 → 自動存檔）」。
  4. Web：[100] 確認後實際跑完一回合回到 SHOP。

## 已知問題

- 未決：`docs/wiki/bridge/unresolved.md`；偏離：`docs/wiki/bridge/deviations.md`（尚未經使用者裁決）。
- 無 BOM 的 7 個角色 CSV 在原版 1.824 會以 Shift-JIS 讀（亂碼）；本程式以 UTF-8 讀，可能是 +v10 差異，待實機確認。
- 開局僅支援「NORMAL＋特装戦隊」；其他初期セット／自訂角色會 `NotImplementedError`。
