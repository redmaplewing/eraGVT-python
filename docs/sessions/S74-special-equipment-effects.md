# S74：W03 特殊裝備的戰鬥回合效果

## 完整成果與範圍
- 保持W03佇列，完成既有特殊裝備506／507／509於SOURCE_CHECK回合結算的實際效果；驗收B04，只回填本次實測邊界。
- 從game/battle/source_check.py@source_check的裝備停止追查原作MISC_PATCH及全部直接相依，完整手翻三種裝備的條件、狀態修改與執行順序。
- 接到原SOURCE_CHECK位置，核對效果在勝利判定、運動結算及敵行動之前的原次序；不能只增加無呼叫者的輔助函式。
- 沿原規則處理裝備欄位、兩形態、消耗／回復／狀態、亂數與共用RESULT(S)；不依裝備名稱猜作用，不自行加入保護或修正原作。
- 遊戲邏輯原生Python；口上／地の文沿既有catalog例外。若實際路徑遇INPUT，沿generator等待，不同步耗盡或代選。
- 其他W03的觸手服199／運動判定及無內衣仍另接續；W02[8]、W05返り血與W08原作錯誤不納入。

## 查證與測試
- 依序讀AGENTS、STATUS、PLAN、本規格；精確搜尋先看總筆數，只讀必要局部。原作附檔案@函式:行號，引擎行為附reference路徑:行號。
- 先由原文列出table-driven前態與expected，先紅後綠；亂數走注入RNG，驗短路與耗用次序。
- 所有新測試／瀏覽器皆全新人工25歲、兩形態預先25歲；不改產品年齡規則，不生成或摘錄露骨敘事。
- 覆蓋三種裝備、沒有相關裝備、作用與不作用門檻、上下限／正負邊界及原作實際狀態組合；不把Python輸出反推成expected。
- 至少由實際戰鬥指令→SOURCE_CHECK→下一個原生輸入驗三種裝備，核對裝備效果與後續回合順序，不只測孤立helper。
- 原測試若需調整driver，保留原expected；catalog驗證可比原分派節點／順序，不摘錄敘事。

## 驗收與收尾
- 提供tmp/s74/browser_fixture.py，使用fresh-adult-25-v1／臨時存檔進真實戰鬥輸入；列出每種裝備的原文推導操作與預期。
- fixture可遮蔽敘事並提供唯讀一般狀態端點，保留真實generator與規則；明記人工前態，不冒充自然遭遇或完整B04。
- 子代理完成定向測試後凍結產品／測試／fixture，主代理獨立全pytest、真瀏覽器與正式500：兩入口各seed0–249、max-shop200、actions101–108、前景50局一批，比對S73完整JSON。
- 更新必要既有wiki／PLAYABILITY／bridge；STATUS／PLAN由主代理收口；繁體中文、LF／UTF-8無BOM、source／reference唯讀。
- 子代理自行核對git status／diff，回報成果／依據／裁決，不commit/push；主代理驗收後明確stage並推main。

## 完成驗收
- 手翻TK_DRONE／HP_AUTOREGAIN／SERVANT，接回SOURCE_CHECK原位置；原文完整路徑／行號與引擎依據見wiki/era/clothing.md的S74段。
- 實作前首案紅燈：`1 failed in 0.23s`，裝備507在source_check.py:81觸發既有NotImplementedError；後新增158案，定向`517 passed, 1 warning in 5.29s`。
- 主代理獨立全pytest：`4795 passed, 1 warning in 148.20s (0:02:28)`；產品／測試凍結後驗收，既有Starlette/httpx警告。
- 三路真瀏覽器皆998不改狀態／RNG、按原201後返回戰鬥選單；變身1、EX12、先制9→8、氣力700、TARGET1與尾格保留。
- 506敵HP2950／體力700，507體力720，509反應24／增量0；全部年齡欄25、catalog失敗0、console錯誤0。只驗人工B04回合邊界，不宣稱自然遭遇／完整B04。
- 證據tmp/s74/browser-{506,507,509}-{pending,invalid,complete}.json及equipment-*-complete.png；原catalog純顯示，其餘Null／遮敘事，臨時存檔，測試頁與伺服器已關。
- 正式500局每50局前景一批，default247上限／3回標題、tokusou250上限；與S73停止表及完整JSON逐seed一致，catalog／fixture失敗0，十批退出0、seed／log／參數核對，見tmp/s74/adult25-v1/audit.json。
- 無新增UNVERIFIED／DEVIATION，bridge既有裁決保持；source／reference未動。下一份S75仍在W03，接外衣199運動／回合結算。
