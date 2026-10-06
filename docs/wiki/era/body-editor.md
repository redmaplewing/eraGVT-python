# 一般身體與外貌編輯（W02，S61／S67／S69）

來源：`ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING:2–2142`；原生實作`game/body_editor.py`。
已接共用角色編輯[6]與狀態PAGE5[20]，開局／招募／醫療／引繼原有共用呼叫者均可抵達；S69子供原作獨立收尾亦接同一編輯器。
S67已接2／12、3／13、46、70–76、80–86，SIZE_SETTING選項分派不再有未移植停止。S69子供獨立身體入口已接通；尾段人工驗收不代表完整出生／加入流程。TS與特殊裝備生命週期仍W03，W07排版差異仍保留。

## 已接操作與依據

- :21–55保存TARGET、轉換舊色彩／年齡欄位、建立兩形態工作值；另一形態無差異時以-1表示。
- :1461–1503年齡輸入與九項生成參數界限；產品原有年齡範圍不改，驗收使用全新25歲人工資料。
- :1506–1531身高型態、:1653–1670一般外貌、:1690–1710形態切換；保留原作依NO與形態的條件及寫回。
- :1712–1715子頁返回不回滾已改欄位；整頁只有99確認。:1734–1749人格空格前移與原有狀態整理照抄，不另訂規則。
- :1720–1729身體／髮型重抽；:1752–1759前後髮型及目光；:1761–1823色盤、預設色及兩形態色彩複製。
- :1861–1888人格文字／鎖定／清除／重抽；`@SET_PERSONALITY:2230–2282`含手輸、空字重試、取消與重抽。
- :2110–2142依工作值寫回BASE／MAXBASE，恢復TARGET；函式終端只清RESULT:0，見`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`。
- 狀態入口：`ERB/ヒロイン関連/ステータス画面/SHOW_STATUS_CHARA_SELECT_PAGE5.ERB@CMD_STATUS_CHARA_SELECT_PAGE5:73–79`先生成初始數值，再進編輯；99才返回狀態頁。

## 已查明而保留的細節

- `@SIZE_SETTING:1458`令DISPLAY_FLAG=-1，bit2／bit3均為1；一般操作不走:2106的清頁，會保留歷史列，不能把舊按鈕當新輸入模式。
- :97–130檢查數值0..9999；CAL_VAR在本函式沒有寫入非零範圍，只有:1837–1851清零。負數資料依原作跑到5000次，不自行略過或改產物。
- :341–344／378–380的TOP_UNDER／CUP_SIZE顯示也寫共用RESULT:1與RESULTS；不能只保留GENERATE的成長曲線殘值。
- :1449的STRLENS按語系位元組長度，不是Unicode字數：`reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:2095–2107`→`_Library/LangManager.cs:17–20`。
- 人格重抽比較`"CSTR:ARG:41"`等字面值；候選頁:2241／2244的`"%CSTR...%"`也不是格式插值，所以重複候選照原作保留。一般引號與`@"..."`的差別見`reference/emuera-1824/Emuera/Sub/LexicalAnalyzer.cs:917–936`，不推測修正作者意圖。

## S67一般操作

以下來源皆為`ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING`：

- :1533–1606接2／12性別循環，NO=0才寫入；先將190–193及避妊結界每個非零項清除並各退50修練P，兩形態相依欄位依原順序處理。
- :1608–1651接3／13體型循環，NO=0且該形態非男性才寫入。另一形態到末端時:1619直接設差值-2，沒有減去通常形態值；保留原行為，未自行修正。
- :810–828／1891–1902接46配件0→1→2→3→0；ISGIRLY才顯示，固有標記只限制寫入，不隱藏按鈕；NO非零不等於固有標記。判定依`ERB/汎用関数/SEX_GENDER.ERB@ISGIRLY:28–37`。
- :2049–2051的85原文明示未使用，接受手輸而不改值；沒有新增按鈕或設定。
- :725–748／2053–2102接86初期狀態，GLOBAL／模式、SOLO略3與所有副作用和`ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB@CHARA_MAKE_MAIN:150–198`逐條相同，重用S66循環。顯示GLOBAL門檻不額外變成手輸拒絕規則；離開既有3狀態仍減經驗，無下限修正。
- :1717–1718保留原分派優先序：固定角色手輸2未走性別，落入實年齡模式；數字子頁先攔輸入，一般子頁直接操作後取消不回滾。原文:823／747用PRINTFORM，46／86在數字模式仍有按鈕，輸入由當時模式解讀。
- :2只宣告ARG一個參數，:726的ARG:1沒有寫入。精確搜尋SIZE_SETTING共4處（1宣告、3個單參數CALL），沒有ARG@SIZE_SETTING跨函式寫入；所以不能捏造鎖定參數。ARG按函式建立，預設零：`reference/emuera-1824/Emuera/GameData/Variable/VariableData.cs:330–331`、`reference/emuera-1824/Emuera/GameData/Variable/VariableLocal.cs:23–29、36–70`、`reference/emuera-1824/Emuera/GameData/Variable/VariableToken.cs:1726–1738`；多傳參數會拒絕：`reference/emuera-1824/Emuera/GameProc/Process.CalledFunction.cs:154–159`。

- :1904–1978的70–74直接循環數值：通常形態正向／負向兩欄0→正向→負向→0；男性且TS>0時70／72改另一形態差值0→1→-1→0，無TS則不變。71／73／74不限制性別。沒有年齡判斷、經驗生成或敘事呼叫。
- :1979–1999的75／80切換零與非零；76是未熟欄位0→1→2→0，其他值歸0。:709–721顯示未熟／不妊／人工子宮；此局部分派沒有未成年專用生成，因此一併接通，保留原值與標籤。
- :2000–2028的81按通常／變身形態與能力精確切換0／3；只有關閉分支且固有角色、初期經驗鎖均0時清除既有經驗。:2030–2048的82／83是旗標切換，84關閉時另清共生；均無生成敘事或年齡條件。
- :482–724的70–76、80–84使用PRINTFORM，數字模式仍顯示按鈕但由輸入模式先解讀；GLOBAL:244／245／253／255只控制81／82／83／84顯示，不限制手輸。81／82顯示另看女性或男性TS>0，不查變身能力；寫入81則精確查能力==1。NO與固有標記不額外禁止這組操作。

範圍修正：第一輪將70–76、80–84與[8]經歷生成一併列為阻塞，範圍過廣。以上逐分支查證已更正並實作；[8]直接按未成年年齡／學生類型生成性經驗的既有範圍阻塞仍只適用[8]，見[角色編輯](character-editor.md)。沿用既有來源查證，未重查、未改產品年齡規則、未新增成人限制。驗收資料全為新建25歲人工角色。

S67第一輪60新案，同階段補完另85案（先紅85 failed，再綠）；移除1項已過時的70停止測試。身體三檔定向`181 passed, 1 warning in 52.00s`，涵蓋兩形態、固定／固有角色、GLOBAL／SOLO、隱藏手輸、數字攔截、取消／確認／重入、RESULT尾值／TARGET／RNG、非目標角色不變。補完兩個真Web入口的70–84操作後另驗`60 passed, 1 warning in 10.03s`；警告為既有Starlette/httpx棄用提示。
人工瀏覽器fixture：`python -X utf8 tmp/s67/browser_fixture.py --entry editor --scenario unlocked --port 8781`，狀態入口用`--entry status`，另可選locked／fixed／unique／male。資料為全新fresh-adult-25-v1，Null敘事、臨時存檔，每次HTTP前後檢查年齡；為測兩形態明確配置另一形態25歲，關閉時保留原有-1哨兵。`/fixture/state`僅一般數值，形態尺寸待99後按原作寫回。
editor步驟：6進入，2／12測性別循環、3／13測體型、46測配件、86循環到0；5→46→5測子頁取消保留配件；20關閉／20開啟，99→6確認重入，再99→99→1000→1到SHOP。status為20進入，99返回，20重入，99→999到SHOP。fixed手輸2後只輸25；unique的46顯示但不改值；locked不顯示86且初態0手輸86不變。
補完步驟：unlocked人工GLOBAL另開244／245／253／255，70–84欄位從0開始；70–74各按三次回0，75／80／82／83／84各按兩次回0，76按三次回0，女性且變身能力1／TS0時81按四次回兩形態0。可在5子頁按75後5取消，99確認後重入核對保留。locked不顯示81–84但手輸可切換；male且TS0不顯示70／72／81／82，70／72手輸不變，82仍可手輸。`/fixture/state`新增traits與cleanup_counter純數值；不產生經歷或敘事。
主代理全pytest4365、25歲真瀏覽器雙入口及限制／隱藏手輸驗收通過；正式500完整JSON逐seed與S66一致，catalog／fixture失敗0。證據tmp/s67/browser-*.json、body-settings-complete.jpg與adult25-v1/audit.json；無新增UNVERIFIED／DEVIATION，既有W07排版差異維持。

## S69 子供實際收尾入口

- `ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD:1075–1107`由`child.add_child_finish(ctx, parent)`實作，ADD_CHILD在原位置呼叫。CFLAG34為0才執行`ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE.ERB@GENERATE_BODYLINE:475–540`；先RAND535627332240，再60次RAND726（滿9另重抽），之後進SIZE_SETTING等待真實輸入。非零曲線不抽數。
- `ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD:1083–1092`先恢復親、清親CFLAG224、恢復隊員、CHECK_ALL_RELATION。`ERB/ヒロイン関連/RECOVER_TO_PARTY.ERB@RECOVER_TO_PARTY:3–23`保持原有PARTY_MAX判斷。CHILDCARE優先於CFLAG22分支；:1093–1106原清理保留，其純狀態案同樣以25歲前態驗證，不新增敘事內容。一般分支均不符合時直接返回，不清224或更新關係。
- `ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING:2141`還原的是進入編輯時TARGET；本尾段已指向新角色，所以確認後仍為2，不還原成親1。外層`ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@GROW_HANTEI:27`原還原另有其責任，未移入尾段。
- `ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD:1107`的RETURN只清RESULT0，保留其他結果格；依據`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1997–2023`。身體顯示原本寫入的RESULT1／RESULTS0仍保留；關係判定沿`ERB/ヒロイン関連/CHARA_RELATION.ERB@CHECK_ALL_RELATION:576–588、931–949`。
- 新12案先紅後綠，再補原第三分支及IF優先序2案，`14 passed, 1 warning in 0.75s`。新案涵蓋真實等待、一般外貌／色彩／人格文字、空字返回、99確認、一般／育兒／原第三分支、復歸次序、關係、TARGET／RESULT尾值、生成RNG及Web文字／數字／重送。凍結版六檔定向`243 passed, 1 warning in 63.74s (0:01:03)`（尾段、一人稱、身體編輯三檔與狀態頁）；警告為既有Starlette/httpx提示。主代理全pytest`4394 passed, 1 warning in 176.82s (0:02:56)`；真瀏覽器ordinary與childcare+unset-body均通過，確認一般編輯、空字返回、原復歸／關係、TARGET／RESULT尾格、RNG及25歲，console錯誤0。正式500完整JSON與S68逐seed一致：default247上限／3回標題，tokusou250上限，catalog／fixture失敗0。證據tmp/s69/browser-*.json、body-tail-childcare.jpg及adult25-v1/audit.json。
- 重現：`python -X utf8 tmp/s69/browser_fixture.py --branch ordinary --port 8783`；育兒尾段改`--branch childcare`，另可加`--unset-body`驗原曲線初始化。fresh-adult-25-v1、Null敘事、臨時存檔；直接呼叫真實產品尾段，沒有替換產品generator或改動既存角色年齡。
- 代表操作4→601→60→20→「沉穩」→99；人格輸入空字返回候選，再20重輸可驗取消。`/fixture/state`只讀25歲四格、一般外貌／色彩／人格、TARGET／RESULT(S)、RNG剩餘及復歸／關係數值。ordinary完成仍保留親224=9、隊員狀態11且不加關係；childcare完成兩者狀態0／party1、親224=0與雙向親子bit20。尾段完成後fixture拒絕POST，不繼續外層流程。
- 此成果只稱**ADD_CHILD尾段函式邊界驗收**，不是完整子供加入、自然流程、B05整列或W02完成；不執行前段固定年齡生成，不事後改齡，不重新分類S67已查證的一般欄位。無新增UNVERIFIED／DEVIATION；既有[8]具體範圍阻塞與W07顯示差異維持。

## 色盤

`ERB/汎用関数/COLOR_TABLE.ERB@COLOR_TABLE:2–158`保留32×32選色、三軸、軸色與32級明度、確認及取消；輸入採原作公式，包含格子顯示與被選數值不同的原有一格差。
軸、MODE、選取RGB與明度為static；每次只重設軸色8。原生存於GameState.temp.locals，程序內各session隔離，重設／讀檔清除，不存JSON。
依據：`reference/emuera-1824/Emuera/GameData/Variable/VariableToken.cs:1846–1865`、`VariableData.cs:514–520`；不能用Python模組全域。
確認回RESULT:0=1；取消回0..3全-1。重新進入保留上次MODE，且原文:86–88先檢查共用RESULT:0殘值。
一般頁兩形態改為依序列出與色盤實際行數清頁沿既有W07顯示偏離，已回填deviations，未把W07結案。

## 驗收

- 子代理定向：`97 passed, 1 warning in 2.31s`（新37案、角色編輯與狀態頁），警告為既有Starlette/httpx提示。
- 固定expected由ERB推導，例如TOP_UNDER影響值190、軸2選10000半明度為(4,127,4)；不由Python實作反推。
- 本機人工fixture：`python -X utf8 tmp/s61/browser_fixture.py --entry editor --port 8776`；狀態入口改`--entry status --port 8777`。它們走真實GameSession，NullNarration、臨時存檔、每次HTTP前後檢查25歲，-1僅為另一形態未設定哨兵。
- editor開始在個別角色編輯：6進身體，50→25驗實年齡，5→100→5驗髮型；6→601→600→10000→0驗色盤，600→99驗取消，6→99返回；重入後99→99→1000→1到SHOP。
- status開始在人工未設定身體的第五頁：20進編輯，50→25→99返回，再999回SHOP。
- `/fixture/state`只回一般數值。Web API冒煙已通過；父代理全pytest、500局與真瀏覽器的最終結果以STATUS為準，不把API當瀏覽器。

- 父獨立全pytest：`3942 passed, 1 warning in 250.70s (0:04:10)`；產品定向凍結後執行。
- 父真瀏覽器雙入口通過：共用[6]編輯25歲、前髮改ナチュラル、預設紅色及色盤(8,8,255)確認／取消、人格手輸「沉穩」與鎖定，99確認後重入保留；再完成製作到SHOP。狀態PAGE5[20]維持25歲、身高型態改長身，顯示153.6→166.9cm、確認後回SHOP；每次HTTP檢查年齡，最終四年齡格全25。兩頁console無error／warn。
- 瀏覽器結果`tmp/s61/browser-results.json`、重入畫面`tmp/s61/body-editor-verified.jpg`；伺服器與驗收頁均已關閉。這些為人工前態／NullNarration，一般互動驗收不代表自然完整通關。

## S61主代理驗收

- 全pytest：`3942 passed, 1 warning in 250.70s (0:04:10)`；共用與狀態兩入口25歲真瀏覽器均返回SHOP，細節見body-editor wiki。
- 正式500：default247上限／3回標題、tokusou250上限；catalog失敗0、fixture停止0；十批退出0，seed／log／JSONL／參數核對通過。與S60同一人工資料的500筆完整JSON逐seed一致。
- 新基線與核對結果：`tmp/s61/adult25-v1/`及`audit.json`；舊基線`tmp/s60/adult25-v1/`。source/reference未動，無新增未決事項。
- S61一般身體／外貌成果完成；SIZE_SETTING其餘操作、子供獨立流程與W02其他子選單仍未完成，既有W07顯示差異保留。
