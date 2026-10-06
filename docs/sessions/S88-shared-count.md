# S88：W07 共用 COUNT 生命週期與角色編輯／模式邊界

## 完整成果與範圍
- 接續W07既有COUNT偏離，讓catalog與原生Python呼叫讀寫同一個原作COUNT；不以新增但沒有呼叫者的欄位作為完成。
- 本階段完整邊界：COUNT共用／JSON遷移／交易，以及個別角色編輯主入口、姓名、一人稱、性格亂數、CSV、單詞命名與模式選單／模式判定；17處原作迴圈。其他原生群組保留既有偏離，下一成果仍接COUNT，不把整項結案。
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
- 本次必跑500：`reference/emuera-1824/Emuera/GameData/Variable/VariableCode.cs:45、94`確認COUNT=0x0B在0x3C存檔範圍，`VariableData.cs:663–688`實際存讀；新增JSON v4與v1–3遷移，確實涉及跨系統存讀。後續補局部原生終值不自動再次觸發，需新增核心影響或W07結包依據。
- 若需要500，沿S84最新完整25歲人工基線、兩入口各seed0–249、max-shop200、actions101–108、前景50局一批，不與全pytest並行；其後新完整基線以STATUS為準。
- 更新既有COUNT偏離與未決原項、PLAYABILITY及必要wiki；查不到才記UNVERIFIED，不自行裁決原作錯誤。
- W07其他舊WAIT與catalog失敗處置尚未結包，不宣稱完整B矩陣通過；STATUS／PLAN由主代理收口。
- 繁體中文、LF／UTF-8無BOM，source／reference唯讀；自查git範圍、不commit/push，最後三段回報。

## 驗收證據
- 新增50案；初始共用36案與編輯7案先紅後綠；定向502通過（11.34秒，1個既有警告）。主代理全pytest：`5515 passed, 1 warning in 188.68s (0:03:08)`。
- 主代理兩路真瀏覽器通過：editor一人稱10／性格19／姓名20、收尾[700,3]；csv選0→確認收尾[4,74]；中性catalog讀同值，dump/load函式邊界一致，完成回標題。
- 全新25歲人工前態，替代MAXBASE41保留-1哨兵；catalog／console失敗0、journal0、無worker。tmp/s88/browser-summary.json及兩張截圖；伺服器／頁籤已關。
- 500局在default seed216遇CLOTH_CUSTOMIZE_OPTION_DRAW(992)顯示失敗，已停剩餘批次並做第1輪修正；已有完整200局及第五批17局，不能稱完整500。最終比較與提交前範圍檢查由主代理收口。未決13→12、COUNT既有偏離保持未結案，沒有新增裁決。

- 第1輪修正根因不是COUNT：S86新增事件衣裝992顯示，3004函式info的CSTR寫入令option整函式被catalog靜態拒絕；現用窄原生option轉接與四條原文RESULTS片段，不開放info遊戲邏輯。
- 新增12案（7個真cloth_durability分支先紅後綠），定向233通過；default216單跑shops201、catalog／fixture0，與S84只多adapter事件計數3。
- 追加25歲事件衣裝真UI，820→830→998後category2、turn0、COUNT[9,0]、RNG不變，catalog／console0、journal0、無worker；browser-cloth-repair.png與browser-summary.json，服務／頁籤已關。
- 窄修正僅在先前必失敗的3004 option呼叫生效；前四完整批200局catalog0，可沿用，重跑default200–249再續tokusou。編輯／CSV的產品路徑未改，沿既有UI證據。
- 修正後主代理全pytest：`5527 passed, 1 warning in 194.26s (0:03:14)`，已含新增12案；產品未再改，後補文件沿用此結果。
- 最終500局通過：default247上限／3回標題，tokusou250上限，catalog／fixture0；與S84僅default216多原生衣裝option事件3，其餘模擬輸出欄位一致。tmp/s88/adult25-v1/audit.json為新完整基線。
- 驗收組成：修正前無catalog失敗的完整default0–199四批沿用；修正後default200–249及tokusou0–249六批，均前景50局一批／16隔離worker、不與全pytest並行。初次失敗17局另存seed216-initial-failure，不計入最終500。
- source／reference未動、LF／UTF-8無BOM；STATUS≤150、規格≤60；下一S89仍留同一COUNT工作項。
