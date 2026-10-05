# 一般身體與外貌編輯（W02，S61部分成果）

來源：`ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@SIZE_SETTING:2–2142`；原生實作`game/body_editor.py`。
已接共用角色編輯[6]與狀態PAGE5[20]，開局／招募／醫療／引繼原有共用呼叫者均可抵達；子供原作獨立流程保留原範圍。
這不是完整SIZE_SETTING：2／12、3／13、46、70–76、80–86仍明確停止；TS與特殊裝備生命週期仍W03。

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

## 主代理最終驗收

- 全pytest：`3942 passed, 1 warning in 250.70s (0:04:10)`；共用與狀態兩入口25歲真瀏覽器均返回SHOP，細節見body-editor wiki。
- 正式500：default247上限／3回標題、tokusou250上限；catalog失敗0、fixture停止0；十批退出0，seed／log／JSONL／參數核對通過。與S60同一人工資料的500筆完整JSON逐seed一致。
- 新基線與核對結果：`tmp/s61/adult25-v1/`及`audit.json`；舊基線`tmp/s60/adult25-v1/`。source/reference未動，無新增未決事項。
- S61一般身體／外貌成果完成；SIZE_SETTING其餘操作、子供獨立流程與W02其他子選單仍未完成，既有W07顯示差異保留。
