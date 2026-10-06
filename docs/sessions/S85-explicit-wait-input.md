# S85：W07 真確認等待與有效輸入

## 完整成果與範圍
- W06結包後依固定佇列進W07，先完成共用WAIT／PRINTW確認的實際互動；S84暴露的評分／成就殘留戰鬥按鈕是代表症狀，不只修測試fixture。
- 查現有原生等待、成就包裝及catalog generator等待的真正來源，將已判定的確認等待傳遞為WaitInputRequest；一般INPUT／INPUTS保留原資料與預設語意。
- 檢查所有相同等待包裝的實際呼叫者，一次完成此共用路徑；不能依歷史wait_count或yield None猜測，把真正數字選擇誤當確認。
- 確認畫面只能以當前有效控制項推進；舊選單按鈕不得在確認期間誤導或送出另一指令，Enter與可點按確認均有效，返回標題／重啟／舊token重送維持原保護。
- 不以清空所有敘事歷史取代正確輸入狀態；實際INPUT選項仍照原作可操作。等待本身不得額外覆寫RESULT(S)或消耗RNG。
- S60b、S79、S80、S83的已完成明確等待直接重用；新模組須當次接到實際流程。
- W07的SHOP／戰鬥資訊與分類、字型／HTML／圖樣、COUNT與catalog失敗處理仍按包內剩餘範圍推進，不在本次冒充整包完成。
- W02／W04既有具體阻塞不重查，原作未完成仍保留；不新增、改寫或摘錄露骨敘事，測試只需中性輸出及25歲人工資料。

## 查證與測試
- 讀AGENTS、STATUS、PLAN、本規格、docs/wiki/bridge/generic-input.md及必要bridge原項；按實際呼叫局部讀原文與引擎，附檔案@函式:行號／reference檔案:行號。
- 先寫原文／引擎expected的定向紅綠，含確認前後狀態、RESULT(S)保留、數字／文字不被誤分類、已完成等待與重送／重啟邊界。
- 子代理只跑受影響定向測試；驗證工具與模擬器若需接受新請求，只補相關契約，不全盤重跑既有工具測試。
- 提供tmp/s85/browser_fixture.py與必要最少代表路徑：中性混合INPUT／INPUTS／WAIT、實際成就／評分或戰鬥後等待，清楚列可見前態與expected。
- 人工資料建立起年齡25，保留原生未設定哨兵、不改產品年齡規則；真流程catalog照常執行，可遮蔽敘事但不能吞掉等待。
- 產品／測試／fixture完全凍結後通知主代理，再由主代理真瀏覽器及提交前一次全pytest；凍結後只收文件，不偷偷追加測試邏輯。

## 分級驗證與收尾
- 此成果為輸入呈現與明確請求傳遞，預設定向＋必要瀏覽器＋一次全pytest，不因共用檔名自動500；W07未結包。
- 若查證發現實際改動跨系統狀態寫入、排程、RNG或存讀行為，先在規格寫明影響證據，才擴大相關驗證；工具修正只重跑受影響範圍。
- 通過後純文件修改沿用證據；沒有新產品變更不重做已通過的瀏覽器路徑。
- 更新generic-input與既有deviations等待原項，精確說明已解／仍未解範圍；有新UNVERIFIED依規則記錄，不以文件刪掉問題。
- STATUS／PLAN由主代理收口；其餘必要PLAYABILITY／wiki同步，避免新增巨型日誌。
- 繁體中文、LF／UTF-8無BOM、source／reference唯讀；子代理自查範圍、不commit/push；三段回報成果／依據／需要裁決。

## 子代理交付證據
- 四處同步等待全部傳遞WaitInputRequest；模板確認期間只呈現歷史選項文字；既有catalog明確等待通道不重寫。RESULT(S)／RNG及保存順序按原作保留。
- 定向`280 passed, 1 warning in 5.45s`；模擬器明確型別契約`1 passed, 5 deselected in 0.07s`，詳細指令與來源見[共用輸入](../wiki/bridge/generic-input.md)。
- tmp/s85/browser_fixture.py兩入口API冒煙通過；mixed為中性catalog，achievement為全新25歲人工資料真GET_STATE_TROPHY。產品／測試／fixture凍結後才交主代理真瀏覽器與一次全pytest。
- source／reference未動；UTF-8無BOM／LF及git diff --check通過。無新增UNVERIFIED／DEVIATION；未逐處核對的舊等待仍列W07，不宣稱整包完成。

- 主代理兩路真瀏覽器通過，catalog／console0、RNG不變、RESULT(S)及保存順序正確，完成後worker／journal清空；完整pytest `5404 passed, 1 warning in 181.72s (0:03:01)`。
- 正常INPUT轉送前wait_bridge會恢復callback，工具只改確認型別辨識、無策略改變；本階段不跑500，沿用S84基線。下一成果S86決策資訊與分類，W07未結包。
