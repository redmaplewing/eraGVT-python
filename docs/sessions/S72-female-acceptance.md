# S72：W03 女體受容取得與生命週期續行

## 完整成果與範圍
- 保持W03佇列，接續S70／S71後仍未移植的女體受容；驗收B04／B05，只回填實測邊界。
- 完成game/battle/ablup.py@_talents的取得停止，經既有yobai.py@_ablup1接真實夜間，並經EVENTEND接戰後能力更新。
- 原列yobai.py@yobai:204實為候選列表覆寫後TARGET越界的原作錯誤，歸W08且保留停止；不是第二個女體受容取得點（見PLAYABILITY更正）。
- 由停止點及精確原文搜尋查清原函式、全部條件、狀態修改與必要相依；不得預設只是單一TALENT賦值，也不得依名稱猜行為。
- 同一成果完成此取得功能的可達呼叫與後續；若原函式有INPUT，使用S70／S71等待通道，不代選、不插入另一選單。
- 保留變身／TARGET／能力與特徵相依、衣裝或尺寸重算的原次序；只處理原文實際要求的相依，不擴張成整個裝備工作包。
- W02[8]既有具體阻塞、其他裝備、SUPART_BLOOD與未完成原作內容不納入；不能因本項完成就宣稱W03或整列生命週期完成。

## 查證與測試
- 依序讀AGENTS、STATUS、PLAN、本規格；精確搜尋先看總筆數，只讀必要局部。原作附檔案@函式:行號，引擎行為附reference路徑:行號。
- 原作既有錯誤先查意圖與上下游，不自行修正；真的查不到才記UNVERIFIED，新偏離要明示，不自行設計新規則。
- table-driven由ERB推導前態與expected，先紅後綠；亂數走注入RNG，保留耗用次序。
- 所有新測試／瀏覽器為全新人工25歲、兩形態預先25歲，不改產品年齡規則、不執行未成年性內容、不生成或摘錄露骨敘事。
- 覆蓋取得／不取得的原條件邊界、重複呼叫、兩形態與相依狀態，以及TARGET／RESULT(S)返回責任。
- 至少各一個真實夜間與能力更新呼叫案例；若存在互動，驗無效重試、等待前後次序及返回，不以孤立函式或假generator代替整合。
- 已查ERB/ヒロイン関連/ABL_UP_CHECK.ERB@_ABLUP:444–479五分支及SWAP；夜間ERB/ゲーム内_イベント発生/強制発生イベント/FORCE_夜這い.ERB@YOBAI_ACTION:1048、1063、2645呼叫共用取得。取得無INPUT，兩入口仍以原生夜間選擇／戰鬥撤退驗收。
- 既有測試若需改driver，保留原expected與呼叫順序；不得在產品碼加入吞None或同步代答層迎合測試。

## 驗收與收尾
- 提供tmp/s72/browser_fixture.py，以fresh-adult-25-v1／Null／臨時存檔進本次真實入口；唯讀端點只暴露一般狀態、TARGET及年齡，列出原文推導預期。
- 主代理真瀏覽器操作實際可達選項／觸發及完成後續行；明記人工前態或函式邊界，不冒充自然通關。
- 產品／測試定向通過後凍結，主代理獨立全pytest及正式500局：兩入口各seed0–249、max-shop200、actions101–108、前景50局一批，與S71完整JSON比對。
- 更新必要既有wiki／PLAYABILITY／bridge；STATUS／PLAN由主代理收口；文件繁體中文，LF／UTF-8無BOM，source／reference唯讀。
- 子代理核對git status／diff，回報成果／依據／裁決，不commit/push。主代理驗收後明確stage並推main。

## 完成驗收
- 新增50案，先紅後綠；定向247案通過。主代理全pytest：4552 passed, 1 warning in 155.78s (0:02:35)。
- 主代理真瀏覽器night／battle兩路通過無效998及原選項2／999，核對取得、交換、TARGET、解除變身、RESULT尾格及全員兩形態25歲；console錯誤0。
- fixture只遮蔽文字與保留原數字按鈕，操作實際YOBAI／run_train；證據tmp/s72/browser-*.json與battle-complete.png，不稱自然遭遇或整列B04／B05完成。
- 正式500：default247上限／3回標題、tokusou250上限；catalog／fixture失敗0；完整JSON與S71逐seed一致，十批退出／seed／log／參數核對。
- 無新增UNVERIFIED／DEVIATION；RYOUTOU原派發CHARM照原文。夜間候選列表既有原作錯誤歸W08且保留停止；下一項S73變身衣裝零件仍屬W03。
