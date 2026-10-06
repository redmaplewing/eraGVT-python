# S76：W03 初始衣裝的無內衣判定

## 完整成果與範圍
- 保持W03佇列，完成opening.py@chara_make_finalize中CFLAG:42==0的CLOTH_NO_INNER停止；驗收B02與B04的衣裝初始化邊界。
- 查CHARA_MAKE_FINALIZE原呼叫位置、CLOTH_NO_INNER完整定義與直接相依；區分0的原預設路徑和-1的明確設定，不自行補穿或改預設。
- 手翻實際服裝條件、兩形態／角色索引、回傳及RESULT語意；既有等價原生函式可共用，但必須逐項查證。
- 接回全部使用chara_make_finalize的既有入口，不另造無呼叫者的helper；一般衣裝與特殊外衣／內衣組合按原文驗證。
- 遊戲邏輯原生Python；不更動原作年齡規則，不處理W02[8]、W04其他套組或W08既有錯誤。
- 完成後只移除本次停止，核對W03剩餘條件與既有證據；沒有完整生命週期／編輯後戰鬥證據不得宣稱整包完成。

## 查證與測試
- 依序讀AGENTS、STATUS、PLAN、本規格；精確搜尋先看總筆數，只讀必要局部。原作附檔案@函式:行號，引擎附reference路徑:行號。
- 從原文推導table-driven前態與expected，先紅後綠；注入RNG並核對本次判定是否耗用亂數、RESULT(S)與TARGET責任。
- 所有新案例用fresh-adult-25-v1，全新人工25歲、兩形態四年齡欄25；不生成或摘錄露骨敘事。
- 覆蓋CFLAG42為0／-1／既有衣裝、原作判定各分支、單角色與全部角色finalize、兩形態相依與後續服裝資料重整。
- 至少一個真實編輯確認→finalize→SHOP或原呼叫者，以及一個初始化後進戰鬥的案例；不得以孤立helper取代。
- 若原作存在錯誤，先查完整分支與作者意圖，再記錄具體阻塞，不能自行修正。

## 驗收與收尾
- 提供tmp/s76/browser_fixture.py，以臨時存檔、人工25歲前態走真實輸入／確認；列出原文推導操作與預期。
- 可遮蔽敘事並提供唯讀狀態端點，保留產品generator與規則；明記人工前態及驗收邊界，不宣稱自然全流程。
- 定向測試完成後凍結產品／測試／fixture；主代理獨立全pytest、真瀏覽器與正式500：兩入口各seed0–249、max-shop200、actions101–108、前景50局一批，比對S75完整JSON。
- 更新必要既有wiki／PLAYABILITY／bridge；STATUS／PLAN由主代理收口。繁體中文、LF／UTF-8無BOM、source／reference唯讀。
- 子代理核對git status／diff後回報成果／依據／裁決與紅綠摘要，不commit/push；主代理驗收後明確stage並推main。
