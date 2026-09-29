# AGENTS.md — eraGVT Python 翻寫

## 專案目標

把 `source/earGVP/`（eraGVT，Emuera/ERB 遊戲）**手工翻寫**成 Python + HTML 介面的版本。
不做 ERB 直譯器（先前試過，效果不好）；每個系統都讀懂 ERB 意圖後寫成原生 Python。

本 repo 為 **private**：`source/` 是第三方公開發布的原作，不得把 repo 轉 public。

## 接手必讀（依序，讀完就開工，不要再掃整個 repo）

1. 本檔
2. `docs/STATUS.md`（唯一的現況真相：做到哪、下一步、已知問題）
3. `docs/PLAN.md`（階段規劃與模型分工）
4. 本次 session 的任務規格 `docs/sessions/Sxx-*.md`（使用者會指定）
5. 需要時才查 `docs/wiki/` 對應頁面

## 鐵則

- `source/` **永遠唯讀**。不改、不重新編碼、不移動。
- 文件主語言繁體中文；日文只保留在原名、路徑、函式名、字串 key。
- 不確定的事寫進 `docs/wiki/bridge/unresolved.md`，不要硬猜成定論。
- 引用原作一律寫 `檔案路徑@函式名`，例如 `ERB/インターミッション画面/SHOP.ERB@USERSHOP`。

## 治理：刻意保持輕量（繼承 tohoTW 的教訓）

tohoTW(PY) 的 log／checklist／index 各膨脹到 450–700KB，每個 session 光讀文件就燒掉大量 token，
而且工作被切成過細的「清點→實作→重評」循環。本專案用付費額度開發，**以下規則優先於完整性**：

- **不寫 append-only 的巨型 log**。歷史交給 `git log`；commit message 寫清楚做了什麼。
- `docs/STATUS.md` 上限 150 行，只寫「現在」：完成的階段一行帶過、下一步、已知問題。
- 一個 session 做完一個 `docs/sessions/Sxx` 規格裡的完整成果，不另外拆 inventory／readiness 等中間交付。
- wiki 頁只在「之後的人真的需要查」時才寫，每頁盡量 < 300 行。
- 讀原作用 `grep`／看局部，**不要**整包 `cat` ERB 目錄；口上（148K 行）除非任務相關不要讀。

## 開發方式

- 測試先行：從 ERB 原文推導 prestate 與 expected，寫 table-driven pytest，先紅後綠。
  Expected **不得**由 Python 實作的輸出反推。
- 隨機性：遊戲邏輯一律透過注入的 RNG 物件（可 seed），測試用固定 seed 或 stub。
- 整合測試只在 Web API／存讀檔邊界放少量代表 case。
- 資料與文字優先「抽取」而非手寫：CSV → 資料檔；口上／地の文 → 文字 catalog（見 PLAN）。
- 新模組必須有實際呼叫者（接到遊戲流程或 Web），不做沒人用的 foundation。

## 技術棧（沿用 tohoTW）

- Python ≥ 3.10，套件 `src/eragvt/`，`pyproject.toml` + pytest。
- Web：FastAPI + Jinja2 + 輕量原生 JS；後端持有遊戲狀態，前端只負責顯示與輸入。
- 存檔：版本化 JSON（明碼）。舊 Emuera `.sav` 匯入不在初期範圍。
- AI 敘事（口上／地の文生成）是後期功能；介面先留 `NarrationService`，無 AI 時回落原文 catalog。

## 檔案與 Git

- 新檔一律 **LF + UTF-8（無 BOM）**。Windows 上用 Python 寫檔要 `newline="\n"`；
  commit 前看 `git diff --cached --numstat`，只改幾行卻顯示上千行 = 行尾被污染。
- 只 `git add` 本次任務真正改到的路徑；不要 `git add -A`。
- 雲端 session：在自己的分支工作，完成後 commit + push，由使用者合併進 `main`。
- 不 force-push、不改寫歷史、不刪分支，除非使用者明確要求。
- 子 agent 改完檔案，自己用 `git status`／`git diff --stat` 核對範圍，不要只信它的自述。

## 完成一個 session 的收尾清單

1. `pytest` 全綠（貼出摘要行）。
2. 更新 `docs/STATUS.md`（仍 ≤150 行）。
3. 有新的未決事項 → `docs/wiki/bridge/unresolved.md`。
4. 確認 `git status` 沒有動到 `source/`。
5. commit（訊息結尾照 system 指示加 Co-Authored-By）並 push。
