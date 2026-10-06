# 模式剩餘規則（S83／W06）

S79七模式新局／引繼共用入口維持；S83接回六處停止。MODE_OPTIONS依`ERB/DIM.ERH:60–92`的常數定義：SURVIVAL／FREEPLAY／SANDBOX開ENDLESS，INSTANT開能力降低。規則讀選項位元，不另以模式名稱分派。

能力降低選項精確搜尋共12處；本次敵行動／PALAM／EVENTCOMEND外，開局期限、TENTACLE_LEVEL兩係數及RESEARCH_QUOTA已在原生函式。另`ERB/ゲーム内_戦闘処理/COMMON_TENTACLE_DATA.ERB@MOB_KILL_QUOTA:508–547`只由`ERB/バージョン間互換処理.ERB@UPDATE:446–454`的LASTLOAD_VERSION<360路徑呼叫（全作符號2處含定義），屬既有W08舊版存檔遷移停止，不是當前七模式漏翻的新呼叫者。

## ENDLESS擊破與期限

- `ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:142–165`：普通BOSS勝利仍重置該敵累積傷害；ENDLESS且敵號>0時總數FLAG3加1、保留生存bit，然後以RAND:生存數重抽FLAG18直到不同於FLAG11。非ENDLESS才清生存bit；返血、救出及原戰後呼叫位置不變。
- 重抽原樣包含0、不包含上界，不能改成RAND+1。`ERB/ゲーム内_戦闘処理/ENCOUNT.ERB@ENCOUNT_BOSS:188–219、258–268`在FLAG18=0時改走一般存活候選，因此可再次抽到剛擊破的同一敵；定向案例驗到敵1再出現。這是原文行為，沒有擅修註解所說的「避免連戰」。
- 生存bit精確賦值／SETBIT／CLEARBIT搜尋共5處：`ERB/ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST:73、100–103`、`ERB/ゲーム内_イベント発生/エンディング/SUCCESSION.ERB@SUCCESSION:1092–1095`、上述SOURCE_CHECK:159，以及`ERB/バージョン間互換処理.ERB@UPDATE:146–147`的舊版負值修0。正常新局／新周初始化7bit，ENDLESS勝利不減，連續生命週期保持7存活。不能把不相容人工位元狀態當正常模式前態；舊目標0亦不會通過FLAG11>0的重抽守衛。
- `ERB/ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND:311–333`：擊破數=FLAG3−生存數；扣期日修正DAY1的量為DAY/14＋擊破/10；日期90/135/180或擊破20/40/60各加1，最多FLAG2。
- 剩餘期限`(擊破+1)*FLAG2-DAY+DAY1`若<-1000只補100一次；若<-100只補10一次；-100至-1才反覆補1到0。只有最後分支含GOTO，沒有改成三分支都循環。
- 不新增ENDLESS通關或SANDBOX終局。既有ENDLESS最高紀錄、結局入口仍由`game/ending.py`與W01實作處理；本階段未修改其規則。

## 能力降低與INSTANT等待

- `ERB/ゲーム内_戦闘処理/ENEMY_ACTION.ERB@ENEMY_ACTION:520–540`：體液行動先鉗制當前體／氣損失，之後氣力基礎減LOCAL3/2。完全防禦只跳過當前資源扣除，仍依原LOCAL3減基礎。
- `ERB/ゲーム内_戦闘処理/PALAM_UP.ERB@PALAM_KIRYOKUDOWN:1545–1561`：顯示基礎減少量在GUTS前；實際扣BASE51在GUTS後。例如畫面50/25，保底後實扣49/24。
- `ERB/ゲーム内_戦闘処理/PALAM_UP.ERB@PALAM_SEITAISEIDOWN:1645–1668`：當前耐性扣LOCAL，BASE52再扣LOCAL/2。兩者皆不替基礎值加0下限，也不改MAXBASE。
- `ERB/ゲーム内_戦闘処理/BATTLE_COM.ERB@EVENTCOMEND:929–986`先累加經驗、衰減PALAM、處理觀眾及事件TURNEND，最後才依能力降低位元CALL。
- `ERB/ゲーム内_戦闘処理/INSTANT_ARG_DOWN.ERB@INSTANT_ARG_DOWN:1–32`：未變身5次、變身／SP2次；PRINTFORMW真正等待後才抽RAND5。0–3各減BASE10–13之一1，4減BASE50十，均可負值；不改MAXBASE。LOCAL1迴圈至0、LOCAL2保留末次抽值。
- 使用既有WaitInputRequest，Enter不寫RESULT(S)，函式落底只寫RESULT0=0，其餘格保留。引擎依據：`reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:497–508、707–734`、`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`。
- `event_comend`改generator，唯一產品呼叫者`do_train`已傳遞；`tools/sim.py`無包裝此兩函式，不需改計數工具或共用排程。

## 驗證範圍與後續

- 70案原文table-driven與9條完整catalog人工25歲呼叫鏈；加受影響戰鬥定向共`500 passed, 1 warning in 3.61s`。這是500個pytest案例，**不是500局模擬**。
- 原文紅燈階段覆蓋六缺口；修正測試衣裝／旁支前態後`54 failed, 13 passed`，產品接通後規則67案全綠，再追加三個邊界及9條整合。
- 瀏覽器前態：`tmp/s83/browser_fixture.py`；必要代表為survival-win、normal-win、instant-human、instant-sp、instant-hit、instant-palam。主代理六路已實際操作通過；四年齡欄25、catalog失敗0、console警告／錯誤0，證據tmp/s83/browser-summary.json／browser-instant-wait.png。
- ENDLESS真TRAIN勝利→EVENTEND→TURNEND→SHOP；INSTANT真TRAIN輸入→EVENTCOMEND→確認→再顯示選單；PALAM_UP直接入口驗兩項扣基礎。人工HP／攻擊／日期／下一敵行動明示，不宣稱自然完整通關。
- 主代理全pytest：`5364 passed, 1 warning in 178.06s (0:02:58)`。局部模式規則未改共用排程／RNG／存讀檔，依分級裁決不跑500；最近完整基線仍為S82，未冒充重驗。
- S84已補七模式日期／增援／招募／禁止條件、終局或持續規則，以及新局→結局存檔／新session讀回／引繼新周連續驗收；[原文對照及範圍](mode-lifecycle.md)。W06結包依主代理STATUS驗收，W09完整B矩陣仍保留。
- 無新增UNVERIFIED／DEVIATION，既有W02／W04阻塞與W07舊WAIT範圍不變。
