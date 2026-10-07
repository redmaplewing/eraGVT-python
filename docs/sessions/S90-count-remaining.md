# S90：W07 其餘原生 COUNT 同步

## 完整成果
- 接續S88／S89同一COUNT項，合併核對count wiki剩餘七群206個迴圈搜尋行；不是206個獨立功能，不再按小函式拆階段。
- 包含攻擊數值61、ABL16、狀態19、製作／除錯22、SHOP11、事件41、其他戰鬥36；逐群確認已接catalog、原生可達、原作停用及既有受限範圍。
- 只同步既有原生流程的共享迴圈計數，保留原演算法／RNG／文字；不新增敘事、角色經歷生成或既有W02／W04受限分支，不重查已記錄阻塞。
- 沿GameState.count；正確開始、CALL覆寫、NEXT／BREAK／RETURN時序，FOR LOCAL／CCOUNT不誤寫COUNT；不以函式尾常數代替本體時序。
- 實際呼叫者全部接通；原作未完成／不可達者保留來源證據，剩餘缺口據實記錄，不能宣稱全部W07完成。

## 查證與驗證層級
- 依AGENTS→STATUS→PLAN→count wiki；局部查原文附檔案@函式:行號，引擎沿已確認證據，新增疑問才查reference。
- 來源推導table-driven expected先紅後綠，採等價類代表及跨CALL邊界，不逐等價入口複製測試。
- 子代理跑定向測試；提供最少必要真瀏覽器fixture，全新25歲人工前態及中性顯示，列出操作與expected。
- 本階段涵蓋初始化／事件等群組：先確認實際修改是否影響開局、回合排程、共用RNG或存讀控制流；若有，列明來源並觸發一次標準500局，否則只定向＋必要真瀏覽器＋主代理一次全pytest。
- 不因共用COUNT會保存或觸及共用檔名就自動500；不與全pytest並行，純文件沿用結果。

## 收尾
- 產品／測試／fixture凍結後通知主代理；主代理獨立驗收與提交，子代理不commit/push。
- 更新count wiki及既有deviations項；有新UNVERIFIED列具體查證，不自行裁決。STATUS／PLAN交主代理。
- source／reference唯讀；LF／UTF-8無BOM；最後回報做了什麼、已查證依據、需要使用者決定。

## 驗收結果
- 206行分195原生、1catalog、5無呼叫／不可達及5未移植除錯；既有一般流程已同步，除錯留W08，不稱COUNT整項或W07完成。
- 新增40案，子代理定向`1406 passed, 1 warning in 17.33s`；主全pytest `12 failed, 5586 passed, 1 warning in 204.75s (0:03:24)`。
- 第一輪修正僅套組取消expected：原FOR列表終99，RETURN不還原；完整state比較保留。新子代理定向136過；主代理受影響整檔`54 passed, 1 warning in 0.92s`，無剩餘失敗，產品未改故沿用其餘5586案／瀏覽器，不稱單次5598全測。
- 兩路真瀏覽器status 2000→5000→999→88（37→2）及export 1→1→0→88（272）通過；COUNT1=74、dump/load一致、RNG不變、四年齡欄25、catalog／console0、journal0、無worker，均回標題。
- tmp/s90/browser-summary.json與browser-status／export.png保存證據；局部人工前態非完整開局／存檔選單；服務及頁籤已關。
- 開局／引繼REPEAT僅原有bit與角色增刪、無新CALL消費者；本次不改核心控制流程／RNG／存讀格式且未結W07，不跑500，沿S88基線。source／reference未動，無新增裁決。
