# S80：W05 戰鬥干擾與返血／發現分支

## 完整成果與範圍
- 依固定佇列處理W05第一組共用戰鬥事件；W04套組10／序章觀看具體阻塞保留，不冒充完成，不重查同一受限內容。
- 完成battle/func.py的act_limit觀眾妨礙、battle/source_check.py的_supart_blood／_rescue_deadnum，接原生回合與勝利呼叫者。
- 先查三項全部分支與相依呼叫；若原作條件確實不會到達，提供完整呼叫／寫入證據，不自行開啟；查到原作bug先記錄，不擅修。
- 遊戲狀態手翻為Python，既有文字走catalog；不新增、改寫或摘錄露骨敘事，不做通用ERB執行捷徑。
- 末王回復／動態敵方安全網／ISGIRLY留W05後續完整成果；本次不混入W06模式或W07全面顯示重做。

## 查證與測試
- 依序讀AGENTS、STATUS、PLAN、本規格及必要battle-overview；局部查來源，全域精確搜尋先計數，不掃整庫。
- 原作附檔案@函式:行號；引擎的整數、RESULT(S)、TARGET、迴圈／返回等有新疑點時查reference，不能憑慣例。
- 先從ERB推導table-driven expected再實作，保留紅綠摘要；覆蓋啟用／關閉、命中／未命中、多人／空集合、門檻、RNG耗用及共用暫存殘值。
- 25歲人工fixture從建立開始設定；不得事後改年齡、偷偷改原作分支或以Null取代待驗輸入。產品年齡規則不變。
- 新狀態處理必須實接act_limit／SOURCE_CHECK，不做無呼叫者模組；至少各一個真run_train／Web邊界案例。
- 若有等待／選擇，接既有generator與明確輸入請求，不能代答；訊息副作用不能只猜成顯示。

## 驗收與收尾
- 提供tmp/s80/browser_fixture.py、可見前態控制表單、精確操作與原文expected；B04／B05／B09一般戰鬥操作與設定ON/OFF用真瀏覽器驗收。
- 人工遭遇／救出前態明確標示，不宣稱自然長局、完整救出系統或整列B矩陣完成；臨時存檔與本機服務隔離。
- 子代理完成定向測試及文件後凍結；主代理獨立全pytest、真瀏覽器驗收。
- 2026-10-06使用者改採AGENTS分級驗證；S80工具修正沿用已通過全pytest／瀏覽器，採修正後完整批次default0–249與tokusou0–99共350局及78／88定向重跑；其餘停止，不重跑完整500。
- 模擬沿fresh-adult-25-v1、max-shop200、actions101–108、前景50局一批，與S79相同seed比較；未完成批次不計入正式350局，完整500基線仍為S79。
- 更新必要wiki／PLAYABILITY／bridge；STATUS／PLAN由主代理收口；有新未決／偏離據實列出，既有裁決不重開。
- LF、UTF-8無BOM、繁體中文；source／reference唯讀。自查git status／diff，只回報實際變更，不commit/push。
- 最後三段回報：做了什麼／已查證的依據／需要使用者決定（UNVERIFIED／DEVIATION），附測試摘要與範圍限制。
