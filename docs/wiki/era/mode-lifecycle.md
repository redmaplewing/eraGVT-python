# 七模式生命週期（S84／W06）

本頁承接[S79開局](opening-sequence.md)、[S82戰鬥終端](battle-lifecycle.md)及[S83模式規則](mode-rules.md)。
S84只補完整catalog的定向／連續驗收，沒有產品修改。主代理的瀏覽器、全pytest及W06結包500結果以STATUS與session紀錄為準。

## 模式表

原作依據：`ERB/DIM.ERH:60–92`、`ERB/ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST:98–122`及`@SET_LIMIT_DAY:430–451`。
以下使用新局原預設人數；增減人數另依`FLAG2 -= (CHARANUM-1)-3`，SOLO不套此修正。

| 模式 | 人數 | 每敵期限FLAG2／總期限FLAG1 | 持續與終局 | 特有權限 |
|---|---:|---:|---|---|
| NORMAL | 3 | 11／87 | 普通敵→Ｋ触手→評分；超期回標題 | 一般成就 |
| SOLO | 1 | 12／94 | 有限通關／超期；洗腦及取り込まれ由SOLO專用結局 | 不走團隊全滅結局；防衛105不可設 |
| HARDCORE | 3 | 13／101 | 初周Ｋ触手通關；既有周回Ｋ触手後增加天使樹 | 天使樹增援延長總期限5 |
| SURVIVAL | 3 | 9／0 | ENDLESS擊破不減普通敵存活位元；期限失敗按擊破紀錄分流 | 擊破至少8才進評分，不能假稱有限通關 |
| FREEPLAY | 3 | 9／0 | ENDLESS且不判日期失敗；仍可全滅 | 全滅至少8仍進評分，見下節 |
| SANDBOX | 3 | 9／0 | ENDLESS、不判日期失敗、不走全滅結局 | 不取得成就；引繼選單禁止選入 |
| INSTANT | 3 | 11／87 | 有限通關／超期 | 開放招募引退、能力降低及每戰鬥回合真等待 |

共同跨日規則為白天→夜、夜→次日白天；並非各模式自行加日。依據：`ERB/インターミッション画面/SHOP_TURNEND.ERB@EVENTSHOP:168–180`。
七模式定向均從真正新局的模式→製作1000→基本設定1→序章略過0到SHOP，再以全員休憩完成兩個半日，catalog完整執行。

## 終局、增援與禁止條件

- `ERB/ゲーム内_イベント発生/エンディング/ENDING.ERB@ENDING:9–70`以普通／末王存活位元均0判通關，不直接按模式名稱分派。正常ENDLESS擊破保留7bit，不能拿人工清0冒充其通關。
- 同檔`@ENDING:74–87`：僅FLAG999=0、非GAMEOVER且無「制限時間無し」才判日期。普通敵期限`(FLAG3-存活數+1)*FLAG2-DAY+DAY1 <= 0`且夜；末王階段是總期限**恰為0**且夜，不擅改成小於等於。
- 同檔`@ENDING_3:460–498`：ENDLESS先更新GLOBAL114最高擊破數；小於8回標題，至少8設FLAG999=-997，再由`@ENDING:86–87`轉評分。S84以SURVIVAL擊破7／8、day72／81夜驗此邊界，仍保留FLAG100=127。
- `ERB/ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND:527–528`：安全＋被市民拘禁人數=0、非SOLO、非禁止GAMEOVER、非已GAMEOVER才呼叫ENDING_1。七模式均由真EVENTEND驗守衛；人工成年男性前態走ISMANLY省略額外敘事，不改模式判斷。
- `ERB/ゲーム内_イベント発生/エンディング/ENDING.ERB@ENDING_1:263–293`仍依ENDLESS而非「引継ぎ無し」判擊破至少8。**FREEPLAY也能因全滅進評分／引繼**，雖MODE_SELECT的說明稱不能周回；照原控制流保留，未新增禁止規則。全ERB／ERH精確搜尋`OPTION_引継ぎ無し`共1處，只有`ERB/DIM.ERH:65`定義；沒有消費端。S84補2案由EVENTEND→ENDING_1→EVENTTURNEND→SCORE驗SURVIVAL／FREEPLAY的8體分支。
- `ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK:176–193、266–281`：FLAG854>0且HARDCORE的Ｋ触手勝利，FLAG4由1加至2、FLAG1加5、FLAG21=1；清Ｋbit後生成FLAG101=2的天使樹。S84四有限模式周回K勝利對照只有HARDCORE回SHOP待增援，其餘評分；兩末王各終端及天使樹階段沿用S82／既有`test_angel_tree.py`。
- `ERB/インターミッション画面/SHOP.ERB@USERSHOP:289–294`：加入引退位元只在INSTANT預設開啟；169列表、170且CHARANUM>1可引退、180且CHARANUM<=29可招募。七模式權限表及既有招募／引退Web邊界測試覆蓋；`@USERSHOP:620–621`亦拒絕SOLO防衛。
- `ERB/インターミッション画面/SHOP_TROPHY.ERB@UNLOCK_ACHIEVEMENT:6–20`：SANDBOX禁止取得，其餘允許。S84不預填GLOBAL200，實際呼叫取得並核對寫入；既有解鎖等待／落盤驗收沿用W01。
- `ERB/ゲーム内_イベント発生/エンディング/ENDING.ERB@ENDING_6:657–661`前置原作停用；S84全ERB／ERH搜尋實際CALL／JUMP／TRYCALL／TRYJUMP到ENDING_6為0筆，沒有新增入口。

## 結局存檔與新周連續鏈

新增六條完整catalog定向：NORMAL→NORMAL、SOLO→SOLO、HARDCORE→HARDCORE、INSTANT→INSTANT、NORMAL→SURVIVAL、NORMAL→FREEPLAY。
每條均由真新局完成預設角色製作／原基本設定／序章略過到SHOP；其後才施加明示人工優勢：七普通敵已擊破、K仍存活、研究滿額、累積傷害令原遭遇HP下限1、首人出擊，其餘休憩、攻擊／敏捷10000與seed4。
然後真ACTION_MAIN→遭遇→TRAIN輸入→SOURCE_CHECK→TURNEND→SCORE→原SAVEGAME槽5；不是直接呼叫結局，也不宣稱自然長局通關。

新GameSession只讀同一目錄的save05／global.json：標題讀檔1→槽5，到與結局存檔後相同的引繼選單；999→0確認不選角色→模式→適用時人數0不變→製作1000→基本設定1→SHOP。
依據：`ERB/ゲーム内_イベント発生/オープニング処理.ERB@EVENTLOAD:13–14`、`ERB/ゲーム内_イベント発生/エンディング/ENDING.ERB@ENDING:4–5、29–69`及`ERB/ゲーム内_イベント発生/エンディング/SUCCESSION.ERB@SUCCESSION:1444–1622`。

`ERB/ゲーム内_イベント発生/エンディング/SCORE.ERB@SCORE:740–749`只累加GLOBAL100／101／102對應SOLO／NORMAL／HARDCORE；INSTANT不寫這三格，但FLAG854同樣加1。S84驗新session保留計數、新周DAY1白天、FLAG64=0、7敵存活及自動99同樣保存此邊界。
引繼SANDBOX禁止、繼承多人時SOLO禁止及返回／重入沿用S79與`test_succession.py`。引繼是共用MODE_SELECT，不另造七模式選單。

引擎既有依據沿用[繼承](succession.md)：`reference/emuera-1824/Emuera/GameProc/Process.SystemProc.cs:614–640`（BEGIN SHOP不RESETDATA且可自動存檔）、同檔`:865–869、926–934`（SAVEGAME返回），本次沒有新引擎假設。

## 驗證與範圍

- `tests/test_mode_lifecycle.py`32案：七模式跨日／權限7、期限8、通關讀回新周6、周回K增援4、全滅守衛7。全新人工四年齡欄25，允許原未設定另一形態-1；完整AdultCatalog、只遮蔽敘事輸出。
- 原32案＋開局、模式規則、繼承、兩末王、GAMEOVER、招募／引退及紀錄定向：`523 passed, 1 warning in 32.88s`。
- 補`tests/test_mode_endless_endings.py`2案：`2 passed in 0.99s`。與主代理原全pytest分開補驗，不為純測試追加重跑全套。
- `tmp/s84/browser_fixture.py`六路：normal-chain、survival7、survival8、freeplay、sandbox、hardcore-reinforcement。HTTP只驗fixture可進新局／SHOP前態／行動，不冒充真瀏覽器；主代理六路真瀏覽器已通過，證據tmp/s84/browser-summary.json／browser-audit.json／browser-new-cycle.png；各路新局均實際輸入，完整catalog失敗0、console警告／錯誤0。
- 主代理全pytest：`5396 passed, 1 warning in 384.36s (0:06:24)`；凍結後追加的獨立兩案另由主代理驗`2 passed in 0.90s`，合計5398案驗證，不把兩次合成單次全pytest摘要。產品完全未改，無重跑全套。
- 主鏈首次攻擊後依序等待攻擊成就、SCORE首段、成就211、SCORE末段，再到存檔詢問。既有`with_achievement_wait(None)`呈數字輸入且會殘留TRAIN按鈕；數字值只確認等待。此輸入外觀屬W07，本次未修改，也不能將殘留按鈕誤判仍在戰鬥。
- HARDCORE人工攻擊／敏捷10000另觸發成就220／221／224／225，首次攻擊263後共五次確認才回SHOP；依據`ERB/インターミッション画面/SHOP_TROPHY.ERB@GET_STATE_TROPHY:398–415`。原生等待逐次送出，沒有為驗收取消成就。
- W06 DoD對應：新局／引繼一致＝S79＋S84六連續鏈；日期＝七模式兩半日＋八期限終端；增援＝四有限模式周回K對照＋S82兩末王；招募／禁止＝七模式權限／全滅表＋既有Web邊界；ENDLESS／能力降低＝S83；結局存讀／GLOBAL／新周＝S84六連續鏈及normal真瀏覽器主鏈。
- 主代理六路真瀏覽器與W06結包500通過：default247上限／3回標題、tokusou250上限，catalog／fixture失敗0；十批seed／log／參數／exit0核對，完整輸出欄位逐seed同S82，證據tmp/s84/adult25-v1/audit.json。W06範圍完成，STATUS／PLAN同步；不宣稱完整GameState等價或自然長局通關。W02／W04既有阻塞、W07舊WAIT與W09完整B矩陣仍保留；未新增UNVERIFIED／DEVIATION。
