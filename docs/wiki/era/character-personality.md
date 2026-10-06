# 個別角色性格與精神素質（S62／W02）

Python：`game/character_personality.py`；共用角色編輯[7]呼叫。與S61的CSTR人格描述是不同選單。
以下ERB路徑相對`source/earGVP/`；不執行敘事情節，只有原作指定的色彩函式呼叫。

## 流程與原作依據

- `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN:259–263`：非固有角色才能進入[7]。開局／招募／醫療／引繼共用既有入口；本次不增加子供入口。
- `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_SEIKAKU.ERB@FIRSTSETTING_CHARA_SEIKAKU:9–38`：每次重繪先把BASE與MAXBASE的0、1、2、10–13還原CSV。找不到性格時抽RAND:19+10，只有抽到28才清600–699。
- 同函式`:39–197`：顯示19種性格的七項基礎補正、六項抗性與口上是否存在，十組精神素質保留按鈕說明。COUNT／排版仍沿W07既有差異，沒有宣稱整個文字引擎已等價。
- 同函式`:198–244`：200且精神素質數≤4才完成；98為有口上的性格亂數、99為全部19種亂數，兩者都不是取消。0–18指定性格，先清10–28；28清600–699。300清精神素質，999先清後抽1–3項。
- 同函式`:245–414`：100–106是七組二擇循環；107依614→615→625→無，108依616→617→618→619→無，109依620→621→622→623→624→無。28非零時拒絕十組修改；素質上限計算600–699所有正值，不只畫面具名項。
- 同函式`:419–444`：確認才套用性格補正並同步MAXBASE，不累乘上次值。女性且CSTR4空時，24設CFLAG8=20、25設11；其他性格保留原值。最後重算部位結界；TARGET不改。
- `ERB/ヒロイン関連/CHARA_SEIKAKU.ERB@SHOW_SEIKAKUHOSEI:1026–1050`、`@SHOW_RESISTSEX:1056–1160`：共用既有數值規則與抗性顯示，後者新增compact模式供本選單省略欄名及換行，原主頁預設輸出不變。

## 亂數與口上色彩

- `ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_STATUS_TALENT_SEIKAKU:1237–1331`：少於1項或28正值直接返回，最多10項。八組RAND:2，再以連續RAND:4／3／2與RAND:6／5／4／3／2選其餘兩組；不能改成各一次等機率抽樣，否則亂數序列不同。
- 同函式`:1319–1331`用共用RANDCHOOSE池抽出／移除，直到已持有素質達指定數量。池與注入RNG的副作用均保留；此函式本身不清既有素質，999的呼叫端才清。
- `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_SEIKAKU.ERB@SHOW_KOJO_EXIST:446–454`及`@RAND_CHOOSE_KOJO_SEIKAKU:457–481`：顯示／98都實際執行`KOJO_{オトコ}_COLOR_{性格}`，不是只查catalog索引。98排除目前非零性格；存在卻執行失敗會明確錯誤，不能當沒有口上。正常色函式可修改原作內部變數，例如S54已查證的KOJO_0_COLOR_16。
- 98候選空集合（含只有目前性格可用）照原作RAND:0停止，不新增後備性格。正常原作catalog的操作已有實測；Null或人造catalog可用定向案例驗此邊界。

## 引擎與顯示邊界

- CSVBASE讀角色模板的Maxbase，未定義欄位為0、缺角色是錯誤：`reference/emuera-1824/Emuera/GameData/Variable/VariableEvaluator.cs:1383–1418`。
- TRYCCALLFORM執行函式，只有缺標籤才走CATCH：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:2297–2332`。
- RAND最大值≤0錯誤：`reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:960–970`。
- INPUT只寫RESULT0，函式自然結束寫0：`reference/emuera-1824/Emuera/GameProc/Process.cs:249–252`、`Process.ScriptProc.cs:61–67`；不清RESULT其他格／RESULTS。
- 按鈕value及title：`reference/emuera-1824/Emuera/GameView/HtmlManager.cs:853–916`。手翻選單直接建立結構化按鈕與title，由Jinja自動跳脫並放進Web按鈕屬性；未擴充ERB或HTML解譯器。
- 固定選單文字及十組標籤由`tools/extract_character_personality.py`抽到`character_personality_text.py`；素質名讀CSV，說明沿既有`talent_info`。

## 驗收

- 新增54案，從缺模組紅測試起步；tooltip前端亦先驗出缺title再補。與既有角色／身體／文字定向合計`142 passed, 1 warning in 7.58s`。
- 覆蓋19種性格、十組全部循環、28連動、五項拒絕／四項確認、CSV還原／補正／結界、結果殘值、亂數抽數與共享池、98空集合／執行失敗，以及真GameSession返回／重入／SHOP。expected取ERB分支、CSV設定及引擎，沒有由Python產物反推。
- 父代理另做全pytest／500／真瀏覽器，最終結果見STATUS。本頁不把API通過當成真瀏覽器通過。
- `python -X utf8 tmp/s62/browser_fixture.py --port 8778`：全新25歲人工定義、臨時存檔、Null敘事；僅色彩函式委派真catalog，供98及其狀態副作用。只讀`/fixture/state`回傳年齡、性格／素質數值、BASE／MAXBASE與失敗計數。
- 主代理真瀏覽器通過：7→0→300→100／101／102／103／106→200（五項仍留頁）→300→18→100／999（不增精神素質）→99→98→100兩次／101／102／106（四項）→200→7→200→99→1000→1（SHOP）。確認／重入的數值端點完整相同，體力1200未重複加成，年齡25、未設變身年齡格為原作-1；catalog失敗0、瀏覽器錯誤0。
- 真瀏覽器核對按鈕title包含原文說明；截圖`tmp/s62/personality-verified.jpg`，數值`browser-first-confirm.json`、`browser-reentry.json`、`browser-shop.json`。人工資料與Null敘事不代表自然完整通關，其他W02子選單仍未完成。
