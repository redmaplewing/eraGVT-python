# 開局控制流程（S79／W04）

## 原作與接線範圍

- `ERB/ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST:73–87`先呼叫`MODE_SELECT`，再進角色製作。角色來源只在`ERB/SYSTEM/キャラメイキング関連/CHARA_MAKE.ERB@CHARA_MAKE_MAIN:316–322`的[200]選擇；原作沒有「汎用／特装戦隊」二擇開局。
- `ERB/ゲーム内_イベント発生/オープニング処理.ERB@MODE_SELECT:297–409`的新局1–7與引繼共用原生`mode_select_gen`；選中寫FLAG:0，正常返回RESULT:0=0。新局[100]回999，由EVENTFIRST回標題；[200]全域設定、[300]說明仍接原呼叫。引繼不接受SANDBOX，多於一人不接受SOLO。
- `ERB/DIM.ERH@モードオプション:83–92`定義七模式位元；`ERB/ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST:114–122`按SOLO建立1人，其他3人。角色製作[999]刪除角色、保留FLAG:8並回模式。套組仍由原[200]選單載入，不自動代選。
- `ERB/ゲーム内_イベント発生/オープニング処理.ERB@SET_LIMIT_DAY:430–451`：NORMAL／INSTANT每王11日，SOLO12、HARDCORE13，其餘9；ENDLESS位為1時總期限0。FREEPLAY／SANDBOX也包含ENDLESS位。這裡只驗開局狀態，不宣稱七模式生命週期完成（W06）。

## 序章具體範圍

- `ERB/ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST:177–185`顯示[0]否／[1]是，無預設輸入值、無返回選項；其他數值留在同一INPUT迴圈。[0]只印空行，繼續原初始化。
- 同函式:186–238的觀看支線只有顯示、讀取模式／角色狀態、PRINTW及FORCEWAIT，無遊戲狀態寫入。:193–216包含學生受襲與強制繁殖敘事，保留明確未移植停止；沒有摘錄、改寫、渲染該敘事，不能稱原作未完成或只以Null驗收為觀看完成。
- 本次可交付的是原作選擇／無效輸入控制、略過至SHOP及觀看明確停止；觀看至SHOP仍不成立。W04仍保留套組10及此具體阻塞，產品年齡與故事均未改。

## FIRST與等待

- `ERB/ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST:254–267`逐人先設定TARGET、必要時抽支配者，再呼叫`ERB/地の文/MESSAGE.ERB@MESSAGE_FIRST:4–6`的KOJO_ROOT，最後入隊。沿用原生`kojo_root_gen`與既有catalog；不預先寫入後一人的狀態。
- `ERB/口上/口上システム関係/KOJO_ROOT.ERB@KOJO_ROOT:17–90`既有抑制／口上選號與找不到的回傳保持。MESSAGE_FIRST自然終端寫RESULT:0=0；並非假定所有口上只有FLAG:62／900兩項副作用。
- `CatalogNarrationService.call_kojo_gen(code="FIRST")`啟用同執行緒的WAIT／PRINTW／PRINTDATAW確認；巢狀catalog呼叫也等待，INPUT／INPUTS沿原通道，不重放。其他事件舊WAIT仍歸W07，未全面遷移。
- 引擎依據：`reference/emuera-1824/Emuera/GameProc/Process.ScriptProc.cs:61–67`（自然終端）；`reference/emuera-1824/Emuera/GameProc/Process.cs:249–260`（INPUT／INPUTS）；`reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:497–508、707–734`（確認不寫RESULT(S)）。
- 新局前標題舊文字保留符合`reference/emuera-1824/Emuera/GameProc/Process.SystemProc.cs:197–209`的PrintBar/NewLine；不把畫面歷史[0]當成有效MODE_SELECT選項。
- 沒提供narration的非互動helper仍保留性格初始化的按需catalog載入；明確傳Null不被更換。固定helper只代按其明確參數，遇額外FIRST輸入不猜答案。

## 驗證與人工前態

`tests/test_opening_sequence.py`的expected從上述原文推導；人工catalog只含中性文字、數字與確認，驗TARGET、入隊時序、狀態只加一次及RESULT(S)保留，不代表原作全部敘事已驗。

`tmp/s79/browser_fixture.py`提供可見`/fixture/control`，使用fresh-adult-25-v1、臨時存檔，選Null或中性FIRST；原生按鈕／generator保留。真正預設不改設定路徑保留`MAXBASE:41=-1`未設定形態年齡哨兵，其他三年齡欄25；套組0中性FIRST四欄均25。來源是`ERB/SYSTEM/キャラメイキング関連/CHARA_SIZE_UI.ERB@CHARA_SIZE_DEFAULT:2152–2153`與`CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_BASE_PROFILE:520、533–534`，不可事後覆寫或換套組冒充預設。精確操作：

1. Null預設：標題0→模式1→角色製作1000→配置1→序章0，應到SHOP；角色NO均0、模式2、期限87、FLAG8=3。
2. 返回重入：標題0→模式1→角色製作999→模式2，角色剩管理員＋1人、FLAG8=4；再999→100回標題。新局0→1可再開始。
3. 觀看停止：全新局0→1→1000→1→序章1，HALTED且未逐人FIRST／入隊；不輸出受限原文。從停止返回標題後重走可略過至SHOP。
4. 中性FIRST：表單選中性catalog重建；0→1→200→0→1→1000→1→0，停確認；Enter→文字填「中性輸入」→數字7→Enter→SHOP。第一人CFLAG280=1、281=7、CSTR20保留輸入，catalog失敗0；等待時TARGET=1、尚未入隊。
5. 七模式：每次表單重建，以0→模式n→1000→1→0；SOLO1人，其餘3人，初始期限如前段；此為B02開局邊界，非W06完整長局。

主代理已完成上述七模式開局、返回重入、無效模式／序章值、觀看停止後重新略過，以及中性FIRST的逐步真瀏覽器驗收；console警告／錯誤0。無效模式不變更狀態；序章無效值只更新RESULT:0。中性FIRST兩次等待時尚未入隊，完成才到SHOP，CFLAG280保持1、281為7、CSTR20保留文字，catalog失敗0。證據為`tmp/s79/browser-*.json`、`normal-shop.png`與`neutral-shop.png`，頁籤及伺服器已關閉。

主代理全pytest：`5094 passed, 1 warning in 162.02s (0:02:42)`。首次全測試僅舊模擬假session缺input_kind；新修正代理補上原有確認的number前態，保留expected與策略亂數斷言後通過。正式500最終結果見STATUS。原作受限觀看分支無成功瀏覽器案例。

## 與S78模擬差異的原因

S79 default正式250局中34局完整JSON與S78不同。全部34個差異seed及seed0控制組，以相同25歲人工資料與S78提交6916875／S79開局函式只跑至首次SHOP，確認共同起因是FIRST_21選人初始化提前執行；存檔狀態只差相關角色的CFLAG279／280、CSTR20。33局新增一次數字選人與10次確認；seed214有兩名角色，兩次選人與20次確認。全部到SHOP、catalog失敗0；seed0狀態與兩種RNG完全相同。

依據：`ERB/ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST:254–267`；`ERB/口上/女性汎用口上/KOJO_0_21_ヤンデレ.ERB@KOJO_0_FIRST_21:68–78、104`呼叫設定、轉為固有ID；同檔`@YANDERE_FIRST_SETTING:35–57`選人與99、`@YANDERE_SEARCH:23–26`更新280。等待在FIRST:80、83、85、87–92、105，不寫RESULT(S)。原先漏掉FIRST時，`@KOJO_0_TURNEND_21:109–120`直到TURNEND才補設定。

24局直接選人，完整開局遊戲RNG序列與S78相同；10局選99，按設定函式49–51增加RAND3耗用，抽到自己時重抽。這10局為34、35、53、105、130、135、194、211、214、236。全部34局都增加策略choice耗用，確認等待不耗策略RNG。seed8／9／22首輪三人行動分別由104,106,107→106,107,103、108,106,105→106,105,103、103,104,101→104,101,108；動作碰巧相同也不代表RNG狀態相同。

證據：`tmp/s79/audit_opening_probe.py`／`.json`與`audit_opening_summary.json`。這證實全部34案最早分歧符合原作派發與既有策略；未逐回合追溯全部下游事件。正式500停止表仍可與S78比較，不能宣稱完整JSON等價或每項事件差異已個別證實。
