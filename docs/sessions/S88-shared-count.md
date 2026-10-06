# S88：W07 共用 COUNT 與原生迴圈邊界

## 完整成果與範圍
- 接續W07既有COUNT偏離，讓catalog與原生Python呼叫讀寫同一個原作COUNT；不以新增但沒有呼叫者的欄位作為完成。
- 先查reference的REPEAT／REND／CONTINUE／BREAK、巢狀迴圈、函式呼叫、BEGIN與存讀生命週期；區分COUNT、明示FOR變數及函式區域變數，不把所有Python for都當REPEAT。
- 依精確pattern先看全作總筆數，再查實際已移植讀取／寫入及可達呼叫鏈；優先沿既有result wiki、unresolved GAME_MODE_CHECK及命名／性格／LOADCSV的已知COUNT遺留。
- 原生邏輯手寫對應COUNT邊界；catalog沿既有解析器共用狀態，不新增遊戲邏輯解譯能力，不以執行ERB取代原生實作。
- 原作沒有保存／重置的狀態不得額外保存／重置；需要結構改動時確認既有JSON相容與原作依據，有實質偏離交使用者裁決。
- 已記錄W02／W04阻塞不重查；不新增或改寫露骨敘事，一般功能與catalog用全新25歲人工資料或中性測試函式驗證，產品年齡規則不變。

## 查證與測試
- 依序讀AGENTS、STATUS、PLAN、本規格與必要wiki；原作附檔案@函式:行號、引擎附reference檔案:行號。
- 原文expected先紅後綠：零次／一般／提前退出／巢狀／跨CALL／INPUT暫停與恢復，及已知原生→catalog消費者代表鏈；不替每個等價for新增鏡像測試。
- 核對交易回復與原生hook後失敗的既有契約，不因共用COUNT而吞掉例外或重複狀態副作用。
- 子代理只跑受影響定向；提供最少必要tmp/s88/browser_fixture.py與可見前態／操作／expected，證明真實呼叫端用共用COUNT後仍可續行。
- 產品／測試／fixture完全凍結後交主代理，之後只收文件；主代理必要真瀏覽器及提交前一次全pytest。

## 分級驗證與收尾
- 實作前列COUNT寫入與其後消費、跨系統控制流及存讀的具體影響，再決定驗證層級；不能只因改共用狀態就自動跑500。
- 若查證影響跨系統開局／排程／RNG／存讀，補明確來源及理由後跑標準500；若只有未被後續控制流讀取的殘值與局部消費，採定向／必要瀏覽器／一次全pytest。
- 若需要500，沿S84最新完整25歲人工基線、兩入口各seed0–249、max-shop200、actions101–108、前景50局一批，不與全pytest並行；其後新完整基線以STATUS為準。
- 更新既有COUNT偏離與未決原項、PLAYABILITY及必要wiki；查不到才記UNVERIFIED，不自行裁決原作錯誤。
- W07其他舊WAIT與catalog失敗處置尚未結包，不宣稱完整B矩陣通過；STATUS／PLAN由主代理收口。
- 繁體中文、LF／UTF-8無BOM，source／reference唯讀；自查git範圍、不commit/push，最後三段回報。
