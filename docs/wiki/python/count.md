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

## 下一成果仍留同一 COUNT 項

2026-10-07精確搜尋：`rg --pcre2 '(?<![A-Za-z_])COUNT(?![A-Za-z_])' source/earGVP/ERB --stats`得到795 matches、570行、76檔；`^\s*(REPEAT\b|FOR\s+COUNT(?:\s|:|,))`得到291迴圈行、90檔。原始搜尋含不可達／原作未完成函式；**不等同291個產品缺口**。

扣本次17處後，274行按原檔互斥分組如下；這是後續查證／同步範圍，不把未查群組認定無影響。COUNT會存檔，因此即使沒有立即的分支讀取，殘值仍可觀測；既有COUNT偏離保持未結案。

| 群組 | 迴圈行數 | 對應原檔／目錄與下一步 |
|---|---:|---|
| 衣裝 | 63 | `ERB/武器と衣装/衣装関連/`的CUSTOM_NUM、COPY91、SAVE、DRAW與外衣slot；優先接共用手翻入口 |
| 攻擊數值 | 61 | `ERB/ゲーム内_戦闘処理/戦闘コマンド(性攻撃)/`；LOCAL清12格及RESULT合併可沿共用Python函式同步 |
| ABL升級 | 16 | `ERB/ヒロイン関連/ABL_UP_CHECK.ERB`；起始清空與各5次迴圈 |
| 狀態顯示 | 19 | `ERB/ヒロイン関連/CHARA_STATUS.ERB`及`ステータス画面/`，包括編輯畫面呼叫的SHOW_STATUS_TALENT |
| 製作／除錯 | 22 | `ERB/SYSTEM/キャラメイキング関連/`扣本次項目，及`SYSTEM_DEBUG_口上色設定.ERB`；EXPORT、人数／套組、主題（其WHILE條件不可達已另有原作證據） |
| SHOP | 11 | `ERB/インターミッション画面/SHOP*.ERB`，包括FLASHNEWS_CHOOSEIDOL與決策資訊 |
| 開局／結局／其他事件 | 41 | `ERB/ゲーム内_イベント発生/`扣本次三個模式函式；初始化、引繼、幽閉與夜間各原生邊界 |
| 其他戰鬥 | 36 | `ERB/ゲーム内_戦闘処理/`扣攻擊數值；含1個已由catalog共用承接的中性化驗證未涵蓋訊息迴圈，不能全稱未接 |
| 汎用／武器 | 5 | `ERB/汎用関数/CHOOSE_RAND_1.ERB`、`GET_COLOR_NAME.ERB`與`ERB/武器と衣装/武器カスタマイズ関連/GENERATE_ADD_STR.ERB` |

## 驗證

`tests/test_count_shared.py`：依引擎行號建立中性迴圈expected，含零次、負步進、BREAK／CONTINUE／RETURN、同元素及不同元素巢狀、跨CALL、INPUT兩通道、VARSET／越界、可回復失敗、hook後不可回復、巢狀交易、BEGIN TRAIN與JSON v1–4。

`tests/test_count_editor.py`與既有CSV案例：25歲人工前態，驗COUNT0／1、真實編輯返回及CALL改COUNT後的索引／NEXT；不以產品輸出反推expected。

真瀏覽器fixture為`tmp/s88/browser_fixture.py`：`editor`操作一人稱／性格／姓名後主入口99，原生值`[700,3]`；`csv`載入0並確認，原生值`[4,74]`。兩路接中性catalog可見顯示與INPUT，最後存讀原值。這是局部前態，不宣稱完整自然開局。

S88新增存讀狀態，因此依分級裁決交主代理跑一次全pytest、必要真瀏覽器與S84基線500局；後續單純原生局部終值同步不自動觸發另一次500，需新增核心影響或W07結包依據。
