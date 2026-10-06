# 戰鬥側事件（S80／W05）

狀態邏輯在`game/battle/func.py@act_limit`與`game/battle/side_events.py`手翻；`source_check.py`勝利與`palam.py`的JUMP共用generator。顯示只引用既有catalog行號片段，沒有複製敘事字串。

## 觀眾妨礙

`ERB/ゲーム内_戦闘処理/COMMON_BATTLE_FUNC.ERB@ACT_LIMIT:196–291`：先處理既有素質／妊娠限制，才檢查`FLAG72>0 && FLAG70>0 && TFLAG30>2 && TCVARn0==3`。只符合時抽一次`RAND100`，小於11回1；非空中先呼叫距離顯示，再顯示284–287行。空中位元1成立仍回1，保留狀態、不著地、不新增疲勞。

原作279註解與281回傳矛盾，見[未決](../bridge/unresolved.md)；沒有更改原執行結果。`ERB/ゲーム内_戦闘処理/戦闘コマンド(ヒロイン)/COMF3.ERB@COM3:5–10、21–31`確認回1立即取消攻擊，先於空中旗標與連續距離遞增；Python共用`com_attack`一致。非命中繼續既有刻印限制，最後回0。

可達性：`ERB/ゲーム内_イベント発生/戦闘イベント.ERB@PERFORM_CHEERS_FIRST_HANTEI:57–84`以觀眾人數、RAND100寫入FLAG72；`ERB/ゲーム内_戦闘処理/戦闘コマンド(ヒロイン)/COMF3.ERB@COM3:21–28`同距離持續累加TFLAG30。因此不是需要擅自開啟的停用分支。

## 返血

`ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:136–165`：普通BOSS勝利後，先清敵方旗標再呼叫`SUPART_BLOOD`，不是末王／市民／雜魚分支。
`ERB/ゲーム内_戦闘処理/SUPART_BLOOD.ERB@SUPART_BLOOD:1–177`只在balance4啟用且FLAG11>0執行。SCREEN3只控制5–6或8–9的等待形式，不改數值。

| 分支 | 原文行 | 狀態結果 |
|---|---|---|
| 1–4部位未敏感 | 59–64 | TALENT[2×敵編號+98]加10，後一格減10 |
| 已敏感、ABL低於5 | 66–69 | 對應JUEL加25421 |
| 已敏感、ABL至少5、進階TALENT為0 | 71–81 | TALENT[敵編號+152]加10，再派發原地文 |
| 其餘 | 83–86 | 對應NOWEX設2 |
| 敵編號5 | 88–97 | ABL15加3，上限5 |
| 敵編號6 | 98–106 | ABL20加2，上限5 |
| 敵編號7 | 107–118 | ABL14加3、ABL21加2，各上限5 |

編號2的優先分支16–57：變身TS且變身中，按目前女性／男性分別呼叫既有`TS_MtoF`／`TS_FtoM`；否則目前男性且通常形態男性呼叫`TS_NORMAL`。全部沿原生數字選單等待，不代答。其他編號不進TS。
123–174依C/V/A/B順序讀NOWEX原殘值，值1／2派發一般／強事件；不清NOWEX，也不額外增加EX。各分支最後176呼叫既有`GET_STATE_ABLUP`。關閉、敵編號0或負數不耗亂數。

## 失去角色發現

`ERB/地の文/MESSAGE_BATTLE.ERB@MESSAGE_BATTLE_END_WIN:1648–1652`在maniac14啟用時仍抽`RAND1`，再呼叫發現。Python勝利鏈保留此抽數，末王亦可進入；關閉時短路不抽。
`ERB/地の文/MESSAGE_BATTLE.ERB@MESSAGE_BATTLE_END_RESCUE_DEADNUM:1739–1810`清RANDCHOOSE候選，從索引1到CHARANUM前一個收集`CFLAG0==9 && TALENT苗床化!=0`。空集合不改FLAG112、不抽亂數；多人由候選數抽一次。不刪除角色、不改TARGET，選中索引寫FLAG112。

1751–1785為顯示，PRINTDATA另抽3與4的亂數；FORCEWAIT完成後才寫角色狀態。1786–1809將狀態設-1、清20／21／30／31／220、行動100設103、前三BASE設1、35／36各加300，並按原文設定相關TALENT。1810尚有一次PRINTW；完整共8次確認，前7次等待時尚未回收，第8次等待時已回收。重送Web輸入token不重套一次效果。

## 引擎與等待

- `reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`：自然落尾只清RESULT0；`GameData/Variable/VariableEvaluator.cs:1732–1740`：RETURN不清尾格。
- `reference/emuera-1824/Emuera/GameProc/Process.State.cs:370–378`：JUMP返回後呼叫者立即返回；PALAM_UP的既有勝利捷徑須`yield from source_check_jump`，否則TS／等待會被誤認成錯誤。
- `reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:497–508、707–734`：WAIT確認不改RESULT(S)。沿既有`WaitInputRequest`及Web輸入token。
- catalog `run_event_gen(..., waits=True)`僅本次側事件啟用PRINTW／FORCEWAIT，巢狀口上沿同等待通道；FIRST既有機制保留，其他舊等待仍W07。
- 顯示切片暫借LOCAL供原字串索引顯示，完成後恢復；不改外層RESULT0。切片只有顯示／樣式，無狀態代入、CALL或INPUT；不重播整段發現函式。

## 驗證範圍

`tests/test_battle_side_events.py`75案，從全新人工25歲資料建立；首次紅52 failed／4 passed，追加測試後75案通過；15檔定向1024 passed，1 warning。表格含啟用／關閉、門檻、RNG、多人／空集合、三路真TS選單、catalog等待、真PALAM_UP的JUMP、六路run_train／Web與重送。
`tmp/s80/browser_fixture.py`以臨時存檔提供`/fixture`可見控制表單：七條人工前態均先按201；觀眾ON/OFF不需確認，返血ON5次／OFF0次，發現ON8次／OFF0次。返血TS為前5次確認→數字3,1,0,1,7,0→最後1次確認，全部原生輸入；敘事只保留數字按鈕，其餘Null範圍明示。主代理真瀏覽器七路均通過，按原按鈕／Enter完成；發現第1／7／8次等待與返血第1／5次等待均保存狀態，核對副作用時點與只套用一次。七路輸入總次數依序1／1／6／1／9／1／13；TARGET、RESULT尾格及四年齡欄25保持，console警告／錯誤0。頁籤與伺服器已關，證據為`tmp/s80/browser-*.json`與`blood-ts-complete.png`。
主代理修正後全pytest：`5171 passed, 1 warning in 246.31s (0:04:06)`；依使用者分級驗證裁決沿用此全pytest與瀏覽器結果，模擬範圍見下段。不宣稱自然遭遇、完整救出系統或整列B04／B05／B09完成。

模擬工具的發現事件計數包裝也必須委派generator；同步呼叫會丟棄等待並回傳None。S80第一輪正式模擬在tokusou78／88重現，修正只在`tools/sim.py`，完成後才計數並傳回返回值。`tests/test_sim_isolation.py`新增無等待／兩次等待兩案，驗send、返回值與計數；先紅2案、修正後定向90案通過，兩失敗seed重跑均到上限。第一輪證據保留`tmp/s80/before-repair1`。2026-10-06使用者裁決改採分級驗證後停止餘下模擬；修正後完整批次存`tmp/s80/adult25-v1-final`：default0–249為247上限／3回標題，tokusou0–99為100上限，catalog／fixture失敗0，停止原因均同S79。未結束批次的32局不計入350局驗收。只有tokusou78／88的`S30 pyfunc CLEARRANDCHOOSE`與`CHOICECOUNT_F`計數消失，因候選收集已手翻為原生Python，其餘JSON欄位相同；詳`audit-partial.json`。不宣稱完整500局，最近完整基線仍為S79。
