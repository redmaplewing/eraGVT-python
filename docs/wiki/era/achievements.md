# 成就取得、保存與查看（S57／W01）

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
| `ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK` | 12 | `battle.source_check` 既有6處已接共用入口；救援271／273與全boss259／260／261／265原先整段省略，仍待W01 |
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

## 原作首次全域版本問題（待裁決）

這是`bridge/deviations.md`既有S24「GLOBAL:3未設定的覆寫」的成就影響，並非新推測：

1. `ERB/ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST:29–44`無global檔時只初始化MOB_FLAG，未設GLOBAL:3。
2. 第一次取得成就保存版本0；下次開局／讀檔的`ERB/バージョン間互換処理.ERB@UPDATE_GLOBAL:44–53`把111–170搬至211–270，可能將新成就覆寫成0。其餘既有設定／MOB遷移仍照S24原文。
3. 精確搜尋GLOBAL:3共10處，唯一寫入在同檔@UPDATE_GLOBAL:89。另兩個顯式UPDATE_GLOBAL入口為`ERB/ゲーム内_イベント発生/オープニング処理.ERB@MODE_SELECT:393–402`的[200]與`ERB/SYSTEM/コンフィグ/CONFIG_SYSTEM.ERB@CONFIG:451–462`的[2]；一般預設新局不經過。
4. CSV沒有GLOBAL初值檔；引擎以上述零陣列初始化。獨立測試保留版本0會清220、版本408保留220兩種預期。
5. 建議修法是**僅確定沒有全域檔的首次建立**時初始化GLOBAL:3為現行版本；既有全域檔仍執行原作遷移。此修法尚未獲本次使用者裁決，S57未擅改。

### 與版本遷移獨立的全域設定載入

只初始化GLOBAL:3能避免舊版本搬移成就，**不會**把當前FLAG／MOB_FLAG自動複製到GLOBAL／MOB_GLOBAL；不能據此宣稱所有設定保真。

- `ERB/インターミッション画面/SHOP_TROPHY.ERB@UNLOCK_ACHIEVEMENT`只寫成就格再SAVEGLOBAL；`ERB/SYSTEM/コンフィグ/CONFIG_初期設定.ERB@CONFIG_INIT`基本套組只設FLAG:800–805，不更新GLOBAL:11–15。首次無檔時EVENTFIRST只把MOB_FLAG設100，MOB_GLOBAL仍是零初值。
- `ERB/バージョン間互換処理.ERB@UPDATE:104–125`即使版本已408，仍在FLAG:800 bit0開啟時以GLOBAL:11–15覆蓋FLAG:801–805；**無條件**把GLOBAL:4套到FLAG:850，並把存在雜魚的MOB_GLOBAL套到MOB_FLAG。原預設基本套組bit0關閉，因此不能說基本套組801–805必被覆寫；但MOB篩選仍會從首次的100變成全域零值。
- 原作明確寫回全域設定的入口另在`ERB/SYSTEM/コンフィグ/CONFIG_SYSTEM.ERB@CONFIG:431–448`、`ERB/SYSTEM/コンフィグ/CONFIG_GLOBAL_MANIAC.ERB@CONFIG_F:200`、`ERB/SYSTEM/コンフィグ/CONFIG_GLOBAL_MOB.ERB@CONFIG_M:194`；單次成就保存不經這些入口。
- 這是「首次SAVEGLOBAL使檔案開始存在後，UPDATE讀取全域零值」的獨立原作行為；與版本0遷移重設／搬移是兩件事。本次僅揭示範圍，不擴大待裁決方案，也未修改產品。

## 驗收證據與下個成果

- 主代理全pytest：`3788 passed, 1 warning in 404.00s (0:06:43)`；其中95個成就測試涵蓋所有原文簡單門檻前後值、禁用／重複／未達成、其他GLOBAL資料、取消與catalog副作用。
- 真瀏覽器：`python -m eragvt --port 8057 --save-dir tmp/s57/browser`；背景IAB操作新局→SHOP[800]→未達成頁→前頁1→4→999返回，返回按鈕／灰字／欄位已目視。
- 定向前態：GLOBAL:3=408、角色近距離戰技Lv9（非自然練到Lv9）；讀檔→全員休息→原作確認[9]→成就通知。確認前磁碟231=0；手輸0後231=1；列表第17項顯示名稱、Lv9條件與+20。
- 實際停止程序PID55764、啟動新程序PID57988後，瀏覽器重新讀回並進SHOP[800]，第17項仍保留；未將既有版本前態說成乾淨環境首次持久化成功。畫面證據在本次瀏覽器工具截圖；定向檔保留於gitignored的`tmp/s57/browser/`。
- 首輪標準模擬發現驗收工具兩個問題：成就等待會從40行舊按鈕抽策略RNG；同批seed共用全域目錄，新增SAVEGLOBAL讓後續seed不再是乾淨新局。`tools/sim.py`已改為握手標記辨識純確認並固定輸入0、每seed獨立目錄；2個工具測試覆蓋RNG不變與單獨／正逆序批次隔離。
- 差異定位：default seed0首次新增等待在輸入步74／SHOP15，舊按鈕為`[0,1,9,10,0,1,2,6]`、通知「女性の宿命」。僅移除確認抽樣後，seed0完整摘要與S55一致；seed1仍受共享全域檔影響，改為乾淨目錄後完整摘要亦與S55一致（含敗北／gameover時間及所有events）。診斷產物`tmp/s57/neutral-default*.jsonl`與log。
- 修正後正式500局：default250局中246到上限／4回標題，tokusou250局全到上限，catalog失敗0；兩開局各seed0–249、max-shop200、actions101–108，以50局前景批次執行。逐seed完整摘要（含events）與S55一致；正式產物`tmp/s57/final/`，`audit.json`核對每批退出碼、50筆／seed全集、log與JSONL一致及基線比較。
- W01下一完整成果：`ERB/インターミッション画面/SHOP_TURNEND.ERB@UPDATE_STATUS_RECORD`的歷代紀錄寫入、`ERB/ゲーム内_イベント発生/エンディング/SCORE.ERB@SCORE`最高總評／模式通關數，以及`ERB/ゲーム内_イベント発生/エンディング/ENDING.ERB`各結局ENDLESS最高紀錄；補齊`ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK`原先省略的救援271／273與全boss259／260／261／265六處，再核對角色製作／引繼解鎖消費端。W01未結案，不換W02。
