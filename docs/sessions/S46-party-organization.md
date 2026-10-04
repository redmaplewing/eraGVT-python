# S46：SHOP 隊伍編成

## 目標
- 接通 SHOP [50] 的原生 Python 隊伍編成，以及編成需要的候補成員列表。
- 依 `ERB/インターミッション画面/SHOP_ORGANIZE_PARTY.ERB@SHOP_ORGANIZE_PARTY` 手翻。
- 依 `SHOP_SHOW_STATUS_LIST.ERB` 共用出場／候補列表，接回既有 SHOP 呼叫者。

## 範圍與查證
- 核對 SHOP 入口條件、TARGET 初值、各角色狀態限制與人數計算函式。
- 選擇／取消選擇、位置交換、出場與候補切換、休憩排程重設、完成後 TARGET／FLAG:61／RESULT。
- 交換前 RELATION 欄位與出場旗標的交換順序完全依原作。
- SWAPCHARA 等引擎行為查 reference 並附行號，不自行修補角色索引。
- 原作顯示與判斷若有矛盾，先保持原文與原邏輯並記錄，不自行修正。
- 顯示文字優先抽取，沿用既有輸出基礎設施；不新增 ERB 直譯器。
- 不處理其他 SHOP 選單或既有待裁決項目。

## 驗收
- 先依原文推導 table-driven 測試並確認紅燈，再實作。
- 覆蓋滿員、特殊狀態、無效輸入、雙向交換、RELATION、候補行動重設與 RNG。
- 實際 GameSession 畫面與少量 Web／存讀檔邊界測試。
- 完整 pytest 全綠；source／reference 無修改。
- 預設與 tokusou 各 seed 0–249、max-shop 200、actions 101–108，50 局一批前景執行。
- 統計停止原因、catalog 失敗並與 S45 逐 seed 對照。
- 更新 STATUS（≤120 行）、相關 wiki；新的偏離／未決事項才更新對應登記。
- 主代理驗收後 commit 並 push main，本階段完成即停止。
