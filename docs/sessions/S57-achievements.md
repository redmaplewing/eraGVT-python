# S57：W01 成就取得、保存與查看

## 目標與範圍
- 接續 PLAN 的 W01 首個完整成果；本階段不宣稱整包 W01 完成。
- 原生 Python 實作共用成就取得與 SHOP[800] 列表，接上現存實際呼叫者。
- 依原作查證 GLOBAL 位址、取得條件、重複取得、輸出、SAVEGLOBAL 時機與返回流程。
- 文字優先抽取；不新增原作沒有的成就、條件或劇情。
- 歷代紀錄與未包含的解鎖明確留在 W01，不跳至 W02。

## 查證與實作
- 依序讀 AGENTS、STATUS、PLAN，再查 SHOP_TROPHY.ERB 的 UNLOCK_ACHIEVEMENT／SHOW_TROPHY。
- 精確搜尋共用成就呼叫者，先計數再完整分類；涵蓋 catalog hook 與原生遊戲呼叫者。
- 引擎語意查 reference，程式／測試／wiki 附檔案、函式及行號。
- 從原文推導 table-driven expected，先紅後綠；不得由 Python 結果反推。
- 沿用既有 GlobalStore 與輸入通道，不建立無呼叫者的基礎模組。
- 遇到未明規則先查證；不自行修原作錯誤或批准偏離。

## 驗收與收尾
- B03：真瀏覽器進 SHOP[800]，查看未達成／已達成及返回。
- B06／B07：以原作前態取得成就，查看、關程序重啟後保留；區分定向前態與自然遊玩。
- 驗證未達成不寫入、重複取得、原作保存時機與其他 GLOBAL 資料不被破壞。
- 主代理獨立全 pytest；流程改動跑 default／tokusou 各 seed0–249、max-shop200、actions101–108，前景50局一批。
- 對照 S55 逐 seed 停止原因及 catalog 失敗；若基線產物不可得，明列比較限制。
- 更新 STATUS（≤120行）、PLAN 的 W01 現況、PLAYABILITY 相關缺口與必要 bridge／wiki。
- source／reference 唯讀、UTF-8 無 BOM／LF；子代理不 commit、不 push。
- 回報三段與確切測試／模擬摘要；主代理驗收、commit/push main 後繼續 W01。

## 完成驗收
- 主代理獨立全pytest：`3788 passed, 1 warning in 404.00s (0:06:43)`。
- 正式500局：default246到上限／4回標題、tokusou250到上限；catalog失敗0，逐seed完整結果與S55一致。
- 真瀏覽器已驗取得前後保存時機、成就頁、返回及程序重啟；使用現行GLOBAL版本定向前態，不冒稱首次全域版本缺陷已解決。
- 驗收工具修正每seed目錄隔離及成就純確認不抽策略RNG，另有2項測試。
- 首次GLOBAL版本0問題待使用者裁決；Web數字確認差異留W07，未自行批准偏離。
- W01後續仍含歷代紀錄／通關數、6處成就觸發與解鎖消費端核對；本階段不換包。
