# 成就取得、保存與查看（S57–S59／W01）

## 已接通

- `ERB/インターミッション画面/SHOP_TROPHY.ERB@UNLOCK_ACHIEVEMENT:6–20`：禁止成就的模式直接返回；GLOBAL:num非0不重複取得；首次輸出通知→PRINTW等待→寫1→SAVEGLOBAL。
- `@SHOW_TROPHY:23–353`：紀錄2頁／成就4頁；100、200循環換頁；1000切換模式並回第1頁；999返回SHOP。未達成隱藏名稱、顯示提示；已達成顯示名稱／條件／周回加分。
- `@PRINT_ACHIEVEMENT:355–392`的文字／編號／加分由`tools/extract_achievements.py`抽取，欄寬使用既有Emuera百分比字串格式函式。
- `@GET_STATE_TROPHY:398–441`、`@GET_STATE_ABLUP:443–502`、`@GET_STATE_EXPUP:506–534`已接既有角色重算、訓練、能力提升、經驗取得呼叫者。原作尚未接通的W05支線不因此宣稱完成。
- Python共用入口在`game.achievements`；既有`battle.core.unlock_achievement`與catalog pyfunc共同呼叫。SHOP[800]直接使用同一GlobalStore；EVENTSHOP亦傳入session的GlobalStore。

## 全部直接呼叫分類

精確搜尋`^\s*CALL UNLOCK_ACHIEVEMENT\(`，共60處、11檔；不是成就種類數。

| 原作路徑@函式 | 呼叫數 | Python實際呼叫者 |
|---|---:|---|
| `ERB/インターミッション画面/SHOP_TROPHY.ERB@GET_STATE_TROPHY／GET_STATE_ABLUP／GET_STATE_EXPUP` | 34 | `achievements`三組判定 |
| `ERB/インターミッション画面/SHOP_CLOTH.ERB@SHOW_CLOTH` | 2 | `clothing_inventory` |
| `ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK` | 12 | `battle.source_check` 12處全部已接共用入口；S58補救援271／273與全末王259／260／261／265 |
| `ERB/ゲーム内_戦闘処理/BATTLE_TRAIN.ERB@EVENTTRAIN` | 1 | `battle.train` |
| `ERB/ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND` | 1 | `battle.after` |
| `ERB/ゲーム内_戦闘処理/TENTACLE_SYASEI.ERB@TENTACLE_SAKUSEI` | 1 | `battle.syasei` |
| `ERB/ゲーム内_戦闘処理/戦闘コマンド(ヒロイン)/COM_ATTACK_COMMON.ERB@COM_ATTACK_COMMON` | 2 | `battle.commands` |
| `ERB/ゲーム内_行動実行処理/特別活動/SEISAN_4_PORN_VIDEO.ERB@SEISAN_PORN_VIDEO` | 1 | `seisan` |
| `ERB/ゲーム内_イベント発生/エンディング/SCORE.ERB@SCORE` | 3 | `ending.score` |
| `ERB/地の文/MESSAGE_BATTLE.ERB@MESSAGE_BATTLE_CHARA_TRANSRELEASE／MESSAGE_BATTLE_CHARA_TRANSRELEASE_ECS` | 2 | catalog pyfunc／原生fallback |
| `ERB/地の文/MESSAGE_PRISON.ERB@MESSAGE_PRISON_PRISENTENCE_FIRST` | 1 | catalog hook／原生fallback |

## 引擎與等待邊界

- PRINTW等待使用`reference/emuera-1824/Emuera/GameData/Expression/ExpressionMediator.cs:50–65`；SAVEGLOBAL直接呼叫SaveGlobal，不寫RESULT（`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1279–1281`）。
- 函式無RETURN值時RESULT:0=0：`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`。
- `SHOW_TROPHY`的`#DIM MODE`預設為靜態（`reference/emuera-1824/Emuera/GameProc/UserDefinedVariable.cs:27`；`reference/emuera-1824/Emuera/GameData/Variable/VariableData.cs:451–473,1012–1013`）；返回後重入保留模式、頁數回1，新局／讀檔清除temp後回紀錄模式。
- INPUT回到畫面時提交未換行PRINT：`reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:685–695`。
- 全域陣列零初始化：`reference/emuera-1824/Emuera/GameData/Variable/VariableData.cs:85–95`；保存GLOBAL／GLOBALS：同檔:904–908。
- `wait_bridge`沿用catalog雙queue握手。一般generator輸入時worker已回收；同步成就等待期間才保留worker。返回標題會close舊generator並join巢狀catalog worker，不把確認前成就寫入舊／新session。
- catalog首次取得標記不可回滾；保存後遇不可執行內容會停止，不能假裝整段未執行或重放取得。禁用／重複取得不新增持久化副作用。
- Web按鍵語意仍有W07差異：成就等待傳回`None`，`game/session.py:366`將其視為number，`web/templates/index.html:32`使用required數字欄；玩家須輸入0等數字再提交，空白Enter／任意鍵不能確認，也尚無[0]提示。原引擎PRINTW呼叫ReadAnyKey；本次只驗證阻塞及確認後保存順序，未宣稱鍵操作一致。
- 直接呼叫原生函式的單元測試以同步呼叫代表立即確認；Web及標準模擬均由GameSession真等待通道驅動。

## 原作首次全域版本問題（S59已裁決修正）

這是`bridge/deviations.md`既有S24「GLOBAL:3未設定的覆寫」的成就影響，並非新推測：

1. `ERB/ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST:29–44`無global檔時只初始化MOB_FLAG，未設GLOBAL:3。
2. 第一次取得成就保存版本0；下次開局／讀檔的`ERB/バージョン間互換処理.ERB@UPDATE_GLOBAL:44–53`把111–170搬至211–270，可能將新成就覆寫成0。其餘既有設定／MOB遷移仍照S24原文。
3. 精確搜尋GLOBAL:3共10處，唯一寫入在同檔@UPDATE_GLOBAL:89。另兩個顯式UPDATE_GLOBAL入口為`ERB/ゲーム内_イベント発生/オープニング処理.ERB@MODE_SELECT:393–402`的[200]與`ERB/SYSTEM/コンフィグ/CONFIG_SYSTEM.ERB@CONFIG:451–462`的[2]；一般預設新局不經過。
4. CSV沒有GLOBAL初值檔；引擎以上述零陣列初始化。既有檔案的獨立測試仍保留版本0會清220、版本408保留220兩種預期。
5. 建議修法是**僅確定沒有全域檔的首次建立**時初始化GLOBAL:3為現行版本；既有全域檔仍執行原作遷移。S59使用者於2026-10-05「好，依建議」批准並已實作；`GlobalStore.__init__`只在檔案不存在時從`GameIdentity.version`設定3，未保存前不建立檔案；既有損毀／版本不符的讀取失敗不視為全新。

### 與版本遷移獨立的全域設定載入

只初始化GLOBAL:3能避免舊版本搬移成就，**不會**把當前FLAG／MOB_FLAG自動複製到GLOBAL／MOB_GLOBAL；不能據此宣稱所有設定保真。

- `ERB/インターミッション画面/SHOP_TROPHY.ERB@UNLOCK_ACHIEVEMENT`只寫成就格再SAVEGLOBAL；`ERB/SYSTEM/コンフィグ/CONFIG_初期設定.ERB@CONFIG_INIT`基本套組只設FLAG:800–805，不更新GLOBAL:11–15。首次無檔時EVENTFIRST只把MOB_FLAG設100，MOB_GLOBAL仍是零初值。
- `ERB/バージョン間互換処理.ERB@UPDATE:104–125`即使版本已408，仍在FLAG:800 bit0開啟時以GLOBAL:11–15覆蓋FLAG:801–805；**無條件**把GLOBAL:4套到FLAG:850，並把存在雜魚的MOB_GLOBAL套到MOB_FLAG。原預設基本套組bit0關閉，因此不能說基本套組801–805必被覆寫；但MOB篩選仍會從首次的100變成全域零值。
- 原作明確寫回全域設定的入口另在`ERB/SYSTEM/コンフィグ/CONFIG_SYSTEM.ERB@CONFIG:431–448`、`ERB/SYSTEM/コンフィグ/CONFIG_GLOBAL_MANIAC.ERB@CONFIG_F:200`、`ERB/SYSTEM/コンフィグ/CONFIG_GLOBAL_MOB.ERB@CONFIG_M:194`；單次成就保存不經這些入口。
- 這是「首次SAVEGLOBAL使檔案開始存在後，UPDATE讀取全域零值」的獨立原作行為；與版本0遷移重設／搬移是兩件事。S59僅初始化版本，不擴大已裁決方案，也未改動這些載入規則。

## 驗收證據與下個成果

- 主代理全pytest：`3788 passed, 1 warning in 404.00s (0:06:43)`；其中95個成就測試涵蓋所有原文簡單門檻前後值、禁用／重複／未達成、其他GLOBAL資料、取消與catalog副作用。
- 真瀏覽器：`python -m eragvt --port 8057 --save-dir tmp/s57/browser`；背景IAB操作新局→SHOP[800]→未達成頁→前頁1→4→999返回，返回按鈕／灰字／欄位已目視。
- 定向前態：GLOBAL:3=408、角色近距離戰技Lv9（非自然練到Lv9）；讀檔→全員休息→原作確認[9]→成就通知。確認前磁碟231=0；手輸0後231=1；列表第17項顯示名稱、Lv9條件與+20。
- 實際停止程序PID55764、啟動新程序PID57988後，瀏覽器重新讀回並進SHOP[800]，第17項仍保留；未將既有版本前態說成乾淨環境首次持久化成功。畫面證據在本次瀏覽器工具截圖；定向檔保留於gitignored的`tmp/s57/browser/`。
- 首輪標準模擬發現驗收工具兩個問題：成就等待會從40行舊按鈕抽策略RNG；同批seed共用全域目錄，新增SAVEGLOBAL讓後續seed不再是乾淨新局。`tools/sim.py`已改為握手標記辨識純確認並固定輸入0、每seed獨立目錄；2個工具測試覆蓋RNG不變與單獨／正逆序批次隔離。
- 差異定位：default seed0首次新增等待在輸入步74／SHOP15，舊按鈕為`[0,1,9,10,0,1,2,6]`、通知「女性の宿命」。僅移除確認抽樣後，seed0完整摘要與S55一致；seed1仍受共享全域檔影響，改為乾淨目錄後完整摘要亦與S55一致（含敗北／gameover時間及所有events）。診斷產物`tmp/s57/neutral-default*.jsonl`與log。
- 修正後正式500局：default250局中246到上限／4回標題，tokusou250局全到上限，catalog失敗0；兩開局各seed0–249、max-shop200、actions101–108，以50局前景批次執行。逐seed完整摘要（含events）與S55一致；正式產物`tmp/s57/final/`，`audit.json`核對每批退出碼、50筆／seed全集、log與JSONL一致及基線比較。

## S58 紀錄與解鎖消費端

- `ERB/インターミッション画面/SHOP_TURNEND.ERB@RECALC_PARTYMEMBER:251–255`先更新紀錄，再判成就；`@UPDATE_STATUS_RECORD:263–348`共20個欄位，嚴格大於才替換數值／姓名／等級，每次呼叫均SAVEGLOBAL。沒有禁用模式條件。Python已接回角色重算。
- `ERB/ゲーム内_イベント発生/エンディング/SCORE.ERB@SCORE:694–750`確認後保存最高總評，再處理成就；最後確認後依完整模式值加SOLO／NORMAL／HARDCORE次數並SAVEGLOBAL，再加FLAG:854。其他模式不加次數，但仍保存。兩處保存前等待沿用S57握手。
- `ERB/ゲーム内_イベント発生/エンディング/ENDING.ERB@ENDING_1:263–293／ENDING_3:459–489／ENDING_6:707–739`共用ENDLESS紀錄：先LOADGLOBAL，嚴格破紀錄才通知、等待並保存114。LOADGLOBAL寫RESULT成敗依`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1293–1299`；SAVEGLOBAL不寫RESULT同檔:1279–1281。
- `ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:209–241／283–304`補六處觸發；救援成就在角色狀態變更前取得，全殲滅依序260、261、259、265。259看單人最大修練P而非合計；265看非MASTER角色CFLAG:231>0至少3名，原文未另檢查SOLO（說明文字與條件不同，照條件）。
- 全ERB精確GLOBAL存取308行；解鎖消費端：`ERB/ゲーム内_イベント発生/エンディング/SUCCESSION.ERB@SUCCESSION:31–268／353／606／1452`的周回點數、213等級繼承、人數限制已有實作，直接讀同一GlobalStore，未發現永遠未解鎖占位。`ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB@CHARA_MAKE_MAIN:131／323`人數權限已有條件，但編輯本體未移植；:151–191初始狀態切換及`ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING`身體解鎖介面屬W02。`ERB/SYSTEM/キャラメイキング関連/EXPORT_CSV.ERB`262輸出屬既有除錯／匯出盤點W08。
- W01驗收資料及已有消費端；W02完成未移植互動端與B02解鎖選擇複驗，不能把目前顯示權限當整套編輯可玩。這是消除W01依賴尚未開始W02的循環驗收，不是略過UI成果。

### 最高總評與魅了經驗共用110（S59已裁決修正）

- 直接GLOBAL:110共13處：UPDATE_STATUS_RECORD:293–295三處；SHOP_TROPHY@SHOW_TROPHY:42–52六處；UPDATE_GLOBAL:52–53兩處；SCORE:695–696兩處。
- `ERB/バージョン間互換処理.ERB@UPDATE_GLOBAL:44–53`註明「歴代最高ランクの移動」並110→113，但現行SCORE／SHOW_TROPHY仍用110。魅了經驗>6後最高總評顯示「なし」，1–6則誤顯示評級；總評也可能壓住較小魅了經驗。S58曾保留此碰撞；S59按裁決將SCORE及SHOW_TROPHY最高總評改用113，魅了經驗維持110。
- 113只有上述遷移直接寫入；動態索引完整分類為成就num（呼叫211–280）、變身設定51–59、舊版111–170搬至211–270，不另讀寫現行110／113。沒有GLOBAL全陣列清空指令。
- 建議最小修法：SCORE寫與SHOW_TROPHY讀改113，魅了留110，保留原作已有113遷移。既有受污染110無法可靠分辨總評／魅了，不能猜回填。S59使用者已批准並實作；現行檔113保留，舊版仍按原作遷移，不猜測拆分110。

### S58 驗收

- 主代理獨立全pytest：`3832 passed, 1 warning in 431.06s (0:07:11)`。紀錄新增44案；連同成就與引繼定向：`175 passed, 1 warning in 8.95s`。涵蓋20欄、相等不替換、全模式計數、禁用成就既有測試、GLOBAL其他資料／RESULT其他格／RNG保留與保存前等待。
- 真瀏覽器：`python -m eragvt --port 8058 --save-dir tmp/s58/browser`。人工前態GLOBAL:3=408、角色姓名S58記錄測試／V經驗88；讀槽0→休息回合→SHOP[800]兩頁，紀錄姓名、Lv1與88回正確。停PID58912後新程序PID58672，重新讀槽0（尚未再次行動）→SHOP[800]第二頁仍88回；檔案GLOBAL:120=88／GLOBALS:20吻合。不是自然累積經驗或乾淨版本0存檔驗證。
- 另人工全殲滅槽1→休息→結算B。第一次等待前磁碟110=0、101=0；確認後110=4、101=0；第二次確認後101=1，再拒絕結局存檔進周回選單，顯示NORMAL+5、B+3、合計8點，213未取得時等級繼承仍顯示？？？。B06完整自然通關仍屬W06/W09。
- default seed0–1診斷JSONL與S57完整相同；診斷最後摘要輸出因cp950退出1，不是遊戲錯。正式500另由父以UTF-8獨立前景批次驗收，不拿這2局替代。
- S58主代理正式500：default246到上限／4回標題、tokusou250全到上限；catalog失敗0，逐seed全部欄位與S57一致。10批退出0，50筆／批及完整seed全集、日誌／JSONL一致檢查通過；產物`tmp/s58/final/`與`audit.json`。

## S59 裁決驗收與W01交接

- TDD先紅：13 failed／38 passed；修正後定向`201 passed, 1 warning in 11.26s`（全域建立、紀錄、成就與設定）。缺檔／損毀／舊版／現行版分別驗證；全新首次保存成就後另建session仍保留；總評高／相等／低與魅了77獨立、SHOW_TROPHY使用113；既有舊版遷移測試仍保留。
- 引擎重查：零陣列初始化為`reference/emuera-1824/Emuera/GameData/Variable/VariableData.cs:85–95`；缺檔、識別／版本不符及例外均返回false為`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:2256–2310`，因此S59不能用load=False判斷新檔。
- 初始版本取CSV載入的`GameIdentity.version`，不是新增408常數；真正session建立、純記憶體具identity的GlobalStore共用同一入口。未提供identity的底層測試空store仍為版本0。
- 真瀏覽器由主代理執行：服務`python -m eragvt --port 8059 --save-dir tmp/s59/browser`。啟動時無global.json；人工槽0為魅了77／近距離Lv9，槽1為全殲滅前態／魅了77，並未預寫GLOBAL版本或成就。這些前態不是自然練等或完整通關。
- S59主代理獨立全pytest：`3839 passed, 1 warning in 401.59s (0:06:41)`。正式500：default246上限／4回標題，tokusou250上限，catalog失敗0，逐seed完整結果與S58一致；10批退出0，seed全集及日誌/JSONL核對通過，產物tmp/s59/final。真瀏覽器證據如下；W01本包驗收通過。W01功能覆蓋：全部直接成就呼叫、20欄角色紀錄、模式通關數／最高總評／ENDLESS紀錄、SHOP六頁、保存與重啟、既有引繼解鎖消費端。新角色編輯／初始狀態／SIZE_SETTING解鎖互動端仍由W02驗B02；未移植戰鬥支線本體由W05接通。
- 下一完整成果建議為W02共用個別角色編輯入口：以`ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN`為中心，接回開局與既有招募／醫療／子供／引繼的共用呼叫者，保留確認／返回／重入，整合已移植命名、一人稱、武器選單；具體分支與成果範圍由下階段原文查證定稿。TS／特殊裝備後續生命週期仍W03。

### S59 主代理真瀏覽器驗收
- `python -m eragvt --port 8059 --save-dir tmp/s59/browser`，啟動時沒有global.json，未手動灌版本408；先從標題建立預設新局到SHOP，再讀人工槽0（魅了77／近距離Lv9）以休息觸發紀錄與成就。
- 成就確認前檔案已有版本3=408、魅了110=77，231尚未寫入；數字0確認後231=1。停止原程序64188，新程序41280重啟同目錄；讀槽0後SHOP[800]顯示グランドマスター／Lv9／+20，紀錄顯示魅了77、總評なし。
- 讀人工全殲滅槽1，休息進結算B；確認前101=0／110=77／113=0，第一次確認後113=4且110=77，第二次確認後101=1。進引繼為NORMAL5+B3+成就1=9點；返回標題重讀槽0，SHOP[800]同時顯示B總評與魅了77。
- 上述成就／結算角色為人工前態，沒有宣稱自然完整通關。父已核對AX與畫面，測試程序及分頁已關閉，前態保留於tmp/s59/browser。
