# S36：市民戰

## 目標與範圍
- 使用者已同意依原作補上市民戰，完成本階段後停止。
- 接通 ENCOUNT_CITIZEN 與市民戰的遭遇、戰鬥、勝敗及戰後續行。
- 納入情報收集與自由行動等既有呼叫路徑，消除 config 3 已觀察到的市民戰停止。
- 依實際依賴補齊必要規則；不擴展其他獨立候選系統。
- 忠實轉換既有原作，不新增情節或規則；報告只描述工程行為。

## 實作要求
- 先讀 AGENTS.md、STATUS、PLAN，再按需要定位原作與現有實作。
- 先從 ERB 推導 table-driven 測試並確認紅燈，再手寫原生 Python。
- 遊戲規則附原作檔案@函式:行號；引擎行為查 reference 並附行號。
- RNG 注入、呼叫順序與 RESULT／RESULTS 殘值均照原作。
- 輸入依原作等待；不可用替代行為繞過未實作路徑。
- source/、reference/ 唯讀；不變更既有裁決。
- 新的未知或偏離先明確回報，不自行裁決。

## 驗收與收尾
- 完整 pytest 全綠；實作與測試先固定，再跑最終模擬。
- 預設與 tokusou 各 seed 0–249、max-shop 200、actions 101–108。
- 模擬使用前景分批，每批 50 局，保留逐局停止原因與 catalog 失敗數。
- 正常 config 2／3 各 seed 0–9、max-shop 40、actions 101–108，驗證市民戰續行。
- 對照 S35：標準預設 246 上限／4 回標題，tokusou 250 上限。
- 對照 S35：config 2 為 8 上限／2 回標題；config 3 為 5 上限／1 回標題／4 市民戰停止。
- 更新 STATUS（≤120 行）、相關 wiki；有新增事項才更新 unresolved／deviations。
- 檔案 LF、UTF-8 無 BOM；確認唯讀目錄未動。
- 子 agent 不 commit／push；主 agent 獨立驗收後 commit 並推上 main。
- 最後回報：做了什麼／已查證的依據／需要使用者決定。

## 完成結果（2026-10-04）
- 已完成原生遭遇／敵資料／戰後續行與既有情報、自由行動入口；文字沿用catalog。
- 新增68案例；首次執行因citizen模組不存在紅燈，完成後市民與既有戰鬥回歸430 passed。
- 子agent全套：2175 passed, 1 warning in 189.17s；主agent獨立全套：2175 passed, 1 warning in 227.52s。
- 正常config2：8上限／2回標題；config3：9上限／1回標題，原4次市民戰停止消除。
- 標準預設：246上限／4回標題；tokusou：250上限，與S35相同。
- 520局catalog失敗0；12批exit0、seed全集及JSONL與逐局log一致，稽核摘要在 `tmp/s36/audit.json`。
- STATUS為98行；引用與原作特殊行為見 `docs/wiki/era/citizen.md`；無新增UNVERIFIED／DEVIATION。
- source/、reference/未動；UTF-8無BOM、LF與git diff --check通過；子agent未commit／push。
