# 共用個別角色編輯（S60／W02）

## 已接通與入口

- 原作路徑以下相對 `source/earGVP/`。Python：`game/character_editor.py`、`character_name.py`。
- `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:6–353`：主選單1氏名、2呼稱、3一人稱、5口上、11–14變身名／呼稱／掛聲／名乗、16–18衣裝、24武器均能操作；99決定。
- 主選單沒有取消。各子選單有自己的取消／返回；不要添加整個角色的回滾交易。
- `ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB@CHARA_MAKE_MAIN:142–145、202–204`：男女汎用角色、已存在角色共用入口。
- `ERB/ゲーム内_行動実行処理/ACTIONsub_TSUIKAYOUSEI_NORMAL.ERB@TSUIKAYOUSEI_NORMAL:29–39`：[0]/[1]進入編輯器；[2]原作略過，特徵選單後才FINALIZE。
- `ERB/ゲーム内_行動実行処理/ACTIONsub_DRUG_PREPARATION.ERB@DRUG_PREPARATION:303–315`：傳ARG:2=1，只鎖種族與CSV，不鎖姓名、衣裝等。
- `ERB/ゲーム内_イベント発生/エンディング/SUCCESSION.ERB@SUCCESSION:1491–1560`：先調整修練點，再傳周回bonus進CHARA_MAKE_MAIN。MAIN的ARG:1只在999讀CSV後:323補回bonus*10，進入／99不能重複加。
- `ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD`無FIRSTSETTING_CHARA_MAIN呼叫。保留既有獨立命名／一人稱／變身名／SIZE_SETTING流程，不插入不存在的主選單；身體與一人稱代按仍留同W02後續。
- `ERB/武器と衣装/武器カスタマイズ関連/WEAPON_CUSTOMIZE.ERB@WEAPON_CUSTOMIZE:8–80`雖接受ARG:1=1，但函式不讀它，故共用既有customize。

## 狀態次序與查證

1. MAIN:9–14僅備份有名稱的ITEM100–699並暫設1；退出:348–350還原整段，因此無名稱槽歸零，700以外不動。
2. :20–21只在CFLAG240=0時INITIALIZE；子選單返回到START_CHARA_SETTING，不回MASTER_LOOP，不解碼／不重新生成。新角色再次進入仍依原文檢查240。
3. :24–34依序解碼CSTR15–17，然後清空三格。
4. :112–137顯示身體、杯數、性格、素質、EXP仍按次序留下RESULT/RESULTS；`ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE.ERB@GENERATE_CHAR_SIZE:239–249`男性也呼叫CUP_SIZE，不能漏RESULTS:0。
5. :237–337拒絕輸入只重讀、不重畫、不抽RNG。主選單0性別雖未顯示仍接受（非固有）；17僅變身能力=1且非悪堕ち；12還要求CFLAG2=1才開呼稱頁。
6. 99先BASEUP_CAL_SHIELD，再清SAVESTR0–3及還原ITEM，清畫面返回；TARGET始終由呼叫者管理。
7. INPUT只寫RESULT0、INPUTS只寫RESULTS0：`reference/emuera-1824/Emuera/GameProc/Process.cs:249–260`；自然終端只寫RESULT0=0：`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`。
8. 姓名來源：`ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_NAME:496–686`、`@FIRSTSETTING_CHARA_NAME_RANDOM:690–1021`。手動姓／名、CSV預設、排列、沿用他人姓氏、20候選生成／重抽／固定順序均接通；詞庫讀CSV STR。命名後依:678–683同步CALLNAME與原本相等的變身呼稱。
9. STRLENS／SUBSTRING使用CP932位移：`reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:2095–2165`、`Emuera/_Library/LangManager.cs:40–85`；STRFIND:2222–2279用IndexOf文化比對，沿既有W08未決項。
10. 固定文字由`tools/extract_character_editor.py`抽取，流程手寫，不增加ERB直譯器。

## 原作怪處與未完成範圍

- 姓名候選頁可固定姓名排列，但回傳:1008–1021不讀固定順序，依姓氏語言組合；照原作保留。
- 同段判斷隨機姓氏的區間時用COUNT而非RESULT。最後REPEAT終值20使索引落在LOCAL30（第一個名字編號）；本函式照這個索引保留。共用COUNT尚未模型化，沿既有W07偏離，不能說全域COUNT已等價。
- 中文名字:913–920兩次WHILE誤查姓氏格；第二字LOCAL31+COUNT又會被下一次名字覆蓋。正常姓氏存在時保留兩次抽數及覆寫；空姓（可由未定義語言手輸觸發）原作無窮重抽，Python明確停止，歸W08安全網待裁決。
- 同姓選擇:656允許RESULT==CHARANUM而取不存在角色，原作越界；Python明確停止，歸W08原作錯誤，不當成未移植玩法。
- S61接通[6]的年齡、身高、一般外貌、髮型／色彩、人格文字、重抽參數與確認／重入；共用編輯及狀態PAGE5[20]均等待真實輸入。完整範圍與未完成分支見[身體編輯](body-editor.md)。
- W02後續：0性別、4種族、7性格／精神、8經歷／初始經驗、10變身能力、23基礎點、999 CSV讀入，以及主製作初始狀態／人數；SIZE_SETTING其餘選項仍明確停止，不能稱整個身體編輯完成。
- CSV讀入與既有`export_csv.py`不同；EXPORT_CSV安全網仍屬原先W08。TS／特殊裝備生命週期仍W03。

## 驗收與重現

- S60定向：`531 passed, 1 warning in 17.41s`（編輯器31、招募／醫療／引繼／共通製作／一人稱／武器）。新入口從紅測試起步，expected取原文。
- Web代表案例涵蓋男女個別開局、取消呼稱、文字修改、99完成、重入及SHOP追加招募；未把API案例當真瀏覽器。
- 兩開局seed0–1、max-shop200、actions101–108四局均到上限，JSON完整物件與S59逐seed一致；未修改sim策略。
- 父代理獨立全pytest：`3905 passed, 1 warning in 385.01s (0:06:25)`；25歲一般子選單及四入口真瀏覽器通過，正式500見STATUS。
- 25歲真瀏覽器重現依[S60d](../../sessions/S60d-adult-editor-validation.md)：`tmp/s60d/adult_editor_fixture.py`與`adult_entry_fixture.py`；四入口使用真實生成／確認／重置、人工定義與NullNarration，不修改使用者存檔，不冒充自然通關。

- S60收口抽查補隨機命名重繪清理：原文`@FIRSTSETTING_CHARA_NAME_RANDOM:823、990、993、997、1001`；配置／重抽／排列只移除對應頁，選項100保留原文返回設定的路徑。全新25歲中性資料9案先紅後綠，加既有6案共`15 passed in 0.14s`；父全回歸與25歲真瀏覽器均通過。
- 清除範圍依據：配置頁`:699–798`為2個前置空白＋15列選單，數字輸入回顯再加1列，原文清16保留呼叫者與2空白；候選頁`:942–978`為1空白＋20候選＋3控制列，輸入回顯後清25。回顯見`reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:733–734`，刪行見`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:488–500`。Python既有精簡版面合併控制列、沒有上述空白／數字回顯，故按當頁實際行數清理；這沿W07顯示偏離，不宣稱逐行排版等價。

## S60 的 25 歲模擬資料

- 使用者於2026-10-06同意建立獨立人工基線：`python -X utf8 tools/sim_adult.py --preset default --seeds 0-49 --max-shop 200 --actions 101,102,103,104,105,106,107,108 --dump tmp/s60/adult25-v1/default-0.jsonl`；其他種子每50局，`tokusou`同參數。
- 工具從載入的設定新建77個記憶體`CharaDef`；姓名／呼び名是人工名稱（分派key `汎用キャラ`保留），nickname/mastername留空、source清空；數值玩法與其餘CSTR設定沿用原編號。不是載入既存角色改齡，也沒有修改CSV、產品年齡規則、性別或玩法開關。
- 生成前BASE40/41=25、CSTR204/205/206=`25`：`ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_AGE_SETTING:1408–1444`。真實初始化／完成、兩入口、catalog、遊戲及方針RNG、sim策略／事件計數均保留；人工名稱與年齡會影響條件及亂數後續，不能宣稱與S59同資料等價。
- 每次輸入前後、catalog函式前後、文字／按鈕輸出前檢查全員（含管理員與非TARGET）。BASE40/41與MAXBASE40必須25；MAXBASE41為25或原作-1哨兵。違反時只記錄`fixture_age`數值原因並停止，沒有修補、忽略或重抽。
- -1是未設定另一形態年齡：`ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@CHARA_SIZE_DEFAULT:2152–2153`。`CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_BASE_PROFILE:520、533–534`先設定哨兵，之後才賦予人間變身能力；不能依最終TALENT誤判為未成年。任何實際年齡非25、或另一形態的正值非25仍停止。
- 工具只輸出停止原因、數值及事件函式計數；畫面只供既有策略讀按鈕，不輸出或保存敘事。JSONL逐局落盤，額外標註fixture版本、fixture_stop、catalog_failures、preset與參數；fixture停止不是遊戲未實作，也不算跑滿200SHOP。
- 工具定向先缺模組紅測試，再補原作哨兵先紅後綠，`8 passed in 1.07s`。default seed0煙測到上限（沿用sim於下次SHOP退出，shops=201），catalog失敗0、fixture停止0。父正式500：default247上限／3回標題、tokusou250上限，catalog失敗0、fixture停止0；十批完整性核對通過，見STATUS。此工具不替代瀏覽器／全模式驗收。
- `--workers N`（預設1）只平行同一前景批次的seed；spawn建立獨立程序，每程序一局即退出，catalog／事件計數／RNG／臨時存檔不跨局。主程序按seed輸入順序落盤、等待整批，離開時關閉worker；不建立跨批背景工作。工具定向`9 passed in 7.70s`，實際default seed0–1／max-shop2的workers1與2完整JSON一致。
