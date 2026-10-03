# 子供與變身後命名（S35）

路徑除引擎外相對 `source/earGVP/`。本階段不新增遊戲內容，只接通原文已有命名。

## 呼叫與輸入

- `ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@BIRTH_DAUGHTER_TENTACLE_ORIGIN`:167–263、`@ADD_CHILD`:324–503：
  手輸入空字串重新等待；空白不去除；姓名確認「いいえ」回到手動／隨機選擇。姓氏組合與隨機語言沿既有原文路徑。
- `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_TRANSFORMATION.ERB@FIRSTSETTING_CHARA_TRANSAFTERNAME`:64–221：
  正式名、全隨機20組、角色名／冠名與隨機詞組合、既有[0]/[5]/[6]；不改原作接受隱藏[4]與[7]/[8]的範圍判定。
- 同檔 `@FIRSTSETTING_CHARA_TRANSAFTERCALLNAME`:226–294、`@FIRSTSETTING_CHARA_TRANSCALL`:298–348、
  `@FIRSTSETTING_CHARA_NANORI`:353–445，以及 `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_CALLNAME`:1072–1101
  的手輸入均已接通，空字串依各函式原文重新等待。
- 正式名手輸入：舊名非空才將「999」解釋為保持舊名；舊名空則名稱就是「999」。變身後呼び名則不論舊值是否空都把999當保持舊值。
- 實際呼叫：`ERB/汎用関数/コモン関数.ERB@SENGIUP`:782–785（命名後CSTR:0非空才設定呼び名）、
  `ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD`:671、
  `ERB/ヒロイン関連/ステータス画面/SHOW_STATUS_CHARA_SELECT_PAGE1.ERB@SHOW_STATUS_CHARA_SELECT_PAGE1`:224。
  全域精確CALL搜尋共4處，另1處是尚未整體移植的 `FIRSTSETTING_CHARA.ERB`:277；不擴張至完整キャラメイク。
- Web沿既有generator和catalog巢狀input_fn傳遞 `TextInputRequest`；畫面回傳input_kind，HTML原生form切換text/number。
  text沒有required、Form空值預設為空字串，API文字值保持字串（例如0007），數字選單才轉int；JS仍只負責捲動與聚焦。
  舊影片／口上INPUTS亦共用此通道，S11/S14整數限制已消除。

## 隨機候選與狀態

`ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_RANDOMNAMING.ERB` 手翻於 `game.naming`，候選文字直接讀現有CSV STR：

| 函式／原文 | 對應行為 |
| --- | --- |
| `@FIRSTSETTING_RANDOMNAMING_ALL`:129–219 | 每列先上後下；genre8先RAND8，然後RAND50+500+100*genre，空字串只重抽RAND50 |
| 同函式:221–273 | 20候選；keep列跳過重抽與反轉；統一上/下句跳過固定半的RAND；重抽/genre選擇清固定編號但不清keep |
| 同函式:3–17 | 每次入口只重設genre為8；keep與固定編號為static #DIM，跨呼叫保留 |
| `@FIRSTSETTING_RANDOMNAMING`:278–303 | RETURN genre,選擇結果；99返回99,0，不清RESULTS |
| `@FIRSTSETTING_RANDOMNAMING_SELECT`:310–447 | 800/801只改順序不重抽，LOCAL:21跨呼叫保留；選定寫RESULTS與CSTR:202 |

- 組合確認「いいえ」恢復入口備份的CSTR:201/202再選；下一次候選選定只覆寫202，201保持舊備份（原文:155–158／189–192）。
- 組合genre99回傳99,0，呼叫端仍確認目前RESULTS；入口已清RESULTS，故第一次返回可確認空字串。不能自行改成直接取消。
- 全隨機99只在genre畫面有效；返回正式命名後執行裸RETURN，RESULT:0=0，名稱不改但201/202已在入口清空。
- `ERB/汎用関数/PRINT_LINE.ERB@LB`:12–18是RETURN RESULT，不能當成一般函式終端清零。
- DA共用二維陣列加入存檔；格式升v3、v2補空DA，v1仍先升v2；RESULTS與static暫存不存檔。

## 引擎查證（reference/emuera-1824/Emuera/）

| 事項 | 原始碼 |
| --- | --- |
| INPUTS無預設、回傳字串，不trim | `GameProc/Function/Instraction.Child.cs`:642–667；`GameView/EmueraConsole.cs`:722–733 |
| INPUTS僅寫RESULTS:0；INPUT僅寫RESULT:0 | `GameProc/Process.cs`:249–260 |
| 裸RETURN與一般函式終端只寫RESULT:0=0 | `GameProc/Function/Instraction.Child.cs`:2006–2023；`GameProc/Process.ScriptProc.cs`:61–67 |
| #DIM預設static | `GameProc/UserDefinedVariable.cs`:27 |
| LOCAL陣列保留；呼叫只更新引數，不清LOCAL | `GameData/Variable/VariableToken.cs`:1712–1737；`GameProc/Process.State.cs`:456–483 |
| DA為SAVE_EXTENDED二維整數 | `GameData/Variable/VariableCode.cs`:182；`VariableToken.cs`:34–39；`VariableData.cs`:723–727 |

測試先以7個既有停止點得到紅燈；最終36個命名case（包含原7個）＋1個子供實際續行case，共新增37個。
既有SENGIUP與子供停止測試改驗證續行。
測試涵蓋空字串／空白／999／數字字串、RNG順序與重抽、static狀態、取消與重選、存讀檔及v2 migration、
真實SHOP狀態入口、Web form/API與catalog兩種既有等待機制。無新增UNVERIFIED／DEVIATION。
