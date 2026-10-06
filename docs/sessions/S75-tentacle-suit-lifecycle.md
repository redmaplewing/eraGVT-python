# S75：W03 觸手服199的運動與回合結算

## 完整成果與範圍
- 保持W03佇列，完成外衣199在既有SOURCE_CHECK兩處停止：_motion_palam運動判定與SUBEVENT_BATTLE_ACTTENTACLESUIT回合處理；驗收B04／B05。
- 查原作兩個入口及全部必要直接相依，完整手翻條件、裝備／角色狀態、亂數與執行順序；不把內衣400的既有處理誤當外衣199。
- 保留一般／變身兩形態所讀服裝欄位、耐久與原作實際門檻；不依名稱猜規則，也不自行補保護、上下限或重算。
- 接回真實戰鬥指令→SOURCE_CHECK→下一個原生輸入；若效果引發狀態事件或等待，沿S70／S71既有generator通道續行，不同步代答。
- 遊戲邏輯原生Python，口上／地の文沿既有catalog例外；僅處理本次外衣199的必要相依。
- W03無內衣路徑、W02[8]、W05返り血與W08既有原作錯誤另依佇列處理；不冒充W03或完整生命週期驗收已完成。

## 查證與測試
- 依序讀AGENTS、STATUS、PLAN、本規格；精確搜尋先看總筆數，只讀必要局部。原作附檔案@函式:行號，引擎行為附reference路徑:行號。
- 由原文推導table-driven前態與expected，先紅後綠；RNG注入，核對短路、呼叫次序與耗用。
- 所有新案例皆全新人工25歲、兩形態預先25歲；不改產品年齡規則，不生成或摘錄露骨敘事。
- 覆蓋穿戴／未穿戴、兩形態切換、運動分支與實際門檻、事件觸發／不觸發，以及TARGET／RESULT(S)與後續流程責任。
- 至少由實際戰鬥輸入完成一回合並返回選單；只驗孤立helper或假generator不能代替整合。必要等待驗無效重試不重跑先前亂數／狀態。
- 既有測試若調整driver，保留原expected；原作錯誤先查意圖，不擅自修正。

## 驗收與收尾
- 提供tmp/s75/browser_fixture.py，以fresh-adult-25-v1／臨時存檔進真實戰鬥入口，列出原文推導的操作與預期。
- fixture可遮蔽敘事並提供唯讀一般狀態端點，保留真實generator與規則；明記人工前態，不冒充自然遭遇或整列B04／B05。
- 定向測試完成後凍結產品／測試／fixture；主代理獨立全pytest、真瀏覽器及正式500：兩入口各seed0–249、max-shop200、actions101–108、前景50局一批，比對S74完整JSON。
- 更新必要既有wiki／PLAYABILITY／bridge；STATUS／PLAN由主代理收口。繁體中文、LF／UTF-8無BOM、source／reference唯讀。
- 子代理自行核對git status／diff，回報成果／依據／裁決，不commit/push；主代理驗收後明確stage並推main。

## 完成驗收
- 外衣199兩處停止已移除；原SOURCE_CHECK無條件CALL／未穿戴RETURN0、兩形態位數、耐性與事件階段、原索引／補正順序及原生等待照原文。完整依據見wiki/era/clothing.md的S75段。
- 首輪39紅（36缺實作、3個測試前態漏動作，依原479–487修正），首輪39綠後擴至新增142案；最新定向`423 passed, 1 warning in 2.71s`。
- 子代理自查補四行純顯示及衣名快照時，首次父全pytest中止、不列驗收；重新凍結後父獨立全pytest：`4937 passed, 1 warning in 147.02s (0:02:27)`，既有Starlette/httpx警告。
- 兩路真瀏覽器998不改狀態／RNG、原201完成後返回選單；cost體氣700／耐性93／階段0，event階段1／經驗1，實測699／677／88符合預先定義下降區間，精確算術由table驗證。
- 共同敵HP3000、變身1、TARGET1、先制9→8、RESULT99=345／RESULTS8保留；全部年齡欄25、catalog失敗0、console錯誤0。原生等待四題與無效9亦有定向案例，不重跑先前RNG／狀態。
- 證據tmp/s75/browser-{cost,event}-{pending,invalid,complete}.json及{cost,event}-complete.png；原地文catalog、其餘Null／遮敘事、臨時存檔，只稱人工回合邊界，測試頁與伺服器已關。
- 正式500前景50局一批，default247上限／3回標題、tokusou250上限；停止表及完整JSON與S74逐seed一致，catalog／fixture失敗0，十批退出0與seed／log／參數核對，見tmp/s75/adult25-v1/audit.json。
- 無新增UNVERIFIED／DEVIATION，bridge既有裁決保持；source／reference未動。下一份S76仍在W03，接初始衣裝CLOTH_NO_INNER，整包尚未宣稱完成。
