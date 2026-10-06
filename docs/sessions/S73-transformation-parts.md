# S73：W03 變身衣裝零件描寫接通

## 完整成果與範圍
- 保持W03佇列，完成衣裝零件的變身呼叫路徑；驗收B04／B08，只回填本次實測邊界。
- 從game/battle/commands.py@_msg_nanori_byousha現有停止查原作MESSAGE_BATTLE_CHARA_NANORI_BYOUSHA，接回真實變身指令及原後續。
- 查清全部EQUIP零件分支、優先序、重複組合、CUSTOMIZABLE及服裝狀態來源；不把現有停止清單當完整原規則。
- 依原文區分遊戲狀態與純敘事：遊戲邏輯手翻，口上／地の文沿既有catalog例外，不建立新的ERB直譯捷徑。
- 核對裝備、變身、TARGET、RESULT(S)、顏色及亂數的原有副作用；沒有原文依據就不加入重算或補正。
- 若原文或真實口上有INPUT，沿現有generator等待通道；不靜默吞輸入、不自動選答。
- 本階段完成此零件描寫及必要直接相依；無內衣、特殊裝備結算／觸手服等其餘W03停止另接續，不跳往W04。
- W02[8]既有阻塞、W08候選列表原作錯誤及原作未完成內容維持原紀錄，不擴張處理。

## 查證與測試
- 依序讀AGENTS、STATUS、PLAN、本規格；精確搜尋先看總筆數，只讀必要局部。原作附檔案@函式:行號，引擎行為附reference路徑:行號。
- 由原文推導table-driven前態與expected，先紅後綠；遊戲亂數走注入RNG，核對耗用次序。
- 新案例皆全新人工25歲、兩形態預先25歲；不改產品年齡規則，不生成或摘錄露骨敘事。
- 覆蓋零件單項／互斥／同時存在、無零件、不同服裝／變身狀態及原作實際門檻；顯示案例只比結構、分派或原文catalog來源。
- 至少一案從實際變身指令進入並回到戰鬥選單，核對消耗、狀態、後續順序與同步讀值；不能只驗孤立文字函式。
- 若測試需調整driver，保留原expected；原作錯誤先查意圖，不自行更正。

## 驗收與收尾
- 提供tmp/s73/browser_fixture.py，以fresh-adult-25-v1／臨時存檔進實際戰鬥輸入；列出原文推導的操作與預期。
- fixture可遮蔽敘事並使用唯讀一般狀態端點；保留真實指令與規則，明記人工邊界，不冒充自然遭遇／全裝備矩陣完成。
- 子代理完成定向測試後凍結產品／測試／fixture，主代理獨立全pytest、真瀏覽器與正式500：兩入口各seed0–249、max-shop200、actions101–108、前景50局一批，比對S72完整JSON。
- 更新必要既有wiki／PLAYABILITY／bridge；STATUS／PLAN由主代理收口。繁體中文、LF／UTF-8無BOM、source／reference唯讀。
- 子代理自行核對git status／diff，回報成果／依據／裁決，不commit/push；主代理驗收後明確stage並推main。

## 完成驗收
- 新增85案先紅後綠，定向326案通過；主代理全pytest：4637 passed, 1 warning in 160.67s (0:02:40)。
- 描寫只有純文字與LOCAL，使用原catalog；COM0仍為Python。CUSTOMIZABLE原文無賦值，保留0；引擎落尾及STATIC零初值已附wiki。
- 主代理真瀏覽器先998、再可見201（原COM0別名），回戰鬥選單；核對體氣500→700、EX12、耐久130、TARGET及尾格、兩形態25歲，catalog／console失敗0。
- 本次原catalog、其餘Null、遮蔽敘事標籤，未替換產品規則；證據tmp/s73/browser-*.json與battle-complete.png，不稱自然遭遇或整列B04／B08完成。
- 正式500：default247上限／3回標題、tokusou250上限；catalog／fixture失敗0；完整JSON與S72逐seed一致，十批退出／seed／log／參數核對。
- 模擬曾因軟體更新中斷：保留已完成的前150局，中斷的default150–199批次封存後重跑，其餘批次依序接續；最終500局資料完整。
- 無新增UNVERIFIED／DEVIATION；下一項S74特殊裝備回合效果仍屬W03。
