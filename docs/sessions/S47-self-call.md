# S47：一人稱設定

## 目標
- 接通狀態畫面 P1 [12] 的 FIRSTSETTING_CHARA_SELFCALL，消除既有停止點。
- 原作入口：`ERB/ヒロイン関連/ステータス画面/SHOW_STATUS_CHARA_SELECT_PAGE1.ERB`。
- 規則來源：`ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_SELFCALL`。

## 範圍
- 預設稱呼／字形、角色名字、手動輸入、性格預設、確認／取消完整流程。
- 讀音分析與音數限制、無效輸入、INPUT／INPUTS／PRINTW 等依原作及引擎查證。
- 優先重用既有 SELF_CALL、SELF_CALL_LIST、SELF_CALL_ANALYSIS 等手翻工具，先核對語意。
- CFLAG／CSTR／RESULT／RESULTS 的寫入時機與取消時殘值依原文，不自創修正。
- 固定顯示文字優先抽取，不新增 ERB 直譯器。
- 只接通此次設定的實際呼叫者，不擴充其他角色製作或事件。
- 原作疑似錯誤記錄依據；需要偏離時交使用者裁決。

## 驗收
- 先由 ERB 推導 table-driven 測試並確認紅燈，再實作。
- 涵蓋各選項、字形、讀音邊界、取消與完成的狀態，以及實際畫面／Web／存讀檔。
- 完整 pytest 全綠，source／reference 無修改，LF／UTF-8 無 BOM。
- 預設與 tokusou 各 seed 0–249、max-shop 200、actions 101–108；每批 50 局前景執行。
- 與 S46 逐 seed 比較完整模擬記錄，回報停止原因及 catalog 失敗。
- 更新 STATUS（≤120 行）與相關 wiki；有新未決／偏離才更新對應登記。
- 主代理驗收、commit 並 push main；本階段完成即停止。

## 驗收結果
- 新增107案，定向回歸172 passed；主代理完整pytest：3165 passed, 1 warning in 259.85s (0:04:19)。
- 標準500局：default246上限／4回標題、tokusou250上限；catalog失敗0，完整紀錄逐seed與S46一致。
- 10批皆exit=0，seed全集及log／JSONL一致；`tmp/s47/audit.py` 驗證通過。
- 原作自訂碼重入後[50]的CALL_LIST越界明確停止，其餘特殊讀音／殘值照原作保留；無新增偏離。
