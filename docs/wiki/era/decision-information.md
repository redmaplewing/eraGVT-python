# SHOP／戰鬥決策資訊（S86）

原作路徑相對 `source/earGVP/`；Python入口為 `game.shop`、`game.shop_status`、`game.battle.train`、`game.battle.status_display`。本頁涵蓋W07的數值、標記與分類選單；字型／共用欄寬、舊等待、HTML／圖樣、COUNT與catalog其他失敗路徑仍由W07接續。

## SHOP

- `ERB/インターミッション画面/SHOP.ERB@SHOW_SHOP_STATUS_TARGET:315–340`：等級後加入共用狀態標記，再顯示原20格漸層資源條；20格漸層先前已由S25接回，本次補列表4格條。
- `ERB/インターミッション画面/SHOP_SHOW_STATUS_LIST.ERB@SHOW_SHOP_STATUS_SIGN:158–188`：週期、憂鬱、疲勞、避孕、妊娠及既有特徵標記。疲勞20／50為換色邊界；`ERB/汎用関数/CPRINT.ERB@CPRINT:15–23`保留呼叫前顏色。
- `ERB/ヒロイン関連/ESTRUS_CYCLE.ERB@PRINT_ESTRUS_CYCLE:4–27`：依既有CFLAG217與排卵異常顯示，不抽亂數、不初始化週期。危險日13減異常值至15優先，異常3以上或16至18／19為排卵日，1為月經；未熟、男性、妊娠早退亦不重設顏色。
- `ERB/インターミッション画面/SHOP_SHOW_STATUS_LIST.ERB@SHOP_SHOW_STATUS_PARTY_LIST:9–42`：姓名／行動後第二行顯示三種4格資源條及標記。寬度統計納入狀態0／10／11，實際出場列表只列0；不合併兩種篩選。
- 同檔`@SHOP_SHOW_STATUS_RESERVE_LIST:52–86`：候補使用呼び名，狀態0／10／11均列出，資源／標記同一行。
- 同檔`@SHOP_SHOW_STATUS_COUNT_MAXLEN:100–124`與`@SHOW_SHOP_STATUS_BASE_ONELINE:133–150`：姓名依cp932位元組長度、數值依最大位數補齊。`ERB/汎用関数/コモン関数.ERB@INTLEN:208–212`是TOSTR後字數，包含負號；不是引擎內建命令。
- `ERB/汎用関数/コモン関数.ERB@COLORSENTENCE_MINIBAR:118–142`：使用▂／▁、長度4及原色階。139行以最大值除長度決定數字顏色，照原文保留。
- `ERB/インターミッション画面/SHOP.ERB@SHOP_NG_ACTION_INFO:347–381`：保留紅色殘值，函式本身沒有RESETCOLOR。

## 戰鬥資訊與選項

- `ERB/ヒロイン関連/CHARA_STATUS.ERB@SHOW_STATUS_BASE_DISPBATTLE:18–205`：名稱／等級／性別／未變身準備、種族與feat效果、PALAM上部、三距離適性與style、支援比率、衣裝耐久、EX／SP、AIR／CHARGE依原次序顯示。距離適性為自身得意2−自身苦手2−其他距離得意，各分級>=1◎、<-2×、<-1△、其餘○。
- 同檔`@STATUS_PRINT_FEAT:1529–1713`依現況顯示禁用顏色與效果。`@STATUS_PRINT_EX:1156–1343`保留五格數值／消費預告；`@STATUS_PRINT_AIRGAGE:1347–1472`保留八槽與本次消費預告；`@STATUS_PRINT_CHARGE:1477–1525`每次SHOW_STATUS恰計算一次TCVARn206，沒有額外重算。
- `ERB/武器と衣装/衣装関連/CLOTH_BATTLE.ERB@CLOTH_BATTLE_DISPHP:31–192`只讀已計算耐久與CLOTH表，負／零／損壞／低於防護門檻／低於中段／完整各依原值及顏色。零外衣分支仍讀CFLAG40，即使已變身亦保留此原文判斷。
- 耐久下方經既有catalog執行`ERB/武器と衣装/衣装関連/CLOTH_衣装カスタマイズ共通処理.ERB@CLOTH_CUSTOMIZE_OPTION_DRAW:161–182`，由EQUIP九位拆出CUSTOM，呼叫原DRAW函式。這些是玩家已選改造／衣裝資訊，不能以純外觀為由省略；沒有新增遊戲邏輯解譯能力。
- 61個DRAW根函式／個別函式皆可由既有catalog執行，原DRAW本文無RAND。根函式原TRYCCALL找不到特定衣裝DRAW時印空行；真正catalog執行失敗則明確停止。只有既有NullNarration測試代理允許無標籤空行，不能用Null驗收正式畫面。
- BAR空段使用預設點：`reference/emuera-1824/Emuera/GameData/Expression/ExpressionMediator.cs:121–144`、`Config/ConfigData.cs:130`；原`CSV/_Replace.csv`只有空白BAR文字1且不生效，沒有BAR文字2覆寫，見[未決查證](../bridge/unresolved.md)。COLOR_BAR除零仍依原作報錯，不為不完整測試前態自訂替代值。
- `ERB/ゲーム内_戦闘処理/BATTLE_SHOW_STATUS.ERB@SHOW_STATUS:18–132`狀態標記、177–217幽閉／洗腦名單、232–250剩餘時間、256–331敵資源及解析能力均接回。名單原文只比CFLAG21與FLAG11／FLAG111，沒有CFLAG20敵類篩選，沒有自行加條件。
- `ERB/汎用関数/コモン関数.ERB@COLORSENTENCE_ENEMYBAR:146–190`：解析25可見上限、50可見當前值，除錯與角色敵直接顯示；數字被遮蔽時條長仍照真實比例。原HP標籤顏色也使用最大值／長度，不另修正。
- `ERB/ゲーム内_戦闘処理/BATTLE_SHOW_STATUS.ERB@SHOW_DISTANCE_WINDOW:510–759`：地面／空中、禁止空中／遠距離、拘束、危險預測與準確度分級。位置擾動只依DAY與TFLAG0模4，沒有RAND。敵名SUBSTRING(0,1)保留跨過第一byte的整字，依`reference/emuera-1824/Emuera/_Library/LangManager.cs:40–82`，不是截斷cp932後解碼。
- `ERB/ゲーム内_戦闘処理/FORECAST.ERB@PRINT_FORECAST:259–322`、`@FORECAST_OUTPUT_NUM:325–342`、`@FORECAST_OUTPUT_SETCOLOR:344–360`：未知為？、拘束為―、禁止空中為---，色彩依原門檻。
- PALAM仍由既有`show_train_palam_status`控制開關／上部下部／開閉；`ERB/ヒロイン関連/CHARA_STATUS.ERB@SHOW_TRAIN_PALAM_STATUS:1715–1750`與`ERB/ゲーム内_戦闘処理/BATTLE_SHOW_STATUS.ERB@SHOW_STATUS_PALAM:353–426`。本次沒有增加PALAM實際執行次數。

## 分類指令

`ERB/ゲーム内_戦闘処理/BATTLE_COM.ERB@SHOW_USERCOM:8–377`的FLAG801 bit2=1路徑已接回，正常／拘束各三組，按鈕810／820／830改TCVARn8；原不分類379–568路徑保留。每排原順序與空格均保留，拘束特殊組兩次72也是原文。可用性仍由`ERB/ゲーム内_戦闘処理/COMABLE.ERB@COM_ABLE*`與`PRINT_COMNAME.ERB@PRINT_COMNAME:2–36`，不可用指令留空，不自行加灰色按鈕。

`@USERCOM:629–639`處理分類與898／899的PALAM開閉／移位，不推進指令、不抽RNG。實際4防禦照原`COMF4.ERB@COM4:2–44`接SOURCE_CHECK及EVENTCOMEND。先制期間只減TFLAG24，TFLAG0不加一（`ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:1313–1318`）。

## 副作用與驗證界線

- SHOW_STATUS出口RESULT0=0，未傳入的RESULT尾格保留；一般函式終端及RETURN依`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`、`GameProc/Function/Instraction.Child.cs:2014–2023`。
- 每次顯示的支援計算沿`ERB/ゲーム内_戦闘処理/BATTLE_SHOW_STATUS.ERB@CALC_CHISEI_SHIEN:467–505`呼叫衣裝補正；CLOTH_HOSEI更新SAVESTR0，SUBSTRING命令更新RESULTS0。只在本次顯示呼叫傳registers=True，不擴散其他原生呼叫者；無支援者則不寫SAVESTR0。
- `ERB/ゲーム内_戦闘処理/COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS:198–309`在201行對**每個key**先寫診斷字串；成功數值回傳也不清空。NAME／GETNAME才換成名字。普通敵畫面通常最後CHISEI，解析100最後HOLD；角色敵不呼叫它，保留最後支援衣裝SUBSTRING字串。
- 定向前態以支援者外衣109（`CLOTHDATAアウター_通常.ERB@CLOTH_STATUS_109:1710`的CHISEI110）、內衣0（`@CLOTH_STATUS_0:73`的SLOT-1,HP0,def0,）驗證：入口RESULT0=888／RESULTS0=入口殘值／SAVESTR0=入口衣裝；出口RESULT0=0、RESULTS0為CHISEI／HOLD診斷或110，SAVESTR0為內衣0字串；兩組尾格與TARGET保留。
- 下一個USERCOM分類／898／899不讀RESULTS；戰後可達FLASHNEWS前會由SAVEINFO覆寫。沿用[result](../python/result.md)全域消費者查證，這些殘值沒有新增跨系統排程／RNG／存讀行為。
- PALAM既有`ERB/ゲーム内_戦闘処理/GAPING.ERB@PRINTFORM_GAPING_NOW:800–808`可能初始化CFLAG35／36並耗RNG，不能稱所有顯示無副作用；開關／上下位置保持原呼叫數，定向以代理確認一次／關閉零次。既有S11／S34行為不另改寫。
- 新增39案，最初18案先紅後綠；涵蓋週期、資源／衣裝邊界、解析遮蔽、六分類、實際可用性、RNG、RESULT(S)／SAVESTR、PALAM及CHARGE次數。整批定向1198通過、2個舊人工敵前態缺FLAG14失敗，依ENCOUNT_BOSS補初始值後僅重跑該檔2案通過；主代理提交前完整`5443 passed, 1 warning in 197.40s (0:03:17)`，新增39案。
- `tmp/s86/browser_fixture.py`為三個獨立25歲人工前態（shop／flat／grouped），完整catalog、真Web輸入與決策顯示；生成起固定25歲，不改產品年齡。主代理三路真瀏覽器通過，SHOP展收與分類／PALAM控制不耗RNG，兩入口防禦4後prevcom4／EX12／先制2／turn0；catalog及console失敗0。證據`tmp/s86/browser-summary.json`及三張畫面，詳[S86 session](../../sessions/S86-decision-information.md)。W07未結包，本階段不觸發500局。
