# S03 — 查證補課 + 新遊戲 + SHOP

建議模型：Opus 5.5（effort high）。開場先讀 `AGENTS.md`（**特別是新增的「查證規則」**）、`docs/STATUS.md`、
`docs/PLAN.md`、`reference/README.md`。

## Part 0：查證補課（先做，約佔本 session 1/4）

S01／S02 有數項 Emuera 行為是憑推測決定的（當時 repo 沒有引擎原始碼）。現在 `reference/emuera-1824/` 已有原始碼，
逐項查證 `docs/wiki/bridge/unresolved.md`「Emuera 規格」段所有 `[ ]` 項目，**有出入就改程式與測試跟原作一致**：

1. 存檔包含哪些變數（`VariableCode.cs` 旗標、`VariableData.cs`/`CharacterData.cs` 存檔實作）→ 修正 `eragvt.state.savefile`。
   TFLAG 等非存檔變數不應存。
2. 新遊戲後的 TARGET／ASSI／其他系統變數初始值（`VariableEvaluator.ResetData` 等）→ 修正 `GameState.new`。
3. 角色 CSV 省略值、`100.`、非數值（`xx`）的處理（`ConstantData.cs`、`CharacterData.cs` 的 CSV 讀取）→ 修正 `csv_loader`。
4. `_Replace.csv` 值的 trim 規則。
5. 自動按鈕 `[n]` 的範圍規則（`GameView/` 內）→ 修正 `eragvt.text.output.split_buttons`。
6. `@EVENTSHOP`／TURNEND 後的流程（`Process.SystemProc.cs@beginTurnend`/`beginShop`）→ 更新 `docs/wiki/era/flow.md`。
7. 回頭檢查 `docs/wiki/era/flow.md`、`battle-overview.md` 裡標「eramaker 慣例」「推定」的敘述，改成附 `reference/...:行號` 的事實。

每項查完在 unresolved.md 打 `[x]` 並寫依據（`檔案:行號`）。若原始碼與本作表現可能不同（+v10 派生版），照 `reference/README.md` 處理。

## Part 1：新遊戲最小路徑

依 `docs/STATUS.md`「下一步 → S03」第 1–2、4 項（開局設定、預設隊伍 特捜戦隊 301–303、CHARA_MAKE_FINALIZE 必要部分、
`@EVENTSHOP` 的 `DAY == 0` 分支、相性→RELATION 轉換）。

- 跳過角色製作 UI 與序章文字，但**狀態結果必須與原作跑完同路徑後一致**；跳過了哪些會影響狀態的步驟，列入 `deviations.md` 請使用者決定。
- 測試：開局後的關鍵變數（MONEY、FLAG:0/2/3/4/5/7/8/41/50/51/100/852、ITEM、三名角色的 CFLAG:6/100/240/999 等）
  expected 由 ERB 原文逐行推導並在測試註解寫行號。

## Part 2：SHOP Web UI（第一版）

依 `docs/STATUS.md`「下一步 → S03」第 3 項：FastAPI + Jinja2，後端持有 `GameState` + `TextOutput`，
`@SHOW_SHOP` 翻成 Python 輸出 `Line` 列表，前端渲染成文字與按鈕；按鈕回傳數字 → `@USERSHOP` 分派。
先做：切換 TARGET、101–108 行動預約、100 確認（停在「將執行 ACTION_MAIN」）、200/300 存讀檔。其他選單項目顯示為「未實作」。

- 整合測試：少量 FastAPI `TestClient` case（開新遊戲 → 看到 SHOP → 預約行動 → 存檔 → 讀檔後狀態一致）。
- `python -m eragvt` 啟動本機 Web。

## 不做

- 行動實際執行（S04）、戰鬥、角色製作完整 UI、口上。

## 驗收

- `pytest` 全綠；unresolved.md「Emuera 規格」段全部 `[x]`，或寫明為何查不到。
- 能在瀏覽器開新遊戲、看到 SHOP、預約行動、存讀檔。
- 結束報告依 AGENTS.md 分三段，明列所有 UNVERIFIED／DEVIATION。
