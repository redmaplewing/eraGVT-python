# 衣裝設定、購買與變身零件描寫（S39／S40／S73）

## 入口與範圍

`ERB/インターミッション画面/SHOP.ERB@USERSHOP:257–259`：非遊戲結束模式且有活動角色時呼叫衣裝設定。
Python 入口為 `GameSession → clothing.cloth_wear_gen`。SHOP [120] 購買入口於S40接通，詳見下節。

`ERB/武器と衣装/衣装関連/CLOTH_WEAR.ERB@CLOTH_WEAR:3–245`：

- 只有一名角色時直接選1；多人時呼叫 `ERB/汎用関数/コモン関数.ERB@CHARA_LIST:303–355`。
- 選角僅允許 `CFLAG:999 != 0` 且 `CFLAG:0 == 0`；一人直接進入時沒有這個選角檢查。
- 外衣／變身外衣／內衣／其他裝備對應 `CFLAG:40/41/42/43`。
- 改名寫 `CSTR:8/9`，INPUTS 空字串也接受；換裝與卸下不清名稱。
- 內衣自訂按鈕的內層條件失敗時會落出函式，而非一律返回同一選單。

## 換裝與部件

`ERB/武器と衣装/衣装関連/CLOTH_WEAR.ERB`：

| 函式 | 行號 | 行為 |
|---|---:|---|
| `@CLOTH_SETTING_OUTER` | 251–322 | 100–199；持有值恰為1；197限非戰鬥員 |
| `@CLOTH_SETTING_OUTER2` | 326–421 | 100–299；列表略過197但仍可手動輸入；401需陥落経験 |
| `@CLOTH_SETTING_INNER` | 425–576 | 300–399；399確定後變400；非308清體操服相依設定 |
| `@CLOTH_SETTING_MISC` | 581–632 | 500–599；持有值恰為1 |
| `@CLOTH_RESETTING_TENTACLECLOTH` | 637–663 | 拆400消耗一片FLAG:200，不足時重問 |
| `@CLOTH_CUSTOMIZE_OUTER2` | 941–1290 | 600–699部件槽、身體／衣裝限制、同類互斥；輸入判斷含700 |

選取物品先暫存，只有[1]確定才換；[0]取消，[2]卸下。
變身外衣真的改成另一件才清 `EQUIP:600–699`；相同衣裝與卸下均不清部件。
部件替換先移除同類別，再算剩餘槽；因此滿槽仍可替換。

## 57種自訂

遊戲規則在 `clothing_custom.py` 手寫：保存編碼、類別／子選項可用性、研究門檻、連動修正。
原文文字常數由 `tools/extract_clothing_text.py` 抽至 `clothing_text.py`，
`MENUS[衣裝ID]["source"]` 記錄每個原作檔案、函式與起始行；不存放可執行ERB條件。
描述抽取器遇非註解／非PRINTL語句立即報錯，避免靜默丟失動態文案。

保存共通低位依據：
`ERB/武器と衣装/衣装関連/CLOTH_衣装カスタマイズ共通処理.ERB@CLOTH_CUSTOMIZE_OPTION_SAVE:561–572`。
第1–9位為外觀，第10／11位為輕／重裝，第12／13位為保護下降／上升；
第14位在部分外衣表示內衣兼用、在內衣表示油斷下降，第15位為內衣油斷上升。
高位直接相加，不額外限制為單一十進位數字。

已保留原作怪處：

- `ERB/武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB@CLOTH_CUSTOMIZE_OPTION_153:8634`：`CUSTOM:1 <= 3 && >= 7`永不成立。
- `ERB/武器と衣装/衣装関連/CLOTHDATAインナー.ERB@CLOTH_CUSTOMIZE_OPTION_305:968`：同一 `CUSTOM:2 == 1` 條件連續加重量1與2。
- `ERB/武器と衣装/衣装関連/CLOTHDATAインナー.ERB@CLOTH_CUSTOMIZE_OPTION_304:750`：保存運算和選項效果文字不同，兩者各自照原文。
- `ERB/武器と衣装/衣装関連/CLOTH_WEAR.ERB@CLOTH_CUSTOMIZE_OUTER:668–937` 與 `@CLOTH_CUSTOMIZE_INNER:1293–1533`：不還原TARGET，返回時清CFLAG:1。
- `ERB/武器と衣装/衣装関連/CLOTHDATAアウター_通常.ERB@CLOTH_CUSTOMIZE_OPTION_104:789`：COMMON顯示5類，但第6類[50]與追加裝備[60]的輸入仍照原作接受。

## 戰鬥補正與瀏覽

`ERB/武器と衣装/衣装関連/CLOTHDATAカスタム.ERB@CLOTH_CUSTOMIZE_COMMONPARTS_CAL:9–18`：
TARGET的非零部件逐一加上該模式常數，沒有對應函式則略過，不看ITEM持有。
補齊衣裝106／115／117／153的內衣兼用與保護分岐、199個別強化、397外衣未裝時回避。

`ERB/武器と衣装/衣装関連/CLOTH_衣装カスタマイズ共通処理.ERB@CLOTH_HOSEI:132–147`：
EQUIP未指定角色，讀TARGET；基礎變身分岐仍讀ARG。此處修正先前Python誤讀ARG。

`ERB/インターミッション画面/SHOP_CLOTH.ERB@SHOW_CLOTH:13–252` 的持有品模式：
分類、單件／目錄／簡易顯示、翻頁、19種交集篩選、返回。
`@LIST_CLOTH_HAVE:616–642` 接受任何非零持有值；
`@FILTER_CLOTH_HOSEI:678–759` 對部件只檢查函式存在，因此負補正也可能被篩出。
[98]僅清FILTER，不重設PAGE／選取位置，照原作。

## 引擎依據與驗證

- INPUT／INPUTS共用變數：`reference/emuera-1824/Emuera/GameProc/Process.cs:249–260`；只改第0格。
- 字串長度／截取：`reference/emuera-1824/Emuera/_Library/LangManager.cs:17–20、40–84`；名稱表長度與截斷以cp932位元組。
- TIMES：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:893–916`；沿用 `era.times` 的Decimal乘算。
- 定向測試 `tests/test_clothing_menu.py`：212項通過；含57件非零編碼矩陣、57個選單來回、相依修正、條件、部件、GameSession與瀏覽。
- 主代理獨立完整 pytest：2491 passed, 1 warning；500 局標準模擬 default 246 上限＋4 標題返回、tokusou 250 上限，catalog_failure 0。
- 10 批前景程序 exit=0；逐 seed 完整結果與 S38 相同，log／JSONL／exit／audit 留在 `tmp/s39/`。抽取器重跑前後 clothing_text.py SHA256 相同。

## 變身零件描寫（S73／W03）

`ERB/ゲーム内_戦闘処理/戦闘コマンド(ヒロイン)/COMF0.ERB@COM0:21–32、51–112`：
名乗り標記`TCVARn:10 != 1`時先口上，再立標記、零件描寫、觀眾反應，然後才變身與回復。
同場重複變身跳過名乗り與描寫。`@COM201／202／203:118–126`共用COM0。
Python仍以原生COM0執行遊戲規則；`commands._msg_nanori_byousha`接既有地の文catalog。

`ERB/地の文/MESSAGE_BATTLE.ERB@MESSAGE_BATTLE_CHARA_NANORI_BYOUSHA:216–342`全部分支：

- `600–603`依序獨立輸出；先以四格總和計總數，再以恰等於1判斷每個零件，連接詞由LOCAL計數決定（221–267）。不把大於1或負數改成布林值。
- `672／673`各自判斷恰等於1，可同時輸出（269–272）。
- 外衣固定讀`CFLAG:41`，200／201／202／299／401／199有專用節點；41與42都為0時再依兩素質與能力門檻選節點，其餘取ITEMNAME（274–299）。不看變身旗標或耐久，不補零件有效性檢查。
- 後段先判任一零件大於0，披肩類依660→661→664優先；都非1才走690／691／693及680／681的獨立描寫。LOCAL只計腳部，兩個手部之間不額外遞增（301–332）。
- `CUSTOMIZABLE`僅有本函式的`#DIM`與333行讀取，全ERB精確搜尋2筆、沒有賦值；預設0，因此沒有334行節點。引擎預設STATIC：`reference/emuera-1824/Emuera/GameProc/UserDefinedVariable.cs:23–27`；零值整數陣列初始化：`reference/emuera-1824/Emuera/GameData/Variable/VariableToken.cs:1847–1857`。
- 最後`CFLAG:TARGET:2 == 1`取`CSTR:0`，否則取`PRINT_TRANSCALLNAME(TARGET)`（338–342）。本函式沒有INPUT、RAND、色彩命令或遊戲狀態寫入，只有函式LOCAL。落尾`RESULT:0=0`，其他RESULT格與RESULTS保留：`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`。Null也保留落尾值，文字沿既有catalog標籤回落。

部件來源沿既有原生衣裝選單：`ERB/武器と衣装/衣装関連/CLOTH_WEAR.ERB@CLOTH_CUSTOMIZE_OUTER2:1240–1277`，切換0／1，660／670／680／690各十格類別互斥。
描寫不重做選單限制；人工異常組合驗證原分支順序，沒有據此擴大遊戲可選範圍。
其他四處呼叫是`ERB/口上/固有キャラ専用口上/kojo_158_森亜るるか.ERB@KOJO_158_BATTLE_CHARA_DEFENSE:700`、`@KOJO_158_BATTLE_CHARA_STEPIN:713`、`@KOJO_158_BATTLE_CHARA_SEETHROUGH:726`、`@KOJO_158_BATTLE_CHARA_TAKEAWAY:739`，已在原catalog內，未另加遊戲執行捷徑。

新增`tests/test_transformation_parts.py`85項：四零件全部組合、披肩優先序、獨立腳／手部、非0／1值、六件專用外衣與一般／無外衣條件、三種變身旗標、重入、TARGET／RESULT(S)／色彩／RNG、COM0移動與回復、真實run_train及Web邊界。
新案例全為25歲人工兩形態；顯示只比原文PRINT節點行號，無敘事摘錄。定向連同戰鬥及衣裝選單共326項通過。
`tmp/s73/browser_fixture.py`提供三槽外衣200搭601／602／661、真戰鬥入口；無效998不改狀態，可見原[201]（COM0別名）完成後體氣500→700、變身1、EX12、外衣耐久130保留，回原戰鬥選單。本次catalog、其餘Null、輸出遮敘事；只是人工邊界，完整瀏覽器與500局由主代理獨立驗收，見STATUS。

## 特殊裝備回合效果（S74／W03）

`ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:12–40、117、439–447、717–835`：先疲勞，再依`CFLAG:43`獨立判506／507／509，之後才末王形態、勝利、運動結算與敵方行動。沒有變身或體力門檻；未裝相關物品不抽本次亂數，也不額外清RESULT。

三函式皆位於`ERB/ゲーム内_戦闘処理/MISC_PATCH.ERB`，遊戲規則由`battle/special_equipment.py`手翻，只有選定的PRINT節點沿原catalog：

- `@TK_DRONE:3–39`：先抽`RAND:26`，暫清`TCVARn:3`的bit0，呼叫既有`DAMAGE,"ATTACK_RANGE_LONG"`後還原；其餘位元保留。傷害是`RESULT*亂數/100`，亂數0–4加50、5–19加100、20–25加250。`FLAG:73>0`強制本次扣血0，但仍完整執行DAMAGE並抽其亂數。敵體力直接相減、不封0；正傷害才顯示數字，最後FONTREGULAR也會清斜體，色彩不改。
- `@HP_AUTOREGAIN:43–52`：抽`2+RAND:7`，乘最大體力除100；加回後大於等於上限，改以「最大值−目前值」回復。沒有下限修正，因此超上限會扣回，負上限按原算式處理；只有正回復顯示。
- `@SERVANT:56–83`：抽`RAND:25`直接加到`TFLAG:3`，若`FLAG:17+TFLAG:3<FLAG:16`再加25。前段顯示依`ENEMY_TYPE_CHECK_F("CITIZEN")`，後段分支依`FLAG:73>0`，兩者不能合併：`ERB/汎用関数/コモン関数.ERB@ENEMY_TYPE_CHECK_F:1356–1371`還要求`FLAG:110==0`。
- `ERB/ゲーム内_戦闘処理/COMMON_BATTLE_HANTEI.ERB@DAMAGE:1175–1546`保留既有原生傷害補正、靜態LOCAL與`RAND:100`；只有bit0攻擊增幅被裝備暫停，bit1防禦、戰技／風格等照舊。`ERB/ゲーム内_戦闘処理/PALAM_UP.ERB@PALAM_UP_ENEMY_REACTION:1823–1852`在後續結算消耗509的`TFLAG:3`。

全ERB精確搜尋三個函式名共6筆：3個定義＋SOURCE_CHECK的3個呼叫，無其他呼叫者。MISC_PATCH沒有INPUT、KOJO或其他隱藏分派；PRINTW沿既有顯示行為，W07的一般WAIT議題不在本次改動。
引擎依據：自然落尾`RESULT:0=0`見`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`；RETURN多值只覆寫傳入格見`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1997–2024`與`GameData/Variable/VariableEvaluator.cs:1732–1740`；除法朝零見`reference/emuera-1824/Emuera/GameData/Expression/OperatorMethod.cs:298–312`；字型見`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1084–1121`。片段額外的CALL落尾不外洩，保留原inline時的RESULT，裝備函式完成才歸0，尾格／RESULTS不清。

`tests/test_special_equipment.py`158案使用全新人工25歲、兩形態25歲，覆蓋門檻、負值／超限、位元、RNG次序、疲勞與勝利順序、原catalog節點／字型、三路真實COM201→COM0→SOURCE_CHECK→下一戰鬥輸入及Web邊界。
`tmp/s74/browser_fixture.py --equipment 506|507|509`提供臨時存檔、原數字按鈕與唯讀狀態端點。無效998不改狀態；可見201後三路變身1／EX12／氣力700，506敵HP2950、507體力720、509的FLAG17=24與TFLAG3=0。本次顯示用原catalog，其餘Null且遮蔽文字；只稱人工B04回合邊界，主代理獨立全pytest、真瀏覽器及500後由STATUS收口。

## 外衣199運動／回合（S75／W03）

原生入口：`ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:448–454、696–702`。先完成運動與內衣400，再**無條件**呼叫外衣199；未穿戴時也會RETURN0。一般形態讀CFLAG40／EQUIP99，變身形態讀CFLAG41／EQUIP199；運動只有第一位數為0才清LOCAL1的衣裝遮蔽位元，不改耐久。兩形態四年齡欄25的測試不改產品年齡規則。

`ERB/ゲーム内_戦闘処理/SUBEVENT_BATTLEE.ERB@SUBEVENT_BATTLE_ACTTENTACLESUIT:309–507`由`battle/tentacle_suit.py`手翻：

- 325–342：耐性>0、第四位≠4，且第四位≠3或RAND100≥5，才消耗`7+RAND5+第二位*7`；第三位>0再+2，第四位1／2／3乘0.9／0.8／0.5，最後耐性封0。負數／超限不自行修正。
- 346–355：其餘走既有`SEX_COMEX(0,0,15)`，12項先乘`100+第二位*20`整除100，第四位1／2再乘1.1／1.2。第三位及第四位3不加此倍率。
- 358–460：先地文／口上再判距離0，保留四個指定姿勢，其他改通常；否則男性LOCAL1歸0；其他依TCVARn41階段處理。階段1潤滑門檻500、特徵與旗標變動；階段2／3／≥4各自倍率、污漬／經驗與`NINSIN_HANTEI`參數完整保留。距離0結尾階段=-1，舊-1→1，其餘+1。
- 462–506：清NOWEX後逐索引0–12補正。保留原作LOCAL索引直接作COMMON_PALAM／特徵補正編號，沒有改映射；只有中毒判定使用`index+10−4`。先姿勢、耐性、特徵、性格、中毒、亂數；原正值補正後封最低1，索引≥4封999999，零／負數不套補正。
- 原呼叫者沒有改TARGET。未穿戴RETURN0與函式落尾只寫RESULT0；事件的SEX_COMEX會先寫RESULT0–11，不能把第8格一律當保留。純顯示片段額外CALL不外洩RESULT，借用LOCAL／LOCALS後還原；衣名依317–323在前段取快照，後續口上不重取。

地文`ERB/地の文/MESSAGE_SUBEVENT.ERB@MESSAGE_SUBEVENT_BATTLE_ACTTENTACLESUIT:65–170`沿`run_event_gen`，四段內嵌敘事只抽原PRINT／字型節點；KOJO及妊娠走原生generator。PRINTW沿既有顯示行為，一般WAIT議題仍屬W07。全ERB精確名稱搜尋10筆（含地文／口上標籤），產品入口與直接相依均已核對；不摘錄敘事。

引擎短路：`reference/emuera-1824/Emuera/GameData/Expression/OperatorMethod.cs:524–555`；TIMES截斷：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:893–916`；自然落尾RESULT0：`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`。無新的UNVERIFIED／DEVIATION。

新增142案，定向連同S71／S73／S74共`423 passed, 1 warning in 2.71s`。先紅39案（36個缺實作／3個運動前態漏指定動作，依原479–487修正前態），首輪綠39，再擴完整分支。原生妊娠等待驗四題與無效輸入：先前SEX_COMEX不重跑，後段階段／NOWEX／經驗／RNG待選擇完成才結算。兩路真`run_train`及Web指令998→201→下一選單；catalog測節點／字型／衣名快照。原算式精確值由table測試驗證，整合事件分支只驗後續PALAM_UP扣除後的正值區間，不以Python實測反推expected。

`tmp/s75/browser_fixture.py --mode cost|event`提供臨時存檔、原按鈕、唯讀數值端點與遮蔽輸出。cost預期體氣700、耐性93；event預期stage1／事件經驗1及後續體氣耐性下降；共同敵HP3000、變身1、TARGET1、遠尾格RESULT99=345、先制餘額減1。僅人工回合邊界，主代理獨立全pytest／真瀏覽器／500由STATUS收口，不宣稱自然遭遇或B04／B05整列完成。

## 衣裝購買（S40）

入口 `ERB/インターミッション画面/SHOP.ERB@USERSHOP:267–269`：非遊戲結束模式且FLAG:63=0。
Python 呼叫 `GameSession → clothing_inventory.inventory_gen(purchase=True)`，和持有品模式共用頁面。

- 商品：`ERB/インターミッション画面/SHOP_CLOTH.ERB@LIST_CLOTH_NOTHAVE:584–611`、`@ISCHECK_CLOTH:757–763`；分類範圍內名稱非空、價格正數、ITEM恰為0。名稱與價格直接讀既有CSV資料。
- 操作：同檔 `@SHOW_CLOTH:172–198`；列表／簡易資訊先進說明，單體／目錄再次輸入ID便付款，沒有額外確認。檢查整個篩選後列表，允許手動輸入非當頁商品ID；不在列表的ID不付款、選取位置留下-1（之後切顯示回第0頁），已持有／零價輸入則顯示預期外值。
- 付款：同檔 `@BUY_CLOTH:768–781`；餘額不足不改狀態，足額扣CSV價格並寫ITEM=1；未增加研究／角色／類別條件。詳情的不足金額「買う」顯示為非按鈕，但手動ID輸入仍會走不足訊息。
- 頁碼：同檔 `@SHOW_CLOTH:187–191`；成功後重建未持有清單，若原位置為最後一件，先以前一位置計算頁碼，否則保持原位置；最後一件買完回第0頁。[98]依舊只清篩選。
- 返回：同檔 `@SHOW_CLOTH:76–92`；單體／目錄先回列表，再返回SHOP並留下RESULT:0=1；返回時計算ITEM:100–399的值總和（排除100／200／300），10／30門檻呼叫實績269／274。
- 實績沿用既有 `battle.core.unlock_achievement` 空操作，故不顯示達成訊息、不寫GLOBAL／SAVEGLOBAL；這是既有「全域資料（GLOBAL）」偏離的新增入口，已補記 `bridge/deviations.md`，未擴展實績系統。
- INPUT只改RESULT:0，其他RESULT格與RESULTS保留：`reference/emuera-1824/Emuera/GameProc/Process.cs:249–260`。畫面重繪的 `@SHOW_CLOTH_FOOTER:395` 最後RETURN 1，所以等待下一輸入時RESULT:0=1，包括購買不足後。

新增32項 `tests/test_clothing_purchase.py`：價格邊界、持有值、不可售品、分類、翻頁／末頁購入、篩選、手動非當頁輸入、空列表、RESULT(S)、實績呼叫門檻；實際GameSession購入後返回SHOP，再進衣裝設定裝備購入物品。S39＋S40定向共244項通過。

主代理獨立完整pytest：`2523 passed, 1 warning in 317.79s (0:05:17)`（既有Starlette警告）。

S40標準500局：default246上限＋4標題返回，tokusou250上限；catalog失敗0，逐seed完整結果與S39相同。10個50局前景批次退出碼均0，seed0–249全集及log／JSONL一致；audit與各批log／JSONL／exit保留於`tmp/s40/`。
