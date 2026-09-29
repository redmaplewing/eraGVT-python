# S02 — 核心狀態模型

建議模型：Opus 5.5（effort high）。開場先讀 `AGENTS.md`、`docs/STATUS.md`、`docs/PLAN.md`，
需要時查 `docs/wiki/era/variables.md`、`csv.md`。

## 目標

建立之後所有系統共用的遊戲狀態、角色、存讀檔與文字輸出層。範圍以 `docs/STATUS.md`「下一步 → S02」的 1–5 項為準。

## 交付物

1. **`GameState`**（`src/eragvt/state/`）：DAY/TIME、MONEY、FLAG（稀疏 dict）、ITEM、SAVESTR、MOB_FLAG、SHIELD 等；
   全域資料（GLOBAL 系，對應 SAVEGLOBAL/LOADGLOBAL）獨立成另一個物件與檔案。
2. **`Character`**：由 S01 的 `CharaDef` 建立；各變數陣列用稀疏 dict，未設定讀為 0／空字串，與 era 一致。
   主流程會用到的常數（`予定_*`、`状態_*`、TCVARn 位元等）做成 `IntEnum`/`IntFlag`，每個值註明來源 `檔案:行`。
3. **角色列表**：index 0 = MASTER（Chara999），`add_chara(no)`（對應 ADDCHARA）、`del_chara`、TARGET/ASSI 指標。
4. **存讀檔**：版本化 JSON（`{"format": "eragvt-save", "version": 1, ...}`），只存 era 存檔變數與 SAVEDATA/CHARADATA 變數；
   存→讀→再存結果逐位元組一致（round-trip 測試）。
5. **文字輸出層**：PRINT 系列 → 結構化行（文字、顏色、換行、等待、按鈕 `[n]`），Web 之後直接渲染；
   `NarrationService` Protocol 佔位 + 「無 AI 時回傳 None」的預設實作。
6. **RNG**：可注入、可 seed 的亂數物件放進 `GameState` 周邊（不放進存檔以外的全域）。

## 原則

- 每個模型只放「S03–S06 確定會用到」的欄位；其他變數用通用稀疏 dict 承接即可，不逐一建模。
- 測試：table-driven；角色初期值 expected 由 CSV 原文手抄；存讀檔測 round-trip 與版本欄位。
- 發現 era 規格不明處 → `docs/wiki/bridge/unresolved.md`，不要卡住。
- 若寫了 Python 端設計決策（例如稀疏 dict 的語意），記在 `docs/wiki/python/state.md`（< 300 行）。

## 不做

- 遊戲流程、Web 畫面（S03）、戰鬥、口上內容、舊 `.sav` 匯入。

## 驗收

- `pytest` 全綠；`python -m eragvt --check-data` 仍正常。
- 能從程式建立「MASTER + 301/302/303 三名角色」的狀態並存讀檔成功（這就是 S03 開局要用的狀態）。
- `docs/STATUS.md` 寫好 S03 的具體下一步；`source/` 無變更。
