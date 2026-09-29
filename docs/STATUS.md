# 現況（唯一真相，≤150 行）

更新：2026-09-29

## 已完成

- 建立 repo，`source/earGVP/` 原作基線入庫（唯讀）。AGENTS.md、PLAN.md。
- **S01**：原作分析 + 專案骨架。
  - era 事實 wiki：`docs/wiki/era/flow.md`、`variables.md`、`csv.md`、`battle-overview.md`。
  - `pyproject.toml`（src layout）、`src/eragvt/`；`python -m eragvt --check-data` 載入全部原作 CSV 並列摘要。
  - `eragvt.data.load_game_data()`：12 張名稱表、Item（含價格）、Str 初期值、GameBase／VariableSize／_Replace、
    77 名角色 CSV（遞迴、BOM 有無、CRLF/LF、名稱索引、64 位元 RELATION）。
  - `tests/`：59 個 table-driven 測試，expected 由 CSV 原文手抄。

## 下一步

- **S02**：核心狀態模型（範圍已依 S01 分析調整，見 PLAN.md 的 S02 說明）：
  1. `GameState`：DAY/TIME（一回合 = 半天，TIME 0 晝 1 夜）、MONEY、FLAG（dict 稀疏）、ITEM（衣裝持有）、SAVESTR、
     `MOB_FLAG`、`SHIELD`；全域 `GLOBAL` 另存。
  2. `Character`：由 `CharaDef` 建立（BASE=MAXBASE=CSV 值）；BASE/MAXBASE/ABL/TALENT/EXP/MARK/JUEL/EX/CFLAG/CSTR/
     CDFLAG/EQUIP/RELATION/TCVARn；`CFLAG:240` 固有番號。常數（`予定_*`、`状態_*`、TCVARn 狀態位元）做成 Enum/IntFlag。
  3. 角色列表語意：第 0 名 = MASTER（Chara999 ダミー），玩家角色從 1 起；TARGET 指標。
  4. JSON 存讀檔（版本化）；只存 era 存檔變數 + CHARADATA/SAVEDATA 變數（非 SAVEDATA 的 `#DIM` 不存）。
  5. 文字輸出層：PRINT 系列 → 行緩衝（含顏色、按鈕 `[n]`），供 Web 顯示；`NarrationService` 介面佔位
     （簽名 `(口上番號, 代碼, 性格) -> 文字|None`，對應 `KOJO_ROOT`）。
- S03 建議的最小開局路徑：預設隊伍 `初期セット/0_特捜戦隊.ERB@SHOKISET_SELECT_0`（ADDCHARA 301/302/303 + `SHOKISET_CSVFIX`），
  跳過 `CHARA_MAKE_MAIN`。

## 已知問題

- 未決事項見 `docs/wiki/bridge/unresolved.md`；最重要的是戰鬥回合數 `TFLAG:0` 的遞增處（S05 前要解）。
- 原作 CSV 有兩處瑕疵（Chara299 `100.`、Chara998 佔位符），載入器已容錯並記警告。
