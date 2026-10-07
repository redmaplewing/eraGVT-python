# 共用 COUNT 與原生同步邊界

## 引擎依據

以下路徑前綴均為`reference/emuera-1824/Emuera/`。

| 行為 | 已查證來源 |
|---|---|
| COUNT是內建整數一維陣列，預設1000格；本作VariableSize.csv未改COUNT | `GameData/Variable/VariableCode.cs:45`、`GameData/ConstantData.cs:147–148` |
| COUNT=0x0B，小於存檔整數陣列上限0x3C；全部元素存讀 | `GameData/Variable/VariableCode.cs:94`、`GameData/Variable/VariableData.cs:663–688` |
| 新局ResetData清零；讀檔先初始化再讀保存值 | `GameData/Variable/VariableEvaluator.cs:1132–1139、2173–2176、2339–2342` |
| BEGIN TRAIN不清COUNT | `GameData/Variable/VariableEvaluator.cs:1422–1460` |
| REPEAT與FOR先寫開始值，再求上限及步進；零次也留下開始值 | `GameProc/Function/Instraction.Child.cs:1731–1744` |
| REND／NEXT及CONTINUE讀目前counter再加步進；BREAK也加一次；RETURN直接退出而不加 | `GameProc/Function/Instraction.Child.cs:1997–2023、2054–2161` |
| CALL只設參數與函式私有動態變數，不保存／還原COUNT；RETURNF亦不還原 | `GameProc/Process.State.cs:438–483、502–523`；COUNT實際直接讀寫全域陣列見`GameData/Variable/VariableEvaluator.cs:2466–2469` |

所以`REPEAT COUNT`先把COUNT清0，上限也是0；同一COUNT元素的巢狀迴圈會互相覆寫，不等同Python巢狀range。`FOR COUNT:1`則使用另一個元素。`FOR LOCAL`、`FOR CCOUNT`及純Python資料走訪不應寫COUNT。

## S88 已接通的完整邊界

`GameState.count`是唯一儲存處；catalog讀／寫／VARSET／REPEAT均共用，`temp.narr`不再持有COUNT。JSON升v4；沿既有新增陣列慣例，v1–3缺欄初始化為0，舊檔從未保存的COUNT無法還原。新局自然清零，BEGIN TRAIN保留，存讀完整保留所有COUNT索引。

catalog失敗可回復時連COUNT一起回復；原生hook後不可回復的失敗仍停止，不重放hook。既有重放式INPUT與worker式INPUT均保留原計數，正常完成不殘留交易或worker。這不裁決既有「catalog同步失敗回復」偏離。

原作路徑以下相對`source/earGVP/`；17個明示COUNT／REPEAT迴圈已接原生實際呼叫者：

| 原作來源 | 原生消費與終值 |
|---|---|
| `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:9–14、345–351` | 進入保存ITEM時FOR100至699；確認後REPEAT4清SAVESTR，再恢復ITEM，最後COUNT0=700；3處 |
| 同檔`@FIRSTSETTING_CHARA_NAME_RANDOM:827–957、1009–1012` | 生成與重繪兩個REPEAT20；輸入後姓名排列索引實讀共用COUNT，不再固定寫LOCAL30；2處 |
| 同檔`@FIRSTSETTING_CHARA_SELFCALL:1211–1253` | 建表COUNT0／COUNT1；顯示至空列9時BREAK→10，預設類型再跑樣式3次→3；COUNT1留3；4處 |
| 同檔`@FIRSTSETTING_CHARA_LOADCSV:1563–1565` | 清4格SAVESTR後，PRINTW等待前COUNT0=4；1處 |
| `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_SEIKAKU.ERB@RAND_CHOOSE_KOJO_SEIKAKU:462–476` | CALL色函式前設COUNT，CALL後以共享新值讀TALENT／建立候選並進NEXT；清性格第二個FOR終值19；2處 |
| `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_RANDOMNAMING.ERB@FIRSTSETTING_RANDOMNAMING_SELECT:314–400` | 冠名／變身名等共用單詞候選生成與顯示，各REPEAT20；2處。ALL的LOCAL走訪不改COUNT |
| `ERB/ゲーム内_イベント発生/オープニング処理.ERB@MODE_SELECT:306–351` | 新局與引繼共用選單FOR1至7，輸入時COUNT0=8；1處 |
| `ERB/ゲーム内_イベント発生/オープニング処理_カスタムGAMEMODE.ERB@GAME_MODE_CHECK:124–130`、`@GAME_MODE_CHECK_F:131–138` | 命中模式RETURN保留當前COUNT0；全未命中COUNT0=8。SAVEINFO、成就與周回呼叫讀到同一COUNT；2處 |

上述邊界不包含所有被角色編輯呼叫的顯示／衣裝內部迴圈；例如SHOW_STATUS_TALENT的COUNT仍屬下列狀態群組。不能把主入口收尾已同步解讀成整個角色編輯內部COUNT均已完整。

## S89 衣裝／武器與共用選取

衣裝63行與汎用／武器5行逐一歸到下表；62行接回原生，6行既由catalog承接並補驗。沒有把搜尋行當成獨立功能，也沒有新增衣裝或選取規則。

| 原作來源 | 實際邊界與COUNT |
|---|---|
| `ERB/武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB@CLOTH_CUSTOMIZE_OPTION_101:168–170`及同檔其餘43件、`CLOTHDATAアウター_特殊.ERB`兩件、`CLOTHDATAインナー.ERB`11件的同名入口（精確行見`clothing_text.MENUS`的source） | 共57個CUSTOM_NUM迴圈由`custom_clothing_gen`共用`_read_custom`執行；每輪CALL前後共用COUNT，終值為各衣裝4–8。個別DRAW、COMMON及PRINT子選單用LOCAL，不改COUNT；99返回保留。原作缺函式如118仍直接返回，不新增COUNT副作用 |
| `ERB/武器と衣装/衣装関連/CLOTH_衣装カスタマイズ共通処理.ERB@CLOTH_CUSTOMIZE_OPTION_COPY91:536–547` | 兩個變身狀態分支共用上述讀取，COUNT=CUSTOM_NUM；COPY92沒有REPEAT，仍直接貼上後重繪 |
| 同檔`@CLOTH_CUSTOMIZE_OPTION_SAVE:561–572` | `encode_custom(..., state=st)`執行共用COUNT；COUNT0為0時CONTINUE仍步進，REND後另加第0格。原低位與高位補正不變；純算式測試可不帶狀態 |
| 同檔`@CLOTH_CUSTOMIZE_OPTION_DRAW:159–181` | 既由catalog執行9次，隨後動態CALL具體DRAW；戰鬥衣裝資訊是實際呼叫者。不同於57件OPTION內直接CALL個別DRAW，不能誤把自訂畫面設為9 |
| `ERB/武器と衣装/衣装関連/CLOTH_WEAR.ERB@CLOTH_CUSTOMIZE_OUTER2:983–989` | 先已用槽REPEAT，再剩餘槽REPEAT；COUNT終值為`max(SLOTMAX-SLOTUSED,0)`。每個字形本體及後續補正CALL皆能看到當時值；零／負上限仍先清0。FOR LOCAL的部件檢索不改COUNT |
| `ERB/武器と衣装/武器カスタマイズ関連/GENERATE_ADD_STR.ERB@GENERATE_ADD_STR:159–169` | 原生字表複製逐組REPEAT100；空字串BREAK仍加1。末組54為空，COUNT=1後才抽RNG；`WEAPON_NAME.ERB@WEAPON_ADD_STRS`外層LOCAL不覆寫，實際生成／選取／返回與存讀皆保留1 |
| `ERB/汎用関数/CHOOSE_RAND_1.ERB@CHOOSE_ACTION_TOGETHER_F:22–41`、`@CHOOSE_RELAXATION_FACILITY:54–115` | 既有catalog執行；同排程選取包括SOLO／無候選早退都先清LOCAL，COUNT=CHARANUM。設施選取有／無候選皆先跑15次，COUNT=15；不新增第二份Python選取實作 |
| `ERB/汎用関数/GET_COLOR_NAME.ERB@GETCOLORNAMESTR:127–156` | 兩個FOR既由catalog承接。空值／格式錯誤原值不動；精確命中RETURNF保留對應20000系索引；近似搜尋跑完COUNT=21000 |

`FIGURE_SPLIT`實際使用LOCAL（`ERB/汎用関数/FIGURE_SPLIT.ERB@FIGURE_SPLIT:4–11`），不覆寫COUNT；測試另用探針確認若被呼叫者覆寫，賦值及NEXT仍讀共享新值。賦值右側先於左側索引寫入的新增查證：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:459–463`；其餘迴圈／CALL規則沿用S88證據。

## S90 其餘七群：既有原生邊界已同步

2026-10-07精確搜尋：`rg --pcre2 '(?<![A-Za-z_])COUNT(?![A-Za-z_])' source/earGVP/ERB --stats`為795 matches、570行、76檔；`^\s*(REPEAT\b|FOR\s+COUNT(?:\s|:|,))`為291迴圈行、90檔。扣S88的17及S89的68後206行分類如下；搜尋行不是獨立功能數。

| 群組 | 搜尋行 | S90原生同步 | catalog已承接 | 無呼叫者／不可達 | 未移植除錯入口 |
|---|---:|---:|---:|---:|---:|
| 攻擊數值 | 61 | 61 | 0 | 0 | 0 |
| ABL升級 | 16 | 16 | 0 | 0 | 0 |
| 狀態顯示 | 19 | 19 | 0 | 0 | 0 |
| 製作／除錯 | 22 | 17 | 0 | 2 | 3 |
| SHOP | 11 | 11 | 0 | 0 | 0 |
| 開局／結局／其他事件 | 41 | 37 | 0 | 2 | 2 |
| 其他戰鬥 | 36 | 34 | 1 | 1 | 0 |
| 合計 | **206** | **195** | **1** | **5** | **5** |

`game.counting.count_loop`只用於上述明示REPEAT／FOR COUNT，開始時寫0（FOR指定起點除外），每次NEXT讀共享值再加1；CALL不還原、RETURN／關閉generator不加，BREAK呼叫端明示加1。上限含CALL／RAND時延後到開始值設定後求值。沒有以函式尾常數代替本體時序；FOR LOCAL／CCOUNT及原作展開IF仍不碰COUNT。

| 原作來源（`ERB/`以下） | 原生邊界及可觀測結果 |
|---|---|
| `ゲーム内_戦闘処理/戦闘コマンド(性攻撃)/SEX_COM0.ERB@SEX_COM0:29–31、85–87`及同群37個COM／SPCOM；`SEX_COMEX.ERB@SEX_COMEX_RANDOM:100–111` | `sexcom._begin`37個清零、`_comex`22個RESULT合併，均12；額外選取兩個4輪。無追加分支不改COUNT；CALL完成後才開始合併迴圈 |
| `ヒロイン関連/ABL_UP_CHECK.ERB@_ABLUP:15–37`、`@ABL_UP_20:495`至`@ABL_UP_3:1156` | `ablup`12格兌換及15個升級的共用5輪；刻印不足RETURN不初始化，感覺上限BREAK仍加1 |
| `ヒロイン関連/CHARA_STATUS.ERB@SHOW_STATUS_TALENT:324–633、691–694`、`@STATUS_PRINT_EX:1203–1209`；`ステータス画面/SHOW_STATUS_CHARA_SELECT_PAGE1.ERB@SHOW_STATUS_CHARA_SHIELDS:375`、PAGE2各SHOW函式、PAGE5各SHOW函式 | TALENT七個檢查／顯示迴圈不能用any提早停，舊式尾299、分類尾250；EX只有ARG1／2有REPEAT。PAGE2三個原陣列長度15／5／37，JUEL12；PAGE5人格3／裏人格4及補空行／非顯示6、頁尾2；SHIELDS無結界不進迴圈 |
| `SYSTEM/キャラメイキング関連/EXPORT_CSV.ERB@EXPORT_CSV:21–35、130–242、465–574`；`CHARA_MAKE.ERB@CHARA_MAKE_MAIN:344–352`；`SHOKISET.ERB@CHARA_MAKE_FINALIZE_KAI:10–32` | 匯出13個迴圈，搜尋號碼BREAK含步進，身體已製作末值272、尚未製作289；人數增加／減少固定進入時上限，相等不碰COUNT；套組列表99及清空舊角色 |
| `インターミッション画面/SHOP.ERB@SHOW_SHOP:115`、`SHOP_SHOW_BOSS_INFO.ERB@SHOP_SHOW_BOSS_INFO:56、106`、`SHOP_SHOW_SITUATION_LIST.ERB@SHOP_SHOW_SITUATION_LIST:16、29`、`SHOP_FLASHNEWS.ERB@FLASHNEWS_CHOOSEIDOL:942–990` | 訊息補空行、敵列表逐次CALL、六個新聞權重迴圈；候選抽RNG前留下最後一組COUNT |
| `ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST:101、121、129`；`エンディング/ENDING.ERB@ENDING:32–44`、`SUCCESSION.ERB@SUCCESSION:278–290、1093–1095、1479–1484` | 初始化bit、新增／刪除角色與設施返款均同步；引繼新增0人原有IF不進REPEAT，保留前值；未改初始化／排程／RNG／存讀控制流 |
| `ゲーム内_イベント発生/イベントから派生する特殊戦闘/●イベント戦闘_襲撃共通.ERB@RAID_ATTACK:68`及救援共通`@RAID_RESCUE:60`；`敗北幽閉中イベント/COMMON_PRISON.ERB@COMMON_PRISON_EXP_SH:44`、`PRISON_COMABLE.ERB@PRISON_COMABLE:15、19`；`強制発生イベント/FORCE_夜間自慰.ERB@SELF_N:255`及SELF_B／A／V；`FORCE_いちゃラブセックス.ERB@SEX_V:165`、`@SEX_A:345`；`FORCE_夜這い.ERB@YOBAI_SELECT_PLAY:566–611`；`FORCE_悪堕ちキャラの淫謀.ERB@AKUOTI_EVENT:514、709–724、919–992` | 沿既有數值／候選／顯示本體同步；警示30輪，清零12格，候選4輪與經驗2輪；十個事件迴圈含開始上限的RAND及末組5輪。不新增任何敘事或經歷生成 |
| `ゲーム内_戦闘処理/BATTLE_SHOW_STATUS.ERB@SHOW_STATUS_PALAM:363`、`@SHOW_DISTANCE_WINDOW:542–740`；`BATTLE_COM.ERB@EVENTCOMEND:818、828、929`；`COMMON_BATTLE_FUNC.ERB@ACT_LIMIT:296–390`；`ENEMY_ACTION.ERB@ENEMY_ACTION:996`；`ENCOUNT.ERB@ENCOUNT_BOSS:230`；`GAPING.ERB@PRINT_TENTACLE_SIZE:757`、`@SET_TENTACLE_SIZE_R:1342–1384`；`PALAM_UP.ERB@PALAM_UP:232`、`@PALAM_TIJOU:1037`、`@PALAM_YOKUJOU:1065`、`@PALAM_KYOUJUN:1253` | 資源12、距離七個顯示迴圈、其餘感覺4及ACT_LIMIT5；ACT_LIMIT訊息CALL之後RETURN保留CALL留下的值；捕獲敵加權內層LOCAL的BREAK不步進COUNT |
| `ゲーム内_戦闘処理/SUBEVENT_BATTLEE.ERB@SUBEVENT_BATTLE_RAPED_ENEMY:28`、`@SUBEVENT_BATTLE_ACTTENTACLECLOTH:101`、`@SUBEVENT_RELEASE_ECSTASY:176`、`@SUBEVENT_BATTLE_ACTTENTACLESUIT:347`；`触手データ/雑魚敵/TENTACLE_MOB_SPCOM.ERB@MOB_CREATE_COM:51、326`；`戦闘コマンド(ヒロイン)/COMF5.ERB@COM5:53、103`、`COMF7.ERB@COM7:65、115`、`COMF45.ERB@COM45:39`、`COMF46.ERB@COM46:36` | 清零／合併12，釋放統計4；MOB的初始化移至原文敘事前；六個疲勞迴圈含零次與BREAK步進 |

其餘11行的邊界：

- 1行已由catalog執行：`ゲーム内_戦闘処理/触手データ/雑魚敵/TENTACLE_MOB_801_物質（カージャッカー）.ERB@MESSAGE_MOB_801_COM2:383`。測試中性化PRINT但保留原控制流、亂數及狀態寫入；兩個0骰值得到COUNT2。
- 5行沒有可達原生呼叫者：`SHOKISET.ERB@GROUP_SELECT_CSV:66`；`オープニング処理_カスタムGAMEMODE.ERB@GAME_OPTION_SET:80`、`@GAME_OPTION_CHECK_MULTI_F:99`；`FORECAST.ERB@MAJORITY_VOTING_PROBABILITY_NUM:240`僅被同檔未被呼叫的`@MAJORITY_VOTING_PROBABILITY`使用；`FIRSTSETTING_TITLE.ERB@FIRSTSETTING_TITLE_RANDOM:115`被:83清RESULTS及:85的WHILE排除。精確名稱全ERB搜尋已核對，不新增無呼叫者模組；主題證據沿[製作選單](../era/creation-menu.md)。
- **5行除錯缺口保留W08**：`SYSTEM/SYSTEM_DEBUG_口上色設定.ERB@KOJO_COLOR_LIST:43、69、139`與`オープニング処理_カスタムGAMEMODE.ERB@GAME_OPTION_CUSTUM:24、35`。唯一入口在`オープニング処理.ERB@MODE_SELECT:381–390`的`[IF_DEBUG]`負數-1／-2；現有Python沒有這兩入口，不把它們稱原作未完成或一般情況不可達。S90範圍只同步既有原生流程，COUNT整項及W07不因此宣告完成。

## 驗證

`tests/test_count_shared.py`：依引擎行號建立中性迴圈expected，含零次、負步進、BREAK／CONTINUE／RETURN、同元素及不同元素巢狀、跨CALL、INPUT兩通道、VARSET／越界、可回復失敗、hook後不可回復、巢狀交易、BEGIN TRAIN與JSON v1–4。

`tests/test_count_editor.py`與既有CSV案例：25歲人工前態，驗COUNT0／1、真實編輯返回及CALL改COUNT後的索引／NEXT；不以產品輸出反推expected。

真瀏覽器fixture為`tmp/s88/browser_fixture.py`：`editor`操作一人稱／性格／姓名後主入口99，原生值`[700,3]`；`csv`載入0並確認，原生值`[4,74]`。兩路接中性catalog可見顯示與INPUT，最後存讀原值。這是局部前態，不宣稱完整自然開局。

S88新增存讀狀態，因此依分級裁決交主代理跑一次全pytest、必要真瀏覽器與S84基線500局；後續單純原生局部終值同步不自動觸發另一次500，需新增核心影響或W07結包依據。

S89的`tests/test_count_equipment.py`共31案：11種CUSTOM_NUM／種類代表、COPY91兩分支／COPY92、缺函式、CALL本體讀值與覆寫、SAVE、剩餘槽0／正／負上限、武器RNG前COUNT及真選單／存讀／中性catalog、既有共用選取與色名RETURN邊界。首次測試先紅，再收斂等價入口避免57件重複測試；最終受影響定向`505 passed, 1 warning in 8.10s`。

`tmp/s89/browser_fixture.py`提供25歲人工局部前態兩路：cloth編輯／複製／貼上／重置後COUNT`[5,74]`，移除1槽部件後`[1,74]`；weapon追加字串／生成／選取後`[1,74]`。每段接中性catalog顯示及dump/load核對；不宣稱完整開局或存檔選單驗收。實際瀏覽器與主代理全pytest結果見S89 session；本次不改開局／排程／RNG演算法或存檔格式，也未結W07，依分級驗證不另跑500局。

S90定向新增`tests/test_count_remaining.py`：來源等價類、CALL→RETURN、NEXT覆寫、巢狀／上限求值、BREAK、零次、分支不進REPEAT、匯出存讀與既有catalog中性驗證。首次缺模組collection error；EX／疲勞案例先紅`7 failed, 6 passed`再綠。原OUTPUT_ABLS／MARKS／EXPS完整陣列為15／5／37，含EXPS的-1換行欄。

`tmp/s90/browser_fixture.py`為全新25歲人工局部前態：status `2000→5000→999→88`，PAGE2依原:31–35非debug略JUEL故COUNT37、PAGE5及返回後2；export `1→1→0→88`，末值272；COUNT1均74，dump/load一致、RNG不變。主代理執行真瀏覽器後回填session；fixture直驅不是瀏覽器證據。

S90不改開局／排程控制流、RNG抽法或存檔格式；初始化REPEAT內只有原有bit／增刪角色，沒有新跨CALL消費者；既有ACT_LIMIT的CALL後直接RETURN。依分級驗證不另跑500，亦未結W07。全pytest及真瀏覽器交主代理。

S90子代理最終受影響26檔定向：`1406 passed, 1 warning in 17.33s`，其中新增COUNT40案。`git diff --check`通過，source／reference未動；主代理驗收前產品／測試／fixture已凍結。

S90驗收修正：主全pytest的12個套組取消案例原本要求COUNT也保持載入後值；依`ERB/SYSTEM/キャラメイキング関連/SHOKISET.ERB@CHARA_MAKE_FINALIZE_KAI:10–12、38–39`，重入列表先完成FOR至99，取消RETURN不還原，因此只修正expected的COUNT0=99，保留其他狀態完整比較，未改產品。套組全檔及COUNT剩餘／共用定向：`136 passed, 1 warning in 1.66s`；其餘驗收沿主代理已有證據。
