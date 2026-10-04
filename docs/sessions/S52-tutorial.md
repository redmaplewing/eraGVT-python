# S52：開局遊戲說明

## 目標
- 接通開局 MODE_SELECT [300] 的 TUTORIAL，消除可點選入口的未移植停止。
- 依原作提供說明內容、可達分頁／選單、等待及返回，閱讀後能正常繼續開局。

## 範圍
- 精確定位 TUTORIAL 定義及開局呼叫，讀原文確認完整可達流程。
- 固定文字從原作抽取，互動邏輯手翻，不新增 ERB 直譯器。
- 核對 INPUT／WAIT／PRINTW、顯示狀態、RESULT／RESULTS 與返回流程，附原文及引擎行號。
- 不擴充其他未移植系統，不自行補寫原作不存在的教學或更動原作規則。
- 如原作存在未完成內容或疑義，附證據記錄，需改動時交使用者裁決。

## 驗收
- 先紅後綠，從原文推導 table-driven expected。
- 覆蓋全部可達章節、合法／無效輸入、等待、返回與重入；固定文字抽取可重現。
- 少量Web整合，確認開局進入說明後可返回並繼續新遊戲。
- 主代理獨立完整pytest；source／reference唯讀、UTF-8無BOM／LF、diff檢查。
- default與tokusou各seed 0–249、max-shop 200、actions 101–108，前景每批50局。
- 對照tmp/s51完整記錄，核對seed全集、批次exit、log／JSONL及catalog失敗。
- 更新STATUS（≤120行）與相關wiki；新未決／偏離才登記。
- 主代理驗收後commit／push main，完成S52即停止。
