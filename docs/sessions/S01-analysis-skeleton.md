# S01 — 原作分析 + 專案骨架

建議模型：Opus 5.5（effort high）。開場先讀 `AGENTS.md`、`docs/STATUS.md`、`docs/PLAN.md`。

## 目標

讓後續 session 不必再重新摸索原作，並有一個能跑測試的 Python 專案。

## 交付物

### A. era 事實 wiki（`docs/wiki/era/`，每頁 < 300 行）

1. `flow.md`：主流程與入口函式的實際呼叫鏈（EVENTFIRST → SHOP → 行動 → TRAIN 戰鬥 → TURNEND），
   每一步標 `檔案@函式`。以 `ERB/※ゲーム開始からのフロー.txt` 為起點驗證。
2. `variables.md`：CSV 定義的變數種類（ABL/BASE/TALENT/EXP/MARK/PALAM/CFLAG/CDFLAG/FLAG/TFLAG/ITEM/STR…）
   各自在本作的用途摘要；`#DIM` 全域變數（`ERB/DIM.ERH`、各 `.ERH`）列表與用途。
   參考 `●開発者向け資料/●GVTフラグ一覧.txt`。只寫主流程會用到的，其他標「未調查」。
3. `csv.md`：`CSV/` 各檔格式、角色 CSV（`CSV/Chara*`，含子資料夾與 `_ADD`）的欄位格式、`_Replace.csv`、`VariableSize.csv`。
4. `battle-overview.md`：戰鬥（TRAIN）結構概觀：遭遇、回合、指令分類（`戦闘コマンド(ヒロイン)`、`戦闘コマンド(性攻撃)`）、
   敵方行動、PALAM 計算、結束條件。只寫架構，細節留給 S05。

### B. Python 骨架

- `pyproject.toml`（套件 `eragvt`，src layout，依賴 fastapi/jinja2/uvicorn，dev：pytest/httpx）。
- `src/eragvt/`：`__init__.py`、`__main__.py`（啟動 Web 的佔位）、`data/`（CSV 載入）。
- CSV 載入器：
  - 讀 `source/earGVP/CSV/` 的變數名表（Abl/Base/Talent/Exp/Mark/Palam/Item/Train/Str/Cdflag…）→ `{index: name}`。
  - 讀角色 CSV（遞迴含子資料夾）→ 角色定義物件（番號、名前、呼び名、BASE/ABL/TALENT/CFLAG/CSTR 等初期值）。
  - 處理 UTF-8 BOM、註解（`;`）、空欄。
- `tests/`：table-driven 測試，expected 值**直接從 CSV 原文手抄**（例如某角色的番號、名前、某個 TALENT 值），
  不從載入器輸出反推。

### C. 收尾

- `docs/STATUS.md` 更新；未決事項寫入 `docs/wiki/bridge/unresolved.md`。
- 在 STATUS 的「下一步」寫下 S02 的具體建議（依分析結果調整 PLAN 的 S02 範圍，必要時直接修改 PLAN.md）。

## 不做

- 不實作遊戲邏輯、Web 畫面、存檔。
- 不讀 `口上/` 內容（只記錄其目錄結構與派發方式一段即可）。

## 驗收

- `pytest` 全綠。
- 四份 wiki 頁存在且每條事實都有 `檔案@函式` 或 `檔案:行` 出處。
- `git status` 顯示 `source/` 無變更。
