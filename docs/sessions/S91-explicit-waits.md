# S91：W07 原生 WAIT／PRINTW 明確等待

## 完整成果與範圍
- 接續S85：核對既有可達原生WAIT／PRINTW及舊數字yield等待，接為明確WaitInputRequest，使Web真的等待確認才續行。
- 先讀wiki/bridge/generic-input.md及既有等待通道，依呼叫鏈合併完成；不按每個小呼叫拆階段、不以盤點表當交付。
- 區分真正INPUT、INPUTS、WAIT、PRINTW／FORCEWAIT；不依歷史輸出、wait_count或yield None猜測輸入類型，不在TextOutput層偷偷重放遊戲邏輯。
- 既有同步函式需要接原生generator／已有等待轉送通道，必須整合所有實際呼叫者；CALL前後狀態、RESULT(S)、COUNT及RNG時序依原作保留。
- 沿用原文catalog與既有事件generator；不新增敘事或W02／W04已記錄受限分支。原作停用／未完成不新增等待。
- catalog失敗回復的產品裁決另留後續；本次不得以吞錯或當找不到來省略等待。

## 查證與驗證
- 依AGENTS→STATUS→PLAN→本規格；精確搜尋先總數後局部查原作及引擎，附檔案@函式:行號；沿用已確認的Enter不寫RESULT(S)規則。
- expected由來源推導，先紅後綠；用來源等價類驗確認前後寫入、CALL巢狀、連續等待／數字／文字、返回標題關閉，不把全部歷史測試重寫一遍。
- 子代理只跑受影響定向測試；提供最少必要真瀏覽器fixture，全新25歲人工資料或中性控制流，寫明可重現操作及expected。
- 預設定向＋必要真瀏覽器＋主代理一次全pytest；只傳遞原有等待、不改核心流程或RNG時，不跑500。若發現確認邊界影響跨系統排程／存讀等，列具體證據再擴大。
- 若模擬工具需要認明確wait，只驗受影響工具案例；不直接重跑全500。通過後純文件沿用結果。

## 收尾
- 更新generic-input wiki與既有deviations項，據實列仍未接來源，不冒充W07完成；新未決記unresolved，不自行裁決。
- 產品／測試／fixture凍結通知主代理，再交全pytest／瀏覽器驗收；STATUS／PLAN主代理維護。
- source／reference唯讀，UTF-8無BOM／LF；不commit/push，最後三段回報。
