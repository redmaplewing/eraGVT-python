# S84：W06 七模式生命週期與結局周回

## 完整成果與範圍
- 依PLAN的W06／B06完成七模式日期、增援、招募、禁止條件、終局或持續規則及引繼；重用S79入口、S82末王交接、S83剩餘規則成果。
- 以原作實際入口與條件建立精簡模式對照及定向案例；SURVIVAL不可假有限通關、SANDBOX不強加結局。原作停用ENDING_6維持停用。
- 至少一條新局→SHOP／行動→結局存檔→新session讀回→引繼新周SHOP的連續驗收；其餘模式／結局分支用原文人工前態覆蓋。
- 分清自然流程與人工優勢／終端前態；不以直接呼叫結局函式冒充新局連續通關，也不為測試偷偷跳過角色製作或真輸入。
- 可用明示的人工25歲資料、資源／敵強度測試前態縮短驗收；未經實際輸入的部分不得稱完整瀏覽器流程。
- 查漏的合法模式分支若有實際缺口，同成果以原生Python接回呼叫者；不另拆清點／readiness交付。
- W02／W04已記錄阻塞不重查；不使用其受限分支、不改產品年齡規則，W09完整B矩陣仍保留原門檻。

## 查證與驗證
- 讀AGENTS、STATUS、PLAN、本規格；局部查相關ERB／reference並附檔案@函式:行號；沿用既有查證，不重抄整包。
- 遊戲邏輯修正先原文expected的table-driven紅綠；純補既有行為驗收可直接綠，不製造假紅。子代理只跑定向測試。
- 全新人工資料建立起四年齡欄25、原生未設定哨兵保留；完整catalog執行，可只遮蔽文字，不摘錄露骨敘事、不Null吞掉待驗分支。
- 先完成產品／測試及tmp/s84/browser_fixture.py，列必要最少代表路徑、可見前態與原文expected，凍結後主代理真瀏覽器／一次全pytest。
- W06全部DoD完成才觸發結包500；理由為整包模式生命週期驗收，不因小修改觸發。若仍有實質缺口則不提早跑結包500、不假稱W06完成。
- 如需500，兩入口各seed0–249、max-shop200、actions101–108、前景50局一批，沿用25歲fixture與S82完整基線tmp/s82/adult25-v1；不得與全pytest並行。
- 已通過且產品未改的入口／瀏覽器證據可沿用，明示來源與範圍；新增缺口只補受影響分支，避免重複成本。

## 收尾
- 更新模式生命週期wiki／必要PLAYABILITY、bridge；清理succession wiki的天使樹及CSV重載舊未移植描述，不擴成無關文件整修。
- 明列W06 DoD各項證據與剩餘缺口；主代理確認後才可在STATUS／PLAN改完成，下一包按既有固定佇列W07。
- 繁體中文、LF／UTF-8無BOM、source／reference唯讀；子代理自查git範圍、不commit/push；STATUS／PLAN由主代理收口。
- 最後三段報告成果／查證依據／UNVERIFIED與DEVIATION，附測試摘要、實際路徑及必要操作。

## 子代理成果與驗證
- 無產品改動；新增32案完整catalog模式生命週期測試及獨立2案ENDLESS全滅八體進評分，詳[模式生命週期](../wiki/era/mode-lifecycle.md)。
- 原32案加既有相關定向：`523 passed, 1 warning in 32.88s`；後補獨立2案：`2 passed in 0.99s`。主代理全pytest與後補定向分開記錄，不重跑已通過全套。
- `tmp/s84/browser_fixture.py`六路原生新局／明示人工前態已備；一般新局輸入→SHOP→施前態→開始行動HTTP通過，不能代替主代理真瀏覽器。
- NORMAL／SOLO／HARDCORE／INSTANT有限通關及六種可選新周都有定向連續存讀；SURVIVAL按7／8體分流，FREEPLAY／SANDBOX期限持續；周回HARDCORE K勝利才增援天使樹。
- FREEPLAY的「引継ぎ無し」只有常數定義，原全滅>=8仍進評分；保留原控制流。ENDING_6維持無入口。沒有新增UNVERIFIED／DEVIATION。
- 主代理瀏覽器／完整pytest與結包500、W06狀態由主代理收口；既有W02／W04阻塞及W09完整B矩陣不變。

- 主代理六路真瀏覽器通過：NORMAL新局至結局存槽5、新session讀回引繼SHOP；SURVIVAL7／8期限分流；FREEPLAY／SANDBOX持續；HARDCORE增援回SHOP。完整catalog失敗0、console0、年齡25／原生未設定哨兵保留。
- 主全pytest `5396 passed, 1 warning in 384.36s (0:06:24)`；後補獨立2案 `2 passed in 0.90s`，沒有重跑整套。W06結包500十批通過：default247上限／3回標題、tokusou250上限，catalog／fixture0，所有輸出欄位逐seed同S82；證據tmp/s84/adult25-v1/audit.json。
