# S61：W02 一般身體／外貌編輯與共用入口

## 完整成果
- 承接S60，完成原作SIZE_SETTING的一般身體／外貌互動並接回共用角色編輯[6]；屬W02／B02、B08。
- 一般範圍包含年齡、身高、一般外貌、髮型／目光／色彩及人格；依原作完成合法輸入、取消、確認、重入及寫回，不代按預設。
- 性屬性等其餘分頁仍明確停止；共用資料複製與確認不任意刪欄，不新增產品年齡限制。文件標SIZE_SETTING部分完成，不宣稱全頁完成。
- 既有身體計算原生函式優先共用，遊戲邏輯手寫；固定文字抽取，不新增直譯器。
- 同函式既有status_screen入口一併整合；子供獨立流程保留原範圍，不把未驗路徑宣稱完成。
- TS／特殊裝備生命週期仍W03；其他個別選單及主製作人數／狀態仍後續W02。

## 查證與測試
- 讀AGENTS、STATUS、PLAN、本規格與相關wiki；限定查SIZE_SETTING及必要呼叫／計算依賴，不掃口上。
- 原作每項狀態／亂數／RESULT(S)與確認時序皆附檔案@函式:行號；引擎語意附reference行號。
- table-driven pytest先紅後綠；expected從ERB推導。注入RNG，驗取消／重入／確認殘值及原作權限。
- 沿用使用者已指定的全新25歲人工資料；瀏覽器與模擬角色實／外見年齡25，不改產品年齡範圍或使用者存檔。
- 測試呈現一般UI與數值結果，不新增敘事情節；不重查已查明的年齡來源，不重開既有裁決。
- 若具體分支需要新裁決，記錄精確原文與受影響操作；可獨立完成的工作繼續，不猜修原作。

## 驗收與交付
- 少量真實GameSession／Web案例驗共用入口到SHOP；以人工前態明示依賴，不以API取代瀏覽器。
- 提供可直接啟動的25歲人工瀏覽器fixture與操作順序；主代理依computer-use操作並核對狀態。
- 子代理定向測試後凍結產品；主代理獨立全pytest。
- 有遊戲流程變動，主代理以tools/sim_adult.py沿用fresh-adult-25-v1跑兩入口各seed0–249、max-shop200、actions101–108，每50局前景分批。
- 與S60同一人工基線tmp/s60/adult25-v1逐seed比較；catalog失敗／fixture停止／遊戲停止分開記錄。
- 更新STATUS≤120、PLAN同一W02、PLAYABILITY、相關wiki／bridge；不寫巨型歷史紀錄。
- source/reference唯讀、LF／UTF-8無BOM；只本次路徑。子代理不commit/push，父驗收後提交main。
- 最後三段回報成果／依據／裁決，明列未完成範圍；不得以未驗收工作冒充完成。

## 主代理最終驗收

- 全pytest：`3942 passed, 1 warning in 250.70s (0:04:10)`；共用與狀態兩入口25歲真瀏覽器均返回SHOP，細節見body-editor wiki。
- 正式500：default247上限／3回標題、tokusou250上限；catalog失敗0、fixture停止0；十批退出0，seed／log／JSONL／參數核對通過。與S60同一人工資料的500筆完整JSON逐seed一致。
- 新基線與核對結果：`tmp/s61/adult25-v1/`及`audit.json`；舊基線`tmp/s60/adult25-v1/`。source/reference未動，無新增未決事項。
- S61一般身體／外貌成果完成；SIZE_SETTING其餘操作、子供獨立流程與W02其他子選單仍未完成，既有W07顯示差異保留。
