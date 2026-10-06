# 戰鬥終端與正常入口驗收（S82）

本頁承接[側事件](battle-side-events.md)與[分派／回復](battle-dispatch.md)，只補W05缺少的連續流程證據。原作路徑相對`source/earGVP/`。未修改產品；不把人工前態稱為新局自然通關。

## 驗收邊界與資料

- `tests/_battle_lifecycle.py`組裝三位人工角色；四年齡欄25，保留`adult_data`原生未設定哨兵規則。角色從建立起即用人工資料，沒有事後改齡。
- 全部使用真`CatalogNarrationService`，只由`NumericOutput`遮蔽顯示文字、保留數字按鈕；不替換COM、SOURCE_CHECK、敵方行動、結算或catalog副作用。已取得成就的人工GLOBAL避免無關重複提示；臨時目錄隔離存檔。
- 正常行動入口使用`ACTION_MAIN`原判定與`GameRng(seed)`；可達條件為人工前態，敵號由原生RNG抽出。沒有patch遭遇函式，也沒有抽中後重設亂數。
- 末王為人工已遭遇前態：最大HP10000，勝利目前HP1；天使樹從形態4收尾，前面三次形態沿用`test_angel_tree.py`，不聲稱從第一形態打完。人工攻擊／敏捷10000；體／氣／耐原1000，敗北第一輸入前設0，超時第一輸入前設到上限。這些是測試前態，非產品規則。
- 主代理真瀏覽器、全pytest、W05結包500結果以[STATUS](../../STATUS.md)及S82規格收口為準；本頁不自行宣告整列B04／B05／B09或W09完成。

## 兩末王八種終端

原生`run_train`包含BEGIN TRAIN初始化、原指令、SOURCE_CHECK、適用時EVENTEND；非勝利再執行原生EVENTTURNEND／其餘角色ACTION_MAIN，最後由`GameSession.begin_shop`回SHOP與自動存檔。

| 路徑 | seed／輸入（fixture0之後） | 原作expected與已驗狀態 |
|---|---|---|
| Ｋ触手勝利 | 1／1 | HP≤0、TFLAG98=1、FLAG101=0、FLAG64=-1、FLAG700仍1、回傳TURNEND |
| 天使樹最終形態勝利 | 1／1 | 同上，FLAG21由4→0後進末王共通勝利 |
| 兩末王敗北 | 各1／4 | TFLAG98=2、FLAG700=0、角色幽閉CFLAG0=1／20=1／21=末王號；經隊伍排序仍保留身分、回SHOP及save99 |
| Ｋ触手撤退 | 82／999、999 | 第一次原判定失敗仍在戰鬥、第二次成功；TFLAG98=0、FLAG700=0、回SHOP |
| 天使樹撤退 | 0／999 | 原判定成功，TFLAG98=0、FLAG700=0、回SHOP |
| 兩末王時間切れ | 各1／4 | 人工TFLAG0=50、原上限50；原SOURCE_CHECK結束、TFLAG98=0、FLAG700=0、回SHOP |

原文：

- `ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:40–112,117–193,279–306`。完全殲滅直接`BEGIN TURNEND`，跳過EVENTEND；本次以此W06結局交接為W05終端，沒有強迫回SHOP。既有末王結局／SCORE／save／引繼測試仍在`test_lastboss.py`、`test_angel_tree.py`。
- 同檔`@SOURCE_CHECK:973,1031–1043,1091–1095`敗北幽閉；`:1104–1130`時間切れ。`ERB/ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND:7,432–439`清戰鬥旗標並保存未擊敗末王的累積傷害／解析。
- `ERB/ゲーム内_戦闘処理/BATTLE_COM.ERB@USERCOM:573–625`先檢查距離、撤退不可、氣絶及CHECK_CAN_RETREAT_F，再抽撤退判定。沒有按敵為末王而禁止；本次末王前態情境空白且距離3。
- `ERB/インターミッション画面/SHOP_TURNEND.ERB@EVENTTURNEND:15–19,52–136`續跑其他角色、重算、正常回SHOP；敗北角色可能被SET_PARTYMEMBER移位，測試以CFLAG240身分追蹤，不能仍假設索引1。
- 引擎`reference/emuera-1824/Emuera/GameProc/Process.SystemProc.cs:524–534`的BEGIN AFTERTRAIN呼叫EVENTEND；BEGIN TRAIN清TFLAG等沿既有`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1422–1462`證據。

## 四類正常行動遭遇抽樣

| 入口 | 人工可達條件／固定seed | 原生實抽結果 |
|---|---|---|
| 出擊→普通敵 | 探索28／配額28、七普通敵生存、seed2 | FLAG10=0／11=1、BOSS，進TRAIN上限50 |
| 出擊→雜魚 | 探索0未滿、雜魚戰ON、16類候選各權重1、seed0 | FLAG10=2／11=803、MOB，進TRAIN上限15 |
| 情報收集→事件捜査 | 市民妨害ON、防衛0、seed0；選1不變身、選1調查 | FLAG10=2／11=1150、CITIZEN、事件6002，進TRAIN上限15 |
| 出擊→悪堕ち | 另有一位人工CFLAG0=3候選、防衛0、seed1 | FLAG110=1／111=2，BOSS，進TRAIN上限50 |

以上只補「正常入口到實際遭遇後TRAIN選單」證據，不稱這四戰已完整通關。原文：`ERB/ゲーム内_行動実行処理/ACTION.ERB@ACTION_MAIN:75–96,145–155`；`ERB/ゲーム内_戦闘処理/ENCOUNT.ERB@ENCOUNT_ENEMY:74–129`、`@ENCOUNT_BOSS:262–297`、`@MOB_TENTACLE_BATTLE:533–600`；`ERB/ゲーム内_行動実行処理/ACTION_GATHER_INFORMATION.ERB@MESSAGE_GATHER_INFORMATION:344–416`。

## 救援事件4完整進出

三人休憩、DAY3白天、防衛0，從原生`RAID_HANTEI`實抽救援→角色→事件號。seed2抽角色1／事件4／普通敵6；敗北用seed32抽角色1／事件4／普通敵2，避開普通敵6的首次敗北取消分支。沒有直接設FLAG45或敵號。seed2拒絕路只走到事件4選擇，不抽戰鬥敵。

| 選擇與終端 | fixture0之後輸入 | 原生結果 |
|---|---|---|
| 接受並勝利 | 0、1 | 人工全部普通敵累積傷害100%，遭遇讀取後HP1；勝利TFLAG98=1、新聞110004、任務報酬5000加一般戰鬥報酬 |
| 接受並超時 | 0、999、4 | 人工第一戰鬥輸入TFLAG0=40，原上限40；999拒絕且回合不變，4觸發超時；TFLAG98=0、新聞100004、任務無報酬 |
| 接受並敗北 | 0、4 | 人工第一戰鬥輸入體／氣／耐0；TFLAG98=2、新聞120004、角色幽閉於敵2 |
| 拒絕 | 1 | 已抽到事件4才拒絕，FLAG45=0；無戰鬥、無任務報酬／新聞，回SHOP |

三場實戰均繼續完成任務SUCCESS／FAILURE、EVENTTURNEND清FLAG45、SHOP及自動99存檔。save99保留顯示前新聞號，SHOP顯示後FLAG60清0；不是只走到下一次輸入就稱事件結束。敗北回SHOP時角色依隊伍排序移至尾端，仍有同一幽閉狀態。

- `ERB/ゲーム内_イベント発生/強制発生イベント/FORCE_襲撃or救援イベント発生.ERB@RAID_HANTEI:95–105`；`ERB/ゲーム内_イベント発生/イベントから派生する特殊戦闘/●イベント戦闘_救援共通.ERB@RAID_RESCUE:42–50,149–216`。
- `ERB/ゲーム内_イベント発生/イベントから派生する特殊戦闘/4 攫われた女性.ERB@EVENT_BATTLE_EXEC_4:44–45`為上限40／撤退不可；`@EVENT_BATTLE_MISSION_CHECKER_4:73–80`只有勝利成功；`@EVENT_BATTLE_SUCCESS_4:66–71`、`@EVENT_BATTLE_FAILURE_4:98–99`寫新聞。
- `ERB/インターミッション画面/SHOP_TURNEND.ERB@EVENTTURNEND:56–61`清事件；`ERB/インターミッション画面/SHOP_FLASHNEWS.ERB@FLASHNEWS:69–88,204`顯示與清新聞。事件4檔頭未實裝標籤不能豁免此完整可達流程。

## W05完成條件對照與驗證

| W05要求 | 證據與範圍 |
|---|---|
| 觀眾妨礙、返り血、救出／發現 | S80七路25歲真瀏覽器、側事件定向；S77既有救出連續鏈；本次事件4完整成功／失敗／拒絕 |
| ISGIRLY／ISHOLE | S81八個條件單測、四條真候選caller與四路真瀏覽器 |
| 末王強化 | S81兩末王ON／OFF原7回復與可達性，未重做；本次補八種終端 |
| 所有原作可達敵類與指令分派 | S81原38COM、7普通／2末王／16雜魚／市民1150合法路由；本次四類ACTION_MAIN實抽 |
| 原作停用分支不新增 | 沿用PLAYABILITY與S81守衛歸屬，沒有新增產品分支 |
| 工作包驗收 | 子代理定向16案、主代理16路真瀏覽器通過；主代理全pytest5285及結包500通過，W05範圍完成；完整B矩陣仍留W09 |

子代理：`python -m pytest -q tests/test_battle_lifecycle.py --tb=short` → `16 passed in 0.79s`，catalog失敗0。本次只有測試／驗收工具／文件，沒有產品修正，因此不製造測試先紅紀錄、不重跑無關定向檔。`tmp/s82/browser_fixture.py`共用同一前態，`python tmp/s82/browser_fixture.py --port 8789`後開`/fixture`，所有分支／人工條件可見。

沒有新增UNVERIFIED／DEVIATION。既有W02／W04具體阻塞、W06模式終局、W07全面WAIT／顯示及W08安全網／原作錯誤仍保留。

主代理16路真瀏覽器均通過，證據`tmp/s82/browser-{mode}.json`／`browser-summary.json`；事件4超時另有手輸999拒絕的`browser-rescue-timeout-rejected.json`。兩末王勝利到結局交接、其他末王六路與救援四路到SHOP、四遭遇到TRAIN；四年齡欄25、catalog失敗0、console警告／錯誤0。瀏覽器頁籤與伺服器已關；產品未改不重做這些路徑。

主代理全pytest：`5285 passed, 1 warning in 166.44s (0:02:46)`。W05結包500：預設247上限／3回標題，初期セット250上限，catalog／fixture失敗0。停止原因逐seed同S79，與S80重疊350局完整相同；S79只有初期セット78／88／153／176少兩個已改原生的catalog候選輔助計數，其他輸出欄位相同。證據`tmp/s82/adult25-v1/audit.json`／`comparison-details.json`；新完整模擬基線為S82。
