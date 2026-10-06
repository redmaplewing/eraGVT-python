# 共用文字、GDI 計量與重繪（S87）

## 原設定與實作邊界

`source/earGVP/emuera.config:11–23` 指定 WINAPI、視窗寬760、PRINTC長25、ＭＳ ゴシック14px、行高15px；`Config/Config.cs:169–172` 在WINAPI下不扣邊界位移。以下引擎路徑均相對 `reference/emuera-1824/Emuera/`。

`text/metrics.py` 用Windows既有GDI+建立Pixel字型及LOGFONT，再呼叫GDI `GetTabbedTextExtentW`；依`Config/Config.cs:186–208`、`GameView/StringMeasure.cs:43–72`、`_Library/GDI.cs:331–347`，傳入UTF-16長度與預設tab stop。每次建立的DC／HFONT均在finally還原／釋放，GDI+ token保留到程序結束；256份LOGFONT資料及8192組文字寬度有界快取，不存未釋放的字型handle，跨執行緒加鎖。

本機已安裝MS Gothic字型家族。獨立C# `System.Drawing.Font.ToHfont`＋原GDI呼叫對照四字型（ＭＳ ゴシック／ＭＳ Ｐゴシック／Arial／不存在字型）、四種粗斜體組合、五種文字（半形／全形／混合／tab），80案均與ctypes一致。例：普通ＭＳ ゴシック26空白182px、54個`―`756px；不存在字型由System.Drawing回落Microsoft Sans Serif，ctypes用GDI+ GenericSansSerif得到相同結果。證據 `tmp/s87/gdi-oracle.ps1`／`gdi-oracle.json`；此核對不等於瀏覽器逐像素比較。

非Windows不載入GDI，沿用原有PRINTLC補白／分隔線及不折行呈現；`@F:`亦保留既有不套用行為，未宣稱等價。Web用解析後字型家族，並把每段GDI advance設為CSS寬度；原字型缺失時依本機System.Drawing回落，沒有安裝字型或改系統設定。瀏覽器字形的光柵化／反鋸齒與原GDI未逐像素比對，仍保留既有顯示差異範圍，不能視為使用者已批准。

## PRINTLC、字型與區切線

- `GameView/EmueraConsole.Print.cs:363–425`：PRINTLC先依cp932位元組數補到26，再用目前字型／粗斜體計量，超過預設字型26空白寬時逐一移除尾空白；原文字超寬不裁掉。
- `GameView/PrintStringBuffer.cs:63–89`：PRINTLC欄位前後均為按鈕判定邊界；前後PRINT文字不併成同一個可點選項。
- catalog的SETFONT現呼叫共用`TextOutput.set_font`，空字串／省略恢復原設定；依`GameProc/Process.ScriptProc.cs:486–492`與`EmueraConsole.Print.cs:60`。FONTREGULAR同時取消粗斜體，樣式和待輸出段落仍由既有catalog交易一起回復。
- `ERB/汎用関数/TagSetText.ERB@PRINT_TAGSET_TEXT:299–318`保存呼叫前字型；`@PRINT_TAGSET_TEXT_MAIN:403–406`先CHKFONT才套用。Windows的`@F:`現在照此套用與還原。
- 原作唯一DRAWLINEFORM為`ERB/地の文/MESSAGE_WindowLibrary_VideoHostSite.ERB@MESSAGE_SEX_VIDEO_SITE_Window:1335`的`―`。`EmueraConsole.Print.cs:543–560`以預設字型計量，重複到超過760再逐字刪尾至不超過。
- `EmueraConsole.Print.cs:517–533`印線時只暫改Regular、不換字型名；`Process.ScriptProc.cs:154–172`在原緩衝後印線再換行，並未先Flush。因此有前文時屬同一論理行，Web可折成數個實體行。

## 論理行、HTML與暫時行

`GameData/Variable/VariableToken.cs:1529–1538`的LINECOUNT直接讀Console.LineCount，後者在`EmueraConsole.Print.cs:103`回傳logicalLineCount。`PrintStringBuffer.cs:176–245`只有第一個實體行標記IsLogicalLine，其餘自動折行或HTML的br均是同組續行；`EmueraConsole.Print.cs:156–176`的CLEARLINE反覆刪最後實體行，直到刪足指定數目的論理行。**CLEARLINE本來就不清未換行緩衝**，`Instraction.Child.cs:488–500`直接deleteLine，沒有PrintFlush；舊deviations這一句誤列，現已更正。

TextOutput保留論理行及HTML續行標記；Web `text/layout.py`按GDI寬度生成實體行，不回寫遊戲狀態。原`ButtonWrap=YES`／`CompatiLinefeedAs1739=NO`（config:38、56）下，放不下的按鈕整個移到下一行，超過整行的按鈕及一般文字才切段；nobr不折行。CLEARLINE刪整組，重繪不會留舊選項，也不靠清空全部敘事歷史。

真角色強化的重繪另依 `ERB/インターミッション画面/SHOP_CHARA_POWERUP.ERB@CHARA_POWERUP:62、92–346` 核對：面板固定25個論理行，有部位結界時另加1＋結界數；`INPUT` 回顯依 `EmueraConsole.cs:733–734` 再添一行，故原 `CLEARLINE 26` 加結界行恰好清掉面板及輸入，不刪此前歷史。此呼叫端已局部補上選角／操作的數值回顯，共用 `input_number` 不變。`ERB/汎用関数/コモン関数.ERB@CHARA_LIST:305–350` 沒有清除列表，角色列表留在歷史符合原文；本修正不全面刪除舊文字。

HTML保留原實用的font color、nonbutton title、br、nobr、shape space，並接數字button／title（`HtmlManager.cs:853–916`）；原呼叫例如`ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_SEIKAKU.ERB@FIRSTSETTING_CHARA_SEIKAKU:66–85`。未知標記仍明確停止，不將任意HTML注入瀏覽器。space的文字本來是空字串，寬為14×param/100，再依`ConsoleShapePart.cs:157–173`截整並傳遞餘數；`PrintStringBuffer.cs:400`初始餘數為0.5，故兩個75依序寬11／10px；150為21px，不再冒充三個空白。

`EmueraConsole.Print.cs:110–114、201–204、295–308`的暫時行只在下一個完成行加入時被取代，PRINT尚未換行時仍保留。標題／存檔選槽／覆寫／讀檔選槽的無效值已照`Process.SystemProc.cs:223–225、882–884、913–915、966–968`改暫時行；系統輸入依`EmueraConsole.cs:701–735`先回顯原字串，再刪掉該輸入行，不再誤刪最後一個選項。數字解析、RESULT(S)、RNG及存讀規則不變；一般遊戲INPUT的既有局部回顯不在此擴張。

## 驗證與尚未完成

新增18案：欄位按鈕邊界、原字型計量、CLEARLINE與部分緩衝、HTML續行分組、暫時行、SETFONT／還原、DRAWLINEFORM、空白幾何／數字按鈕、系統無效值與原字串回顯、Web折行、catalog交易及模板邊界。來源導出案例初始9失敗／3通過；原本正確的CLEARLINE三案直接通過。定向830案通過，後補交易／模板案與narration共98案通過，最終受影響共用輸入／Web組67案通過。父全pytest與真瀏覽器結果由STATUS／S87規格收口。真瀏覽器發現角色強化少了INPUT回顯而每次誤刪前文一行，修正追加4個來源導出案（0／1／2／4種結界）先紅後綠；預約／清除／提交／角色切換均核對歷史不變與單一面板，相關141案通過。

真瀏覽器fixture為`tmp/s87/browser_fixture.py`三路：中性catalog混合字型／長頁／重繪、真CHARA_POWERUP預約／清除／確認、真系統無效輸入／返回。全部全新25歲人工資料；產品年齡規則不變。這是局部顯示成果，不是W07結包，依分級驗證不跑500。COUNT、尚未遷移WAIT、catalog失敗及圖樣仍留W07；既有跨平台／字形像素差異保留，沒有新增規則裁決。
