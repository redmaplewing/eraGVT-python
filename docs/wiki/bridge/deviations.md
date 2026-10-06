# 與原作的偏離（需使用者決定）

凡是 Python 版與原作行為不同的地方（簡化、跳過、近似規則、額外保存的資料…）都列在這裡，
程式對應位置標 `# DEVIATION:`。使用者決定後，在該項註明「已同意（日期）」或改回與原作一致並刪除該項。

**2026-09-29 使用者裁決（整體）**：以下所有項目暫時維持現狀，開發繼續推進；之後的進度可能給出合理解釋。
只有在某項偏離或原作 bug **已嚴重到無法推進開發**時，才回頭評估修正方式。新增項目仍照規則登記並在 session 報告列出。

格式：`- [ ] 內容（原作：檔案@函式／reference 位置；Python：模組@函式）— 為什麼要偏離／替代方案`
ERB 路徑相對 `source/earGVP/ERB/`。
S56現況歸屬：各未勾選項的W編號指向`docs/PLAN.md`；仍待實作／查證／裁決，不因排入計畫而視為批准。現存停止以`docs/PLAYABILITY.md`為準。

## 狀態會不同

- [ ] `W08` **亂數**：用 Python `random.Random`（可 seed），不是 Emuera 的 MT 實作；RAND 的呼叫次數也不追求一致（例：`RESEARCH_QUOTA` 的 `RAND:5` 是否短路求值）。同 seed 不會得到原作同樣的結果。（原作：`reference/.../GameData/Variable/VariableEvaluator.cs`:36–52；Python：`eragvt.state.rng.GameRng`）— 要完全一致需移植 MTRandom 並逐一核對求值順序，成本高。
- [x] ~~**開局：身體資料生成未移植**~~（S09 解決）：`CHARA_MAKE_BASE_PROFILE` 已移植（`eragvt.game.opening.chara_make_base_profile`、
  `eragvt.game.body`）。查證結果：初期セットのキャラは `NO ≠ 0`（:498 條件不成立）→ 原作本來就不生成，BASE:40–48／CFLAG:33–34 為 0
  與原作一致（`docs/wiki/era/body-profile.md`）。S10：汎用キャラ的隨機生成（:507–980）與 AGE_SETTING 的年齢指定（CSTR:204–206）
  已移植；S50 補完原生年齡／色碼的 TOINT／ISNUMERIC 十六／二進位與指數表記（`docs/wiki/python/numeric-input.md`）。
  完整角色製作的手動生成 UI 仍未移植。
- [x] ~~**FLASHNEWS 未移植**~~（S26 解決）：`SHOP_FLASHNEWS.ERB` 全體（新聞產生・亂數・SAVESTR:20／FLAG:60・ゲームオーバーモード 10001・
  裏ボス 10000・イベント戦ニュース・CHOOSEIDOL 的 CFLAG:284 加權・static #DIM）已移植（`eragvt.game.flashnews`）。剩下的偏離見下一項。
- [x] ~~**FLASHNEWS イベント戦ニュースが讀「前回の RESULTS:0」**（S26）~~（S26b 照原作解決）：`TRYCALLFORM EVENT_BATTLE_FLASHNEWS_{n}(ARG)` の後
  `LOCALS'=RESULTS`（:74–87）で前回値を読むのは 3004 の ARG 0（時間切れ＋被害）と 5 の ARG -1（敗北）だけ（3001／3002／6001／6002 は FLAG:60 の
  代入もコメントで到達しない；S26 の「102／87 回」は 3001／3002 の戰鬥回数で、この路の回数ではなかった）。戰後の BEGIN SHOP では
  @EVENTSHOP 後のオートセーブが @SAVEINFO を呼び、:604 `SUBSTRING` が RESULTS:0 = "408" を書く → 原作どおり「FLASH NEWS：《408》」を表示
  （`shop.save_info` が共用 RESULTS:0 を書く。詳細と書き込み元一覧は `docs/wiki/python/result.md`「事件戰ニュースの前回値」）。
- [x] `W01` **全域資料（GLOBAL）：成就／紀錄接通，兩項原作缺陷已修正**（S59；使用者2026-10-05同意）：設定與角色製作GLOBAL存讀、共用成就取得／等待／保存、GET_STATE三組判定及SHOP[800]已接通，見[成就](../era/achievements.md)。
  S58已接通：`ERB/インターミッション画面/SHOP_TURNEND.ERB@UPDATE_STATUS_RECORD`；`ERB/ゲーム内_イベント発生/エンディング/SCORE.ERB@SCORE:695–698／740–747`的GLOBAL:110最高總評與GLOBAL:100–102模式通關數；`ERB/ゲーム内_イベント発生/エンディング/ENDING.ERB@ENDING_1／ENDING_3／ENDING_6`的GLOBAL:114 ENDLESS最高擊破紀錄。20欄紀錄及結算寫入已接通。另`ERB/ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK`原先整段省略的救援271／273與全boss259／260／261／265六處成就已補齊。S59最高總評已改讀寫113，魅了維持110，不拆分回填舊110；對應程式均標DEVIATION。
  既有角色製作權限／引繼解鎖消費端已核對；未移植互動端由W02接續驗收。首次全域檔的GLOBAL:3原作問題見本頁S24怪處；GLOBAL:110碰撞見成就wiki，兩項已於2026-10-05獲使用者「好，依建議」批准；W01最終驗收見STATUS。
- [ ] `W02／W04／W06` **開局的 UI 跳過**（S10 改寫、S24 縮小）：狀態已照原作預設路徑（NORMAL → キャラメイク不設定直接 `[1000]`＝汎用キャラ 3 名おまかせ生成
  → HEROINE_PRESET `[1]` 基本セット → 序章 `[0]`，`docs/wiki/era/flow.md` §1）。**S24**：HEROINE_PRESET 畫面照原文顯示並接受 [0]〜[3]・[10]
  （[20+]／[30] 已於 S25／S51 接通）。S55 已接通角色製作主選單與共通設定。仍略過模式選擇／序章畫面，保留 `@EVENTFIRST` 中 MODE_SELECT 位置的
  2 択「[0] おまかせで開始（原作既定）／[1] 初期セット『特装戦隊』で開始」（後者先載入原作 `[200]`→`[0]`→`[1]はい` 的角色，再進製作主選單；兩者均需按 `[1000]` 完成），
  其下照 MODE_SELECT:360–368 附 [100] タイトルに戻る／[200] グローバルコンフィグの編集（照原作）／[300] ゲームの説明（S52 已接通）。
  模式固定 NORMAL（MODE_SELECT 沒有預設值，[1] 是第一個選項）。（Python：`eragvt.game.opening.event_first_gen`、`session._title_input`）
  開局 `MESSAGE_FIRST` 口上仍不輸出（見下「口上」）。
  S60已取消開局個別編輯／醫療加入／追加招募[0]/[1]／引繼的主選單代按，接通12項子選單；
  招募[2]仍照原作略過個別編輯。子供原作獨立流程不插入共用主選單，S68／S69一人稱及身體尾段已接真實輸入；W02經歷仍未完成。見[角色編輯](../era/character-editor.md)。

- [ ] `W05／W08` **S04未翻行動的停止處理**：8類行動、鍛錬排程、結局／引繼等已接通；目前`action.py:304,420`是不存在預約值與REST狀態安全網，不能沿用舊S04缺口清單。Web遇到未移植仍進HALTED；現存分支統一見`docs/PLAYABILITY.md`，逐項核對可達性。
- [x] ~~**襲撃／救援 會被跳過**~~（S20 解決）：`RAID_HANTEI` 成立時照原作 `JUMP RAID_RESCUE／RAID_ATTACK` → イベント戦（`eragvt.game.raid`）。ラスボス出現後（FLAG:100 = 0）の襲来は S27 接上（生存ラスボス 0 で原作無限ループの路だけ停止）。
- [ ] `W03／W05／W06` **未移植的戰鬥分岐會停止遊戲**：主幹、雜魚／市民／悪堕ち、兩隻末王皆已有實作。剩餘裝備／觸手服、觀眾妨礙、返り血、模式與動態分派安全網見`docs/PLAYABILITY.md`完整歸屬表；依既定規格明確停止，不自行發明行為。
- [ ] `W03／W05` **幽閉未移植分岐會停止遊戲**：TS_MtoF／TS_NORMAL／TS_FtoM仍停止。悪堕ち、容姿／回復、Ｋ触手與天使の樹幽閉已接通；其餘資料分派guard需核對，不能再把整個末王2列未移植。見`game/prison/event.py:87,122,141,233,241`與盤點表。
- [ ] `W03／W08` **妊娠／子供未移植分岐會停止遊戲**：TS轉換與除錯妊娠輸入仍缺；命名INPUTS、變身命名及隨機命名已接通，不再列停止。來源`ERB/ヒロイン関連/TRANS_SEX.ERB@TS_MtoF`，Python `battle/ninsin.py:175,279,296,452`。
- [x] **振り解く判定的 `LOCAL:O`**（S06 新增；**已裁決 2026-10-03：視為打錯字，當 `0` 處理＝`LOCAL:0`**）：`ゲーム内_戦闘処理/COMMON_BATTLE_HANTEI.ERB`:241／:245
  `SIF LOCAL:5 <= 45 && LOCAL:O > 49` 的 `O` 是英文字母，全作沒有這個識別子（grep 僅此 2 處）。1.824 在執行到該行時
  報錯停止（`GameProc/Process.ScriptProc.cs`:38–42、`GameData/Expression/ExpressionParser.cs`:264–269、
  `GameData/IdentifierDictionary.cs`:645），而振り解く的％顯示（`PRINT_COMNAME.ERB`:6–13）每次都會經過這裡，
  也就是原作（1.824）一被拘束就無法繼續。本作當作 `LOCAL:0`（體力氣力殘量％）的筆誤來判定。
  （Python：`eragvt.game.battle.hantei._hurihodoku`）— 替代方案：照 1.824 停止（等同無法玩拘束），或確認 +v10 的行為。
- [x] **SCORE 的 `FOR CCOUNT, O, CHARANUM`**（S27 新增；**已裁決 2026-10-03：維持當 0**——使用者委由代理裁決：`O` 只能是 `0` 的筆誤，
  照 1.824 停止等於クリア後無法看到評價，而當 0 與「從 1 開始」結果相同，不改變任何評價值）：`ゲーム内_イベント発生/エンディング/SCORE.ERB`:150 的 `O`
  同樣是全作不存在的識別子（grep：此處與上項 2 處、`CHARA_SIZE.ERB`:423 的 `RESULTS = O`〔字串，非識別子〕），1.824 在クリア時執行到
  該行會報錯停止（同上依據）。本作當 0（MASTER = 0 會被 :151 跳過，結果與從 1 開始相同）。（Python：`eragvt.game.ending.score_values`）
- [x] ~~**開局身體資料未生成對戰鬥的影響**~~（S09：**不是偏離**，移到下方「原作行為」）。
- [x] ~~**口上的狀態副作用**~~（S07 更新；**S29 解除**）：口上／地の文函式內對狀態變數的代入（CFLAG・TALENT・BASE・CSTR・CDFLAG・NAME…
  盤點 1,064 處）改為直接寫 `GameState`（`narration.runtime.Interp._state_set`，`docs/wiki/python/narration.md`「S29」），KOJO_ROOT 照原作輸出並改變狀態。
  口上 CALL 的 LEVELSTATUS／TRANSFORM／PERFORM_CHEERS_HATE 接 Python 移植（`eragvt.game.kojo_calls`）。S30 起靜態不可執行的口上為 0
  （KOJO_AEGI 的 GOTO、STRDATA 等已支援；剩 1 個地の文 COLOR_T_SHAPE，見覆蓋率報告）。

## 只影響顯示

- [ ] `W04／W07` **口上**（S07 更新）：SHOP 一口メッセージ・行動・戰鬥中的口上改由 catalog 輸出（`eragvt.narration`）。仍未輸出的：
  unsupported 的口上（S30 起 0；實行時失敗者見下項）、開局 `MESSAGE_FIRST`（`opening.event_first_gen` 仍略過此處輸出，
  維持 FLAG:62＝0・FLAG:900＝0 的「找不到」處理）。無 `ERB/` 目錄時回落 `NullNarrationService`。
- [ ] `W07` **口上 catalog 的實行時失敗**（S07 新增；S29 改寫）：執行中才發現的子集外（動態 CALLFORM 的呼叫先不可執行、generator 以外遇到 INPUT）
  或引擎會報錯停止的狀況（除以 0、範圍外參照），catalog 會回復輸出・亂數・LOCAL・RESULT(S)，S29 起連 **GameState 的書き込み**（ジャーナル
  `runtime.StateJournal`，含 KOJO_ROOT 的 FLAG:62／900）也完整回復，口上當「找不到」、地の文印佔位。原作會報錯停止或照常執行。
  無法回復而停止（NotImplementedError）的情況包括：Python 移植的 hook CALL（`HOOK_CALLS`：SET_TENTACLE_SIZE_BY_MESSAGE、NINSIN_HANTEI、
  LEVELSTATUS…）執行後才失敗者。（Python：`eragvt.narration.service._run`）
  S14：含 INPUTS 的函式以「重放」執行（`run_function_gen`），S29 起 INPUTS 前的 GameState 書き込み／KOJO_ROOT 也可回復後重放，只有 hook CALL 之後才停止。
  S29 模擬（`--actions 101〜108`）實際觀察到的失敗：`KOJO_4_HITOKUTI_SHOP` 經動態呼叫到 INPUT（原作會等玩家輸入；本作當找不到、狀態回復）、
  `AEGI` 的 STRDATA（`KOJO_0_SEX_COM0_16` 等經由喘ぎ声；S30 解除）。S30 模擬另觀察到 `KOJO_0_TURNEND_21`（ヤンデレ）經
  `YANDERE_FIRST_SETTING` 到 INPUT（預設 34 局 5,399 次；S29 的程式碼同 seed 也會發生，非 S30 新增）。
  **S31 裁決（2026-10-04）**：TURNEND／SHOP 口上遇到 INPUT 依原作顯示選項並等待，選完續行，不再回復為「找不到」。
  輸入後才發現不可執行內容時停止；其他同步呼叫的失敗回復仍待裁決。詳見 narration wiki 的 S31 節。
- [ ] `W07／W08` **口上 catalog 的顯示簡化**（S07 新增，只影響顯示）：`SETFONT`（字型名）不反映（`FONTITALIC` 斜體 S20 起反映：`TextOutput.set_italic`）；`CLEARLINE` 只刪已完成的行；
  S41角色強化重繪沿用共用CLEARLINE（`ERB/インターミッション画面/SHOP_CHARA_POWERUP.ERB@CHARA_POWERUP:343–346`）；不影響分配、扣款及共享RESULT(S)。
  S60隨機命名沿用精簡按鈕列，重繪依實際輸出行數清除配置／候選頁，對應原文CLEARLINE 16／25；不改狀態與亂數次序。
  S61一般身體頁兩形態依序顯示，數值、提示、可選項與原文INPUT模式保留；固定欄寬／字型仍本項W07。色盤保留32×32及軸／明度列，依實際輸出行數清除舊按鈕，對應`ERB/汎用関数/COLOR_TABLE.ERB@COLOR_TABLE:156`固定40行；不是新增全域CLEARLINE語意。
  S45設施擴充、S49武器自訂沿用同一CLEARLINE偏離；局部回顯數值輸入並在繼續時移除Enter操作提示，避免誤刪選項，未修改全域顯示語意（見`docs/wiki/era/facilities.md`）。
  COUNT 放在口上專用的暫存（`state.temp.narr`），與 Python 移植部分不共用（原作是全域變數；Python 未模型化 COUNT）。RESULT（S21）・RESULTS（S22）
  已改為共用（`GameState.result`／`results`，`docs/wiki/python/result.md`）；Python 移植部分只同步寫 RESULT:1／RESULTS:1 以後的來源與「之後有人讀
  呼叫前值」的 RESULT:0／RESULTS:0。S22 全件確認：RESULTS:0 沒有讀呼叫前值的地方；RESULT:0 只有不發的 TRYCALL(FORM) 之後會讀，已移植者全部同步
  （S22 追加 `BATTLE_COM_AFTER.ERB`:1159）。hook 的 CALL（SET_TENTACLE_SIZE_BY_MESSAGE 等）之後地の文不讀 RESULT（grep）。因此在已確認的讀取位置 RESULT／RESULTS 與原作一致，殘留差異是 COUNT。S60姓名生成僅重現本函式COUNT終值20用於LOCAL30索引，仍不寫catalog的共用COUNT；沿本項W07，未新增批准。S62的RAND_CHOOSE_KOJO_SEIKAKU:462–475同樣只保留局部FOR終值19，不寫catalog共用COUNT；仍沿本項。S64 LOADCSV的REPEAT4清SAVESTR同樣不寫catalog共用COUNT，沿本項W07。
  （Python：`eragvt.narration.runtime`）
  S14：`DRAWLINEFORM 文字列` 畫成與 DRAWLINE 相同的區切線（原作以該字串重複到畫面寬：`GameView/EmueraConsole.Print.cs@getStBar`:543–560；
  動画サイト :1335 的 `―`）；動画サイトの `PRINT_TAGSET_TEXT` 的 `@F:` フォント指定不反映（本作未使用），既定色的 `SETCOLOR 0x{GETCOLOR}`
  以「回到呼叫前的顏色」表示（顯示相同）。（Python：`eragvt.narration.runtime`、`eragvt.narration.windowlib`）
- [ ] `W07` **SHOW_SHOP 簡化**：狀態條（`COLOR_BAR` 的色階與長度）以 20 格單色近似；`SHOW_SHOP_STATUS_SIGN`（生理周期・疲勞等標記）、隊伍列表的欄寬對齊與第 2 行詳細未移植；`SHOP_NG_ACTION_INFO` 的紅字在函式結尾重設顏色（原作不重設）。（Python：`eragvt.game.shop`）
  S46 已接通出場／候補列表與編成選擇，候補列表沿用相同欄寬、數值條與狀態標記簡化；來源 `ERB/インターミッション画面/SHOP_SHOW_STATUS_LIST.ERB@SHOP_SHOW_STATUS_RESERVE_LIST:52–86`。
- [x] **SHOP[800]未實作**（S57解決）：成就4頁／紀錄2頁、切換、循環換頁、返回均接通；紀錄寫入仍見W01上項。
- [ ] `W07` **WAIT／PRINTW 不阻塞**：Web 一次顯示到下一個 INPUT 為止，WAIT 位置以虛線標示，不需按鍵繼續。（Python：`eragvt.game.session`、`eragvt.web`）S44引退名簿／報告、S45設施擴充、S49武器自訂已依原作局部補上PRINTW／WAIT等待；S57成就PRINTW亦已真正等待並在確認後保存，但仍沿用Web的required數字欄（`web/templates/index.html:32`）：須輸入0等數字提交，並非原引擎ReadAnyKey的任意鍵確認，且無[0]提示；此輸入差異仍屬W07。其他系統的既有簡化仍保留，見`docs/wiki/era/retirement.md`與`facilities.md`。
- [ ] `W08` **存檔格式與檔名**：JSON（`saves/saveNN.json`），不是 Emuera 的 `.sav`；存檔說明文字（日時＋`@SAVEINFO`）與一覽格式照原作。
- [ ] `W08` **Web 專用按鈕**：頁尾「タイトルに戻る」（重建 session）是原作沒有的。
- [ ] `W07` **無效輸入訊息**：Emuera 以「刪一行＋暫時行」顯示「無効な値です」，這裡以一般行輸出。
- [ ] `W08` **SHOW_SHOP 的 TARGET == CHARANUM**：原作會因越界參照報錯，這裡視為「編成外」重新選擇 TARGET（`eragvt.game.shop.show_shop`）。

- [ ] `W07` **鍛錬畫面**：（S25 起素質一覧 `SHOW_STATUS_TALENT` 與 COLORSENTENCE_BAR 已照原文移植，以下只剩 PRINTLC）`PRINTLC` 以 cp932 位元組數補空白到 26，不做原作依字型寬度削減尾端空白（`GameView/EmueraConsole.Print.cs@CreateTypeCString`:383–425）。（Python：`eragvt.game.action.show_status_base_training`、`eragvt.text.TextOutput.print_lc`）
- [ ] `W07` **戰鬥畫面簡略顯示**（S05 新增）：`@SHOW_STATUS`（`ゲーム内_戦闘処理/BATTLE_SHOW_STATUS.ERB`:3–351，含
  `ヒロイン関連/CHARA_STATUS.ERB@SHOW_STATUS_BASE_DISPBATTLE`、`SHOW_TRAIN_PALAM_STATUS`、`CLOTH_BATTLE_DISPHP`、
  `SHOW_DISTANCE_WINDOW`）只顯示名稱・Lv・體力／氣力／性耐性條・EX 值・狀態・心境・敵名 Lv・距離・剩餘回合・
  敵體力／射精（解析度不足時 ？？？）・油斷・敵能力・解析度；距離適性、スタイル、衣裝耐久、PALAM 表、距離視窗未顯示。
  這些函式內沒有 RAND；代入只有 `STATUS_PRINT_CHARGE`（CHARA_STATUS.ERB:1477–1489，每回合無條件）的 TCVARn:206（[反撃]バースト的蓄積限度），S16 起照原文計算（`train.status_charge_limit`），其餘不影響狀態。`[800]` ステータス畫面 S25 起照原文移植（`eragvt.game.status_screen`）。`SHOW_USERCOM` 只移植「不分類」版（`BATTLE_COM.ERB`:379–568，基本設定 FLAG:801 bit2 = 0），
  《危険度》的顏色照 `FORECAST_OUTPUT_SETCOLOR`。（Python：`eragvt.game.battle.train.show_status`／`show_usercom`／`usercom`）
- [ ] `W07` **性攻擊的地の文**（S06 新增、S07 更新）：S07 起 `地の文/MESSAGE_SEX*.ERB`、敗北 `MESSAGE_BATTLE_END_LOSS`、射精・處女喪失・
  ヒロイン側性攻撃的地の文由 catalog 輸出本文，其中的狀態變化行經 `narration/hooks.py`（140 行，對照 sexmsg）依 ERB 順序執行、
  RAND 也照 ERB 順序抽（亂數序列與 S06 不同）。S14 起 `MESSAGE_SEX_SPCOM7`（含 INPUTS 與動画サイト）也由 catalog 執行。catalog 不可執行或 Null 時才印
  「〈地の文：函式名〉」並走 S06 的 Python 移植（`eragvt.game.battle.core.run_chinobun`、`sexmsg._catalog`）。
- [ ] `W03／W07` **幽閉的地の文與淫紋顯示**（S08 新增，只影響顯示）：`地の文/MESSAGE_PRISON.ERB`、`MESSAGE_OTHER.ERB` 的 PRISON 系、
  `MESSAGE_KYUUSHUTU.ERB`、刻印地の文由 catalog 輸出（狀態變化行 21 行經 `narration/hooks.py` PRISON_HOOK_LINES：FLAG:900、
  TALENT:膨乳改造値、TS 呼叫 → 停止、成就 → 無動作）；catalog 不可執行（Null 等）時印「〈地の文：…〉」並只做末尾的 KOJO_ROOT
  （`MESSAGE_KYUUSHUTU` 則以 Python 輸出同文）。淫紋圖樣 `CHARA_TATTOO.ERB@PRINT_TATTOO`:239–474／`@TATTOO_LIB`（無代入到狀態、
  無 RAND）因 `CHKFONT`（依安裝字型）catalog 不支援，改印「〈淫紋：PRINT_TATTOO n〉」一行。
  （Python：`eragvt.game.prison.*` 的 `run_chinobun`、`eragvt.game.tattoo.print_tattoo`）
- [x] **INPUTS 只能輸入整數**（S11／S14；S35 已消除）：Web 與既有 catalog 等待通道現接受任意字串／空字串；
  命名、影片及巢狀呼叫共用文字請求標記。數字選單仍接收整數。詳見 `docs/wiki/python/naming.md`。
- [ ] `W07` **HTML_PRINT 的子集**（S11 新增，只影響顯示）：只支援原作用到的 `<font color>`／`<nonbutton title>`（tooltip 以 Web 的
  title 屬性顯示）；S25 加 `<br>`（照 `GameView/HtmlManager.cs`:672–676、`PrintStringBuffer.cs`:189–196 分行）、`<nobr>`（Web 不折行，
  無差）、`<shape type='space' param='n'>`（原作寬 n% × 字型大小：`ConsoleShapePart.cs`:40–53；**近似為半角空白 n/50 個**）。其他タグ停止。（Python：`eragvt.text.TextOutput.html_print`）
- [ ] `W07` **子供設定的說明回落**（S13新增；W02預設代按已解除）：フィート選擇畫面（[0]はい）已移植，種族／フィート說明（`ERB/ヒロイン関連/CHARA_SYUZOKU.ERB@SYUZOKU_INFO`／`ERB/ヒロイン関連/CHARA_SYUZOKU.ERB@FEAT_INFO`）走catalog，不可執行時印「〈SYUZOKU_INFO n〉」的既有回落仍待W07收口（Python：`eragvt.game.firstsetting.feat_select_ui`）。
  S61接狀態PAGE5[20]、S67補完SIZE_SETTING操作；S68接`ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD:515`一人稱，S69接同函式:1075–1107實際身體收尾並刪除`size_setting_default`。兩處均等待真實輸入，原W02代按差異已消除；S69僅25歲人工尾段函式邊界驗收，不代表完整出生／加入流程。見[身體編輯](../era/body-editor.md)。
- [ ] `W08` **Web 停止狀態**：遇到未移植處理時顯示「（未實作のため停止しました：…）」並停住，是原作沒有的畫面（見上「S04 未翻的行動」）。
  （S08 的全滅／ソロ結局後停止已於 S12 解除：照原作進入ゲームオーバーモード繼續。）

## 原作行為（照翻，但請留意）

- S05 戰鬥中照原作移植的疑似 bug：`PALAMLV_F` 看的是上次的回傳值而非引數（`汎用関数/コモン関数.ERB`:1015–1043）；
  `EVENTCOMEND` 的解析度上升式用的是**上一回合**避難人數的靜態 `LOCAL:1`，且 `MAX(BASE:知性 - 100, 1)` 被支援值覆寫
  （`ゲーム内_戦闘処理/BATTLE_COM.ERB`:883–895）；`EVENTCOM` 的 `SIF SELECTCOM == 16 …` 只跳過下一行 `TFLAG:4 = 0`
  （:668–671）；`_ABLUP` 的 `LOCAL:1 *= 135 / 100` 整數除法＝×1（`ヒロイン関連/ABL_UP_CHECK.ERB`:46–47）；
  `ABL_UP_1..3` 的中止條件把自己的感覺 Lv 算兩次（:1070 等）；`AFTER_TRAIN_RAPE` 消耗率的分母用 `BASE:性耐性`（戦闘イベント.ERB:992）。

- S06 照原作移植的疑似 bug／容易誤讀處：`TENTACLE_SAKUSEI` 的 `ARG *= 135 / 100` 整數除法＝×1（`TENTACLE_SYASEI.ERB`:581）；
  敗北時 `ABS LOCAL` 是「式中函式當命令用」→ 結果進 RESULT、LOCAL 不變（`reference/.../Instraction.Child.cs`:390–409），
  クズ市民戰（FLAG:73 > 0）因 `FOR LOCAL,1,CHARANUM` 覆寫 LOCAL，防衛力下降也顯示「上昇した」（`BATTLE_TRAIN_AFTER.ERB`:347–371）；
  `KOJO_ROOT` 的結界判定用 STRFIND 部分一致，`SEX_COM1` 也擋住 `SEX_COM10`〜`19`（`KOJO_ROOT.ERB`:23–39）；
  `&&` 與 `||` 同優先順位・左結合（`OperatorCode.cs`:33–34、`ExpressionParser.cs`:502–506），不加括號的
  `A && B || C && D` 是 `((A && B) || C) && D`：`MESSAGE_BATTLE.ERB`:852（引き剥がす失敗文）、`PALAM_UP.ERB`:254、
  `コモン関数.ERB`:714／716（SENGIUP 的距離得意補正，S05 原本誤譯成 Python 的 and/or 優先順位，S06 修正：
  實際上只有 ARG:1 == 2（遠距離）時才可能 ×0.9／×1.1）；`RAND:RESULT / 2` 是 `(RAND:RESULT) / 2`
  （`ExpressionParser.cs@ReduceVariableArgument`:192–198，`COMF6.ERB`:73–88）。
- `USERSHOP_ACTION_CONFIRM` 的確認只有 `CASE 9` 會開始行動，`[1]はい` 會中斷回到選單（`インターミッション画面/SHOP.ERB`:521–532）。看起來像原作 bug，目前照原作；要不要修正請決定。
- `RECOVERY_OVER_TIME` 夜間的 `TALENT:夜魔の貴族` 與 `DAILY_POPULARITY_CHANGE` 的 `TALENT:変身時非処女`、`CFLAG:825` 沒有寫角色 index，實際看的是當下 TARGET（`インターミッション画面/SHOP_TURNEND.ERB`:610、:519、:569）。TARGET 為 TURNEND 時最後處理的角色。照原作。
- `@EVENTSHOP` 的 `PARASITE` 會把 `FLAG:799`（行動中角色）覆寫成 `CHARANUM-1`（`FORCE_深夜の寄生触手暴走.ERB`:9），靠 `SHOW_SHOP`:20 歸 0 才不出錯。照原作。
- S08 幽閉中照原作移植的疑似 bug／容易誤讀處（詳見 `docs/wiki/era/prison.md`「照原作移植的怪處」）：
  `EVENT_PALAM_UP.ERB`:19–21／:88–90／:137–139 的迴圈只涵蓋 UP:0–11（習得〜恐怖 不 ×9、不受触手補正），且幽閉中 UP:0–11 被
  「触手補正 %／100」**覆寫**（:134–140，結果快Ｃ等幾乎只剩 1）；`FUNC_EVENT_PALAM_CALC_TIJYOU_BONUS`:284–293 看未代入的 LOCAL:100–103；
  巨乳補正加在 快Ｖ（:220–229）；`PRISON_GAPING` 的 RESULT 含 ARG:2／3 → LOCAL:151／152 兩倍（各 PRISON_COM :190–192 等）；
  `PRISON_COM102`:105–106 恥情表寫入 LOCAL:8；`PRISON.ERB`:41 `今回陥落するフラグ` 與 :175 `LOCAL:2` 為靜態、沿用上次值；
  `SET_PARTYMEMBER.ERB`:22–24 SHIFTBACK 後遞補的角色本輪不判定；`AFTER_RESCUED.ERB`:23 `FLAG:32 = 0`（非 CFLAG）；
  `SHOP_SHOW_SITUATION_LIST.ERB`:10–39 不還原 FLAG:11 並設 SAVESTR:13；TFLAG:9 全作無代入（`KYUSHUTU_TIMEUP_HANTEI` 不會輸出）。
- S09 身體資料（`docs/wiki/era/body-profile.md`）：**僅初期セット路徑如此**（S10 起預設開局是汎用キャラ，身體資料照原文生成，
  體重正常、此補正約 1–5%）。初期セット直接開始時原作也不生成身體資料（`CHARA_MAKE_DEFAULT.ERB`:498 的
  `NO:SELECT == 0` 條件；NO＝CSV 番号，`reference/emuera-1824/Emuera/GameData/Variable/CharacterData.cs`:99），所以 BASE:体重(44)／
  胸の重量(48) 為 0，`COMMON_BATTLE_HANTEI.ERB` 的胸部重量補正 `value*(1+胸の重量)/(1+体重)`（:606–614 被弾、:1097–1105 撤退 減去；
  :1207–1214 DAMAGE 加上）讓女性角色敏捷變 0、攻擊 2 倍。照原作（`battle.hantei.breast_weight_term`）。
  **需使用者決定**：是否以 DEVIATION 在開局為初期セット角色生成身體資料（等同玩家在キャラメイク畫面按 [6]／狀態畫面 PAGE5 指令 20，
  `body.generate_bodyline`＋`chara_make_age_setting`＋`chara_size_default` 已移植可直接呼叫），以得到「正常體重」的戰鬥數值。
  另外 SET_PROFILE（膨乳化）不看 CFLAG:34，年齢 0 的初期セット角色會得到嬰兒體格（身長 544mm・体重 4.8kg 左右）。
- S10 汎用キャラ生成（`CHARA_MAKE_DEFAULT.ERB`）照原作的怪處：`CHARA_SIZE_DEFAULT`（:519）在「人間には必ず変身能力」（:531–534）
  **之前**執行，所以人間也得到 `MAXBASE:年齢 = -1`、變身時身體資料（MAXBASE:43–48）= 0；BASE_PROFILE 最後 `CFLAG:34 = 1`（:980）
  覆寫 GENERATE_BODYLINE 的成長曲線；AGE_SETTING（:514）在 FLAVOR 決定「学生」（:1077–1087）之前，所以學生別的年齢幅不會套用；
  STATUS_TALENT 可把 :508–512 立的処女拿掉（20%）但清純派留著。`CFLAG:123`（裕福な実家）在 FINALIZE 兩次各 +2500（本作 FLAVOR 不給此素質）。
- S11 拡張度・いちゃラブ照原作的怪處（`docs/wiki/era/gaping.md`）：**Ｖ／Ａ拡張度 CFLAG:35／36 的初期值只在顯示拡張度時設定**
  （`GAPING.ERB@PRINTFORM_GAPING_NOW`:800–808；呼叫者是 FLAG:801 bit 5 的戰鬥 PALAM 表示〔既定 OFF〕與ステータス畫面 PAGE5〔S25 移植：顯示時設定〕），
  所以既定遊玩時從 0（rank 0）開始、第一次被插入就大幅上升（例：0 → 55、膣径 +3.8 cm）；GET_*_GAPING_EXP 的靜態 LOCAL 在 ARG < 3 時沿用
  上次值（:1018–1022）；V_GAPING 等的早期 RETURN 不還原 TARGET；いちゃラブ的処女地の文（MESSAGE_SEX.ERB:1301）因 SEX_V:221 先把
  処女改成 −1 而不會出現。**使用者裁決（2026-09-30）**：照原作，不在開局設定初期值（狀態畫面 PAGE5 移植後自然會在顯示時設定）。
- S25 ステータス畫面照原作的怪處：PAGE1:100 `ELSEIF TALENT;ARG:変身能力 == …` 的 `;` 之後是行中註解
  （`Sub/LexicalAnalyzer.cs`:954–966），實際條件是 `TALENT:TARGET:0`（TARGET 的処女，`VariableParser.cs`:107–119）→ 變身能力なし
  且 TARGET 是処女時顯示【非戦闘員】、非戦闘員本人反而不顯示；性格素質なし時 PAGE1 的性格欄顯示 `TALENTNAME:0`（処女）與其說明；
  PAGE1 アウター（變身能力あり）有名稱時不印「┏」；PAGE4 父親為不存在的ボス／ラスボス番號時 TRYCALLFORM 不發、印前一個 RESULTS
  （Python 停止）；EXPORT_CSV 的 `GLOBAL:262`（成就）消費端仍待W01核對（見「全域資料（GLOBAL）」）；`PRINT_TALENT_CATEGORY`
  的 `SUB_STR:0` 是靜態變數，CFLAG:0 為 -1／5 等時沿用前一個素質名（照移植）。（Python：`eragvt.game.status_screen`、`status_talent`、`export_csv`）
- S13 妊娠・子供照原作的怪處（詳見 `docs/wiki/era/pregnancy.md`「照原作移植的怪處」）：**苗床出産的 `LOSEDEF` 是 static**
  （`BIRTH_AUTO_RANDOM`:607），每次呼叫都累加並以累計值扣防衛力，ゲームオーバーモード中防衛力下降會越來越快；
  `NUM_CHILD_TENTACLE(ARG)` 讀的是 TARGET（:579–601），苗床出産的母乳體質／膨乳改造値也加在 TARGET（:729–732）；
  `BIRTH_HANTEI` 中 SET_PARTYMEMBER 的並べ替え讓同一周回的日數加算落在別的角色上；`ABL_UP_BIRTH` 的氣力由減半後的體力計算、
  快Ｖ／快Ｂ 的珠是代入；`SET_FEAT_DEFAULT` 只要枠 > 0 就取得全部可取得的フィート；`GROW_HANTEI` 在 ADD_CHILD 後的性徴處理落在新角色上；
  `RECALC_PARTYMEMBER` 在 RESCUE_CHILD 施設送り後多跳過 1 人。**使用者裁決（2026-09-30）**：全部照原作（含 LOSEDEF）。
- S15 戰後レイプ・自慰照原作的怪處：**`CALC_GANGBANG` 不 VARSET LOCAL**（`CALC_GANGBANG.ERB`:3–166），條件式才代入的 LOCAL
  （:11 快Ｖ、:20 苦痛、:120 Ｖ経験、:113、:142、:150、:151／152）沿用上次呼叫的值 → 第 2 次以後即使沒有 V 插入（男性・聖処女）
  也會把上次的 Ｖ経験量／快Ｖ 再加一次（`battle.rape.calc_gangbang`，`st.temp.locals`）；`AFTER_TRAIN_RAPE` 的 `LOCAL` 同時是發生機率與
  パイズリ旗標，機率剛好為 1 時聖処女沒選パイズリ也出「胸に精液をぶっかける」（戦闘イベント.ERB:977、:1230）；:1069 的
  `CFLAG:286 == 0 && 清純派` 分岐不可能到達（:1028 先取）；:1082／:1195 `CFLAG:42 != 300 || … != 397` 恆真（只看 ISMALE）；
  **襲われた場合必定 RETURN 1**（:1334），「次も頼むわ」（沒錄影）的分岐也會接到 `DOUGA_RYUSUTU, 1` 動画流出；
  `SELF_KIND` 的 `#DIM Ｖ自慰可／Ａ自慰可` 是靜態且不歸 0（FORCE_夜間自慰.ERB:183–209），一旦有人 Ｖ感覚 ≥ 1 之後所有角色都走 Ｖ 分岐，
  :236 的「兩者皆可」分岐不可能到達；`SELF_NIGHT`:10 的初心判定只看 TURNEND 當下的 TARGET。
- S16 ＳＰ変身・バースト照原作的怪處：**`ADDBATTLESITUATION` 是覆寫**（`特殊シチュエーション.ERB`:43–44 `'=`＝字串代入，
  `reference/emuera-1824/Emuera/GameProc/Function/ArgumentBuilder.cs`:786–807、`Instraction.Child.cs`:466–468），ＳＰフルバースト後
  「EX不可,」取代原本的特殊シチュエーション（例如事件戰的「撤退不可」「攻撃不可」會被解除）；ＳＰ変身（`COMF73.ERB`:12）直接寫
  CFLAG:1 = 2 不經 TRANSFORM，而效果時間結束的 `TRANSFORM, 1`（`BATTLE_COM.ERB`:790–795）在 CFLAG:1 = 2 時再走一次「通常→変身」分岐
  （`COMMON_BATTLE_FUNC.ERB`:458–：胸・體格再套用變動、男の娘／ふたなり 與変身時版本再交換一次 → 交換回去）；
  `COM_ATTACK_COMMON.ERB`:218–221 秘められし力的「隠し補正」加在 RESULT 上，隨即被 `CALL DAMAGE` 覆寫 → 無效；
  [反撃]バーストの蓄積ダメージ TCVARn:205 只在反撃成功（`HANGEKI_STYLE.ERB`:67，S23 移植）增加，限度 TCVARn:206 只在狀態列顯示
  （`STATUS_PRINT_CHARGE`）時計算；ＳＰフルバースト在変身能力ありのキャラ不看ゲージ（`COMABLE.ERB`:808–815 原作註解自承）。
- S23 [反撃]スタイル照原作的怪處（`eragvt.game.battle.hangeki`）：反撃成功時寫入的是 `体勢：ＥＸ反撃`（301，`HANGEKI_STYLE.ERB`:56），
  `体勢：反撃成功`（302，`DIM.ERH`:205）全作沒有任何代入（`TCVARn:2` 代入 口上以外 201 行＋口上 99 行全查）→ `COM_ATTACK_COMMON.ERB`:38 的
  `MESSAGE_BATTLE_CHARA_ATTACK_HANGEKI` 不會出現、`FIGHT_STYLE.ERB`:102–108 的「一次攻撃 1/3」在反撃攻擊時也適用（說明文「反撃成功時に強力な速攻」
  實際不成立）、反撃攻擊後 `COM_ATTACK_COMMON`:419–425 又回到 `体勢：反撃`；HANGEKI 的 ARG:2 是 ENEMY_ACTION 的 LOCAL:2＝被弾量（非完全防御時
  也照樣受傷並蓄積）；攻擊（TFLAG:10 = 1）被直擊也算反擊成功（:27–30）。不屬於偏離，僅記錄。
- S17 寄生系統照原作的怪處（`強制発生イベント/FORCE_深夜の寄生触手暴走.ERB`，Python：`eragvt.game.parasite`）：
  PARASITE_ACTION／SYNBIOSIS_ABL_UP 的「精液経験 10／フェラ経験 2」兩行都寫 `LOCAL:123`（:232–234、:1076–1078）→ 只有精液経験 +2、
  フェラ経験不增加；快B 表只有第一個條件看 Ｂ感覚，`ELSEIF` 以下看 Ｃ感覚（:173–185、:1022–1034）；処女喪失直接寫 `TALENT:処女 = -1`・
  `CFLAG:206 = 4`，不呼叫 LOSTVIRGIN（無喪失地の文、心境變化）；`PARASITE` 的 `LOCAL:2`（:50–52）靜態不歸 0 → 只有讀檔／開局後第一次
  暴走・慰み者前出 DRAWLINE；`SYNBIOSIS_GET_EVENT` 的 INPUT 不檢查值（0／9 以外都當「いいえ」，1 以外走「永久」文面但 CFLAG:84 只在 9 設定）；
  夜這い的對象輸入接受 `0 < RESULT < CHARANUM` 的任何角色番號（:655，含名單外、實行者自己）；`PRINT_CHARA_LIST` 的年上判定
  `TOSHIUE_F(TARGET, …)` 用 TARGET 而非實行者（:834／:851／:868），只有「いとこ」時括號不閉合（:931）；
  `SYNBIOSIS_OUT_OF_CONTROL_EVENT`（:542–565）的兩個呼叫處（:411／:420）原作已註解掉 → 無呼叫者，不移植。
- S18 強制發生事件照原作的怪處（`強制発生イベント/`，Python：`eragvt.game.intimidation`／`yobai`／`small_tentacle`）：
  **クズ市民**：CFLAG:72（監禁クールダウン）只被設成 8、全 ERB 沒有遞減處 → 一旦救出／解放，該角色之後**永遠不再被脅迫**（:13）（**S20 起改為 DEVIATION**：每回合 −1）；
  CFLAG:291 全 ERB 無代入（恆 0）；CFLAG:71（救出所需點數）只在情報収集（`ACTION_GATHER_INFORMATION.ERB`:1004–1041，未移植→停止）減少，
  目前監禁只會以「廃棄」解放（CFLAG:70 > 6 後每回合 20〜40%，CFLAG:70 由 CALC_GANGBANG "監禁" 每回合 +1，晝夜都會 KIDNAPPING）；
  二次脅迫的 :166 分岐與 :123 同條件 → 到達不了；:290 `IF LOCAL == 1` 在未選パイズリ時看的是發生機率值（恰為 1 時出胸射文）；
  :248 `PRINT る痛みの中、` 不換行、與下一行相連；KIDNAPPING 的 `SELECTCASE RAND(35)` 各 CASE 全被註解 → 恆 INTIMIDATION_RAPE（RAND 仍消耗）。
  **夜這い**：YOBAI_SELECT_PLAY 的 `CALL CLEARRANDCHOOSE`（:545）覆寫 YOBAI 的候補清單 → YOBAI_EVENT 在 SELECT_PLAY 之後回 -999（:275）時
  REROLL 會從プレイ内容（1／2／4／8／16／32）抽 TARGET（原作照做；角色不存在時原作報錯 → 停止）；YOBAI_EVENT 的條件把淫乳寫成
  `TALENT:淫乳 * 3 + ABL:Ｃ感覚`（:160–177）→ 只有 Ｂ感覚 ≥ 3 的角色會被 YOBAI 選中但必定 -999（**S20 起改為 DEVIATION**：用 Ｂ感覚）；CASE 1 的 `GOTO V_SEX／A_SEX…`（:1098–1213）
  跳進 CASE 2／4 的標籤、執行到該 IF 分岐結束後經 ENDIF → 下一個 CASE 行 → ENDSELECT（`Instraction.Child.cs`:1805–1821）；
  `%CALLNAME:ARG%`／`%CALLNAME:MASTER%`（:1450、:1796）印的是 ARG（2／4）號角色與 MASTER 的名字（ARG 號不存在時原作報錯 → 停止）；
  HOUSHI_4 的處女喪失把 `CFLAG:206` 寫在實行者 LCOUNT（:3088–3092），對象的 CFLAG:206 不變（**S20 起改為 DEVIATION**）；HOUSHI_4／5 的 `LOCAL:124 = LOCAL:324`
  在 VARSET LOCAL 之後（:3237、:3622）→ 恆 0（**S20 起改為 DEVIATION**，見「使用者裁決 2026-10-01」）；HOUSHI_4／5 的續柄用 `ISMALE()`＝實行者的性別；Ａ系（A_LOSTVERGIN・A_SEX・HOUSHI_5）中出し
  不做 AFTER_PILL／NINSIN；實行者疲勞寝落ち（:949、:960）的 RETURN 連最後的 `_ABLUP, 1`（:2645）也跳過；YOBAI_ACTION 結束時 TARGET 留在對象。
  **子触手**：SMALL_TENTACLE_ATTACK 的 `ISHOLE()`（:105）看的是呼叫時的 TARGET 而非候補；成功襲來不減 FLAG:44（子触手留著）（**S20 起改為 DEVIATION**：成功也 −1）；
  Ｖ襲來的處女喪失直接寫 `TALENT:処女 = -1`・`CFLAG:206 = 1`（不呼叫 LOSTVIRGIN），之後 `処女 < 1` 成立 → 以精液 0 呼叫 AFTER_PILL／NINSIN_HANTEI。
- S19 悪堕ちキャラ照原作的怪處（`強制発生イベント/FORCE_悪堕ちキャラの淫謀.ERB`、`ゲーム内_戦闘処理/`；Python：`eragvt.game.akuoti`、`battle.*`）：
  **戰鬥**：ACTION.ERB:37–38 每次行動把 FLAG:10／11 設 0 → 悪堕ち戰中 `TENTACLE_ACCESS` 指向不存在的 `TENTACLE_BOSS_0_*`，TRYCALLFORM 不發、
  NAME／GETNAME 印出／回傳原作的錯誤字串「【エラー：BOSS_0に対するTENTACLE_ACCESS('GETNAME')関数失敗】」（例：時間切れ文 `BATTLE_COM_AFTER.ERB`
  的第二個 NAME 未分岐、受精時 NINSIN_HANTEI:150–151）；勝利時 :314 FLAG:110 = 0 → 之後 EVENTEND 以ボス（FLAG:11 = 0）處理報酬；
  敗北／時間切れ後 FLAG:110 留 1 → 淫紋陥落（INMON_RECOVERY:873–877）走 GET_LASTBOSS_ERB_NUM（2）；TENTACLE_SAKUSEI 用前一次的 RESULT
  （SYASEI_POINT 的 LOCAL:0 或 PALAM_UP 最後的 PALAM_HOSEI 值）；SEX_COMEX_RANDOM 的 SETBIT 把 A-1 寫成 B（:66–74）；
  遭遇率アップ（ENCOUNT_ENEMY:81–86）會把 FLAG:111 換成幽閉中（CFLAG:0 = 1）的角色 → 該戰敗北時兩分岐都不符、不幽閉不受辱直接結束。
  **淫謀**：女を攫う分岐（:1230–1316）`IF 1;RAND:3 == 0` 恆真、不設經驗／V_SEX，:1295「腰を振り続ける%LOCALS:3%%PRINT_TRANSCALLNAME%」照字面相連；
  動画拡散（:934–992）的留言寫入 LOCALS:0〜4、顯示 LOCALS:1〜5 → 第 1 則永不顯示、第 5 行只有空白；被調教系（:1609–1710）FLAG:111 直接設
  CFLAG:21（不經 CFLAG:240 對照）且不還原，沒有聖処女／ISHOLE／淫紋／陥落判定；`LOCAL:2`（:1700）恆 0 → 搾精強化不發生。
  **防衛力為負**：BIRTH_AUTO_RANDOM（PREGNANT_SOURCE_NINSIN.ERB:737）扣防衛力不設下限，在 DAILY_DEFENCE_CHANGE（SHOP_TURNEND:122）之後
  （:166）→ 次回合 AKUOTI_ATTACK（:110）的 `SQRT(FLAG:852)` 對負數 → 原作 CodeEE（`reference/emuera-1824/Emuera/GameData/Function/
  Creator.Method.cs`:1078）錯誤停止；Python 照樣丟出 ValueError（Web 停止）。僅在有悪堕ちキャラ且苗床出産發生後的ゲームオーバーモード出現
  （`--corrupt 3` 模擬 250 局中 151〜178 局）。**S20 起改為 DEVIATION**（使用者裁決：SQRT 當 0，見下）。
- [x] ~~S19 顯示：`AKUOTI_EVENT` 動画拡散的 FONTITALIC 不反映~~（S20：使用者裁決 2026-10-01 支援斜體，`akuoti._robot_checkbox` 照 :810–815 以太字＋斜體顯示）。
- S20 襲撃／救援イベント戰照原作的怪處（`イベントから派生する特殊戦闘/`；Python：`eragvt.game.raid`）：
  `RAID_RESCUE` 的 LOCAL:1（:31 試行回數）是靜態 LOCAL，只有 :35「見つからない」路會留下 999 → 之後每次 RAID_RESCUE 都立刻「気のせい」結束；
  `RAID_ATTACK`:15 `ISHOLE()` 看呼叫時的 TARGET 而非候補；救援 2（女子高）`RAND:7` 不會出 7 → 「自衛隊員らしき女性」不出現；
  ~~3003／3004 的 MISSION_CHECKER 未受凌辱而敗北判為「成功」~~（S26b 訂正：S20 的解讀忽略了外側括號。3003:78／3004:208
  `98 == 2 || (98 == 0 && (21 & 3) || …)` 的括號內是獨立部分式〔`ExpressionParser.cs`:404–414〕→ 敗北一律「失敗」，`raid._checker_idol` 已修正）；
  3004 TURNEND 的白濁シャワー（:344–354）只 RESETCOLOR 不 FONTREGULAR → 其後文字保持太字；3002 繁殖袋路 :25 `PRINTFORM`（無換行）
  與下一行相連；救援 5（触手洞窟）以 FLAG:111 == 0 為條件（同回合 AKUOTI_EVENT 留下的 FLAG:111 會讓 `5 触手洞窟.ERB`:146–302 的 CASE 0／1／2（知性 > 600）不加任何シチュエーション，ターン上限照設）；
  `CLOTHDATA※イベント専用装備.ERB` 的 `@CLOTH_STATUS_991` 定義兩次（:73／:88），引擎用先定義的 :73（HP0）；3004 以外 FLAG:45 的 992 インナー
  走 CATCH 既定值（HP80・SEITAISEI95）；FLAG:999 ≠ 0（デバッグ以外の値も）時 FLAG:45 不抽選 → EVENT_BATTLE_SITUATION_0 不存在的錯誤路。

- S24 コンフィグ／GLOBAL 照原作的怪處（`eragvt.game.config`，`docs/wiki/era/flow.md` §10）：
  **GLOBAL:3 未設定的覆寫**：初次啟動（無 global 檔）時從 CONFIG [1]／[9999] 或 フィルタ [200] 存下的 GLOBAL，其 GLOBAL:3（全域資料版本）仍是 0
  （只有 UPDATE_GLOBAL 會設 408）→ 下一次 UPDATE（新遊戲開局・讀檔）的 UPDATE_GLOBAL:21–31／:32–36／:56–66 把 GLOBAL:11〜14 改成 4／31／88／5、
  GLOBAL:15 = 0、GLOBAL:4 反轉 9 個 bit，玩家第一次存的設定被蓋掉（第二次起正常）。CONFIG [2] 或 MODE_SELECT [200] 先跑過 UPDATE_GLOBAL 就不會發生。
  **S57新增影響／S59已裁決修正**：成就也會首次建立版本0的global；`ERB/バージョン間互換処理.ERB@UPDATE_GLOBAL:44–53`將111–170搬到211–270，會覆寫剛取得的成就。已補版本0／408測試與完整入口查證，見[成就](../era/achievements.md)。使用者2026-10-05同意：僅確定不存在全域檔時以GameIdentity.version初始化GLOBAL:3；既有檔仍遷移，已有損毀檔不當新檔。上述首次設定覆寫因此只保留為原作／既有版本0檔行為。
  **性嗜好フィルタ的初期值**：無 global 檔時 FLAG:850 = 0（全部 ○）；一旦有 global 檔，UPDATE 一律 FLAG:850 = GLOBAL:4，而 GLOBAL:4 經上述反轉後
  （既有版本0檔遷移後）是「淫紋サブ 5 項・拡張度表示・極端な拡張・極端な膨乳・極端な太さ」為 ×。MOB_FLAG 也一律 = MOB_GLOBAL（從未存過雑魚フィルタ時只有 MOB_GLOBAL:0:1 = 100，其餘雑魚 0%）。
  **CONFIG_F [22]**（CONFIG_GLOBAL_MANIAC.ERB:195–196）：Wingdings 設為 × 時清除的是 bit 1（ふたなり）而非 bit 11。
  **CONFIG("mainmenu")**：[999]／[9999] 不顯示但可輸入（:417–436 只控制顯示）；開局時在此改的 FLAG:800〜805 會被之後的 CONFIG_INIT 覆寫。
  **TENTACLE_MOB_901_GETNAME**：雑魚フィルタ畫面顯示名稱時也會把 TFLAG:17 的 3／5 改成 -1（:9–13）。

- S27 ラスボス・結局照原作的怪處（`docs/wiki/era/lastboss.md`）：**完全殲滅不經 @EVENTEND**（`BATTLE_COM_AFTER.ERB`:306 在 SOURCE_CHECK 中
  `BEGIN TURNEND`：該戰沒有經驗・報酬・FLAG:700 = 0 等，其餘角色照常行動後 ENDING_2）；**Ｋ觸手幽閉用Ｃ觸手的 PALAM 補正**
  （`COMMON_TENTACLE_DATA.ERB`:338–339 呼 `TENTACLE_BOSS_{CFLAG:21}_PALAM_HOSEI`）；**ラスボス戰的 TENTACLE_LEVEL** 以 FLAG:4 數存活
  （FLAG:10 = 1 → TENTACLE_SURVIVE "NUM" 走ラスボス側：撃破數 = FLAG:3 − 1 = 6）；**ENDING_2 的 LOCALS:3 判定**（:336 `IF LOCALS:3 == ""`
  永真 → 悪堕ちキャラ每次覆寫 LOCALS:1）；**クリア後必定經引き継ぎ**（ENDING.ERB:29–69 `JUMP SUCCESSION`，沒有回標題的路；
  讀クリアデータ〔FLAG:64 > 0〕也直接 `JUMP ENDING` → 引き繼ぎ）；**ラスボス出現後的悪堕ちキャラ戰**中 TENTACLE_ACCESS 走ラスボス側
  （FLAG:11 = 0 → 錯誤字串），SOURCE_CHECK:1154 的素股焦らし REACTION_REF 不發 → 共用 RESULT:0。

## 使用者裁決 2026-10-01（`# DEVIATION:`，S20 實作）

- [x] **防衛力為負時 SQRT 當 0**：`AKUOTI_ATTACK`:20 的 `SQRT(FLAG:852)` 在 FLAG:852 < 0 時以 0 計算（原作 CodeEE：
  `reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs@SqrtMethod`:1074–1080）。（Python：`turnend.akuoti_attack`）
  **延伸**：緊接的 `AKUOTI_EVENT`:42／:45／:58／:465 的 `SQRT(FLAG:852)` 同樣當 0（`akuoti.akuoti_event`；2026-10-02 使用者確認，見下）。
  `戦闘イベント.ERB`:65 `SQRT(FLAG:852 + 625)` 也於 S21 比照（D3，見「使用者裁決 2026-10-02」）。
- [x] **クズ市民脅迫クールダウン**：CFLAG:72（原作只設 8、無遞減）在 EVENTTURNEND 的 INTIMIDATION 判定（`SHOP_TURNEND.ERB`:90–101）之前
  每回合（半日）> 0 則 −1。（Python：`turnend.event_turnend`）
- [x] **夜這い淫乳條件**：`YOBAI_EVENT`:160–177 的 `TALENT:淫乳 * 3 + ABL:Ｃ感覚` 改用 `ABL:Ｂ感覚`。（Python：`yobai.yobai_event`）
- [x] **夜這い奉仕的フェラ経験**：HOUSHI_4／5 的 `LOCAL:124 = LOCAL:324`（:3237、:3622）改用 VARSET LOCAL 之前的 LOCAL:324
  （口內射精時フェラ経験 +1，與 :1738／:2063 一致）。（Python：`yobai.yobai_houshi_4／5`）
- [x] **夜這い HOUSHI_4 處女喪失原因**（Part C1）：:3088–3092 的 CFLAG:206 改寫在失去處女的對象（TARGET = FLAG:799），值的條件
  `LOVER_F(LCOUNT, FLAG:799)` 不變。（Python：`yobai.yobai_houshi_4`）
- [x] **子触手襲来**：`SMALL_TENTACLE_ATTACK` 襲擊成功（:108–109）時也 `FLAG:44 -= 1`（同失敗分岐 :88／:95）。（Python：`small_tentacle.small_tentacle_attack`）
- [x] **斜體**（Part C2）：FONTITALIC 反映到 `TextOutput`（`Segment.italic`、Web 以 CSS `font-style: italic`），FONTREGULAR 同時解除太字・斜體
  （`GameProc/Function/Instraction.Child.cs`:1084–1121）。已不是偏離，記錄於此備查。

## 使用者裁決 2026-10-02（S21 實作）

- [x] **悪堕ちキャラ幽閉的 PALAM_HOSEI 殘值照原作**：不是偏離。RESULT 改為共用陣列（`docs/wiki/python/result.md`）。
- [x] **防衛力為負時「當 0」全面延伸**（`# DEVIATION:` 使用者裁決 2026-10-02）：
  - D1：`AKUOTI_EVENT`:42／:45／:58／:465 的 `SQRT(FLAG:852)` 以 0 計算（S20 實作，此次確認）。（Python：`akuoti.akuoti_event`）
  - D2：:58／:465 損失式中防衛力的項（`FLAG:852 * 5 / 100`、`* 10 / 100`）在 FLAG:852 < 0 時也代 0 → 損失 0（原作是負的損失，
    :458／:1603 `FLAG:852 -= DAMAGE` 讓防衛力增加並印「防衛力が-n低下した！」）。（Python：同上）
  - D3：`戦闘イベント.ERB`:65 `PERFORM_CHEERS_FIRST_HANTEI` 的 `SQRT(FLAG:852 + 625)` 括號內為負時以 0 計算（原作 CodeEE：
    `reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs@SqrtMethod`:1074–1080）。（Python：`battle.cheers.perform_cheers_first_hantei`）
  - D4：`ACTION_GATHER_INFORMATION.ERB`:142 的 `SQRT(FLAG:852)` 在 FLAG:852 < 0 時以 0 計算（S28a 實作：`gather._rumor`，`# DEVIATION:`）；
    `PASTIME_悪堕ち遭遇.ERB`:19 於 S28c1 比照實作（`pastime.akuoti_encounter`，`# DEVIATION:`）。
- S21 照原作的怪處（`eragvt.game.corruption`、`battle.source_check`、`battle.restraint`）：
  **悪堕ち容姿**：CORRUPT_CHANGE_LOOKS_MAIN 的 `SETBIT CFLAG:80, n`、CORRUPT_CHANGE_LOOKS 的 `CSTR:1 == CSTR:0`・`CFLAG:42 = 0`、
  RECOVER_CORRUPTION 的 `CFLAG:81 == 0b1111`・`CLEARBIT CFLAG:80, 2` 都寫／讀 TARGET 而非 ARG；變身後名改竄不看 CFLAG:2（未登錄則 CSTR:0 變空）；
  髮色候補 `232//200//0` 行尾有 TAB → SETCOLOR_BY_STR 不上色；NANORI_FINAL 的性格引數是未代入的靜態 LOCAL（恆 0 → 強気系）、
  `REPLACE LOCALS:1,…` 結果進 RESULTS（LOCALS:1 不變）。完堕ち時 `CFLAG:42 = 0` 會順帶拆掉触手拘束具。
  **触手拘束具**：SUBEVENT_BATTLE_ACTTENTACLECLOTH 以 LOCAL 的編號（0〜11）當 PALAM_HOSEI_TALENT／性格補正的 PALAM 番號與 COMMON_PALAM 的
  添字（:130／:134／:155）→ LOCAL:4〜11 加到 PALAM 4〜11（潤滑〜恐怖 10〜17 只有 10／11 收到苦痛／恐怖的值）；FOR 到 12 但 LOCAL:12 恆 0。
  素股焦らし失敗的處女喪失（COMF103:156–158）直接寫 `TALENT:処女 = -1`・`CFLAG:206 = 2`（不呼叫 LOSTVIRGIN）。
  拆除只能經 SHOP [112] 衣裝設定的 `CLOTH_RESETTING_TENTACLECLOTH`（觸手の欠片 1 個，未移植 UI；預設路徑＝不操作）或完堕ち／イベント戦的衣裝還原。
- [x] **開局的デフォルト悪堕ち**（S21）：`オープニング処理.ERB`:241–250 的 CORRUPT_CHANGE_LOOKS_MAIN 已接上，但 `event_first` 無輸出／narration
  （同「開局 MESSAGE_FIRST」），其畫面輸出丟棄。預設開局不會發生（無悪堕ちキャラ）。（Python：`opening.event_first`）
  **使用者裁決（2026-10-02）**：維持現況。

## S28a 照原作的怪處（非偏離，備查）

- `ACTION_SUPPORT.ERB`:38–58：FLAG:43 ≥ 3 時不乘係數，消費 = MAXBASE 全量（經 SYOUHI_KEIGEN）。
- `ACTION_GATHER_INFORMATION.ERB`：`#DIM NAKADASHI` 靜態不歸 0（一次中出し後，之後素股都走 AFTER_PILL／NINSIN_HANTEI）；:933 比較 "お調子者の男"
  但 LOCALS 是 "お調子者な男" → 恆走 ELSE；:52–58 スケジュール「仲間の捜索」不能時印「代わりに事件の捜査」卻設 RESULT 0（噂話）；
  :1048–1049 只顯示「探索度が上昇」不呼 RESEARCH_PROGRESS；:389 スタンロッド的傷害只顯示不扣；カラダ選單 [1]／[3] 不檢查巨乳／性別。
- `ACTIONsub_TRANSFORMATION_SELECT.ERB`:37–39 先把 CFLAG:1 設 1 再設 0（與原值無關）；[9]／[10] 只改記憶體 GLOBAL（不 SAVEGLOBAL）。
- `CALC_CHARM_FEAT.ERB`:34 `TALENT:平凡` 讀 TARGET；`SENGIUP`:761 `IF CFLAG:34` 讀 TARGET。
- `ACTION_TRAINING.ERB`:274 スケジュール不正時看 CFLAG:111（特別活動）而非 110。

## S28b 照原作的怪處（非偏離，備查；`docs/wiki/era/actions.md`「S28b 補足」）

- `特別活動/SEISAN_INIT.ERB`:8 アルバイト「失敗」に `特活報酬_アルバイト_成功` の係数（`_失敗` は未使用）。
- `SEISAN_1_RESEARCH.ERB`:57（研究所助手の知性倍率）・`SEISAN_6_IDOL_ACTIVITY.ERB`:56–57（路上ライブ +200）は表示額のみ、MONEY は CALC_SEISAN の稼ぎ。
- `CALC_SEISAN.ERB`:80–85 公衆便所の固有稼ぎは野良犬（表示「１＄たりとも得られなかった」）でも MONEY に入る。
- `SEISAN_5_TOILET.ERB`:56–57／:79–91 路地裏放置は AFTER_PILL（終端 0）・NINSIN_HANTEI 後の RESULT:0 で妊娠判定・経験を計算；:47 LOST_VIRGIN は常に 0。
  `SEISAN_2_PEST_CONTROL.ERB`:70 も AFTER_PILL 後の RESULT:0（＝0）で NINSIN_HANTEI(2, 50, 200)。
- `SEISAN_8_IDOL_LIVE.ERB`:12–14 CHARM_BASE 等は静的変数：失敗・絶頂失敗では前回値（初回 0）で魅了経験が上がる。
- `SEISAN_4_PORN_VIDEO.ERB`:46／:50／:82 `\@TALENT:変身能力 == 1?#…\@` は変身能力 1 のとき空文字（変身できない人に「すぷらったー☆」等）。

## S28c1（自由行動；待使用者裁決）

- [x] **夜間排程全為學校 → 隨機去處**（`ACTION_PASTIME.ERB`:33–43；**已裁決 2026-10-03：照作者意圖**）：原作 :34 註解「全てダメなら行先ランダムにする」
  並設 `RESULT = 1`，但 (1) 迴圈次數用了 CFLAG:113 的項目編碼（`NUM_SCHEDULE_F`，項目 9 個時約 10^16），全為學校時事實上停住；
  (2) 迴圈內 `CALL RES_SCHEDULE` 每次把 RESULT 蓋回 0，跑完也是夜裡上學。只要有非學校項目，原作在第一個非學校項目就 BREAK（正常情況夜裡不會上學）。
  Python 只跑項目數次（實行番號一巡），全為學校則 RESULT = 1 → 夜間隨機（:59–67）。（Python：`pastime._schedule_night`）
- [ ] `W07` **catalog 不可時的狀態變化**：本文中心函式（`PASTIME_HOOK_LINES`）在 Null narration 時，Pool 的淫乱分岐水着（CFLAG:270）與授業
  （Classwork_CL／PE 的 EXP・処女・CFLAG:42）依本文亂數決定 → 停止（NotImplementedError）；其他以 `_FALLBACKS` 照 ERB 更新。Web 預設 catalog 可執行，
  不會發生。（Python：`pastime._FALLBACKS`）
- S28c1 照原作的怪處（非偏離，備查）：見 `docs/wiki/era/actions.md`「S28c1 補足」。

## S28c2（自由行動的本編；待使用者裁決）

- [ ] `W07` **catalog 不可時停止**：ナンパ・酒ナンパ・痴漢的本編（`PASTIME_ナンパ.ERB` 等 11 函式）只以 catalog 執行（`pastime_nanpa._run`），
  Null narration（無原作 ERB）時 NotImplementedError → Web 停止（原作不會停）。Web 預設 catalog 可執行（72 行 hook 全部可執行，
  `tests/test_pastime_nanpa.py::test_nanpa_hook_table_matches_erb`），不會發生。
- 備查（非偏離）：原文`ERB/ゲーム内_イベント発生/自由行動中イベント/PASTIME_ナンパ.ERB@PASTIME_NANPA_RAPE:3086`與`PASTIME_酒ナンパ.ERB@PASTIME_SAKE_NANPA_RAPE:1696`的`ENCOUNT_CITIZEN(6001)`已於S36接通：`narration/hooks.py:288,310,369`→`game/pastime_nanpa.py@hook_encount_citizen:98–102`→`game/battle/citizen.py@encount_citizen:8–40`，已執行市民遭遇狀態設定，不再屬未移植停止；定向證據`tests/test_citizen_battle.py:191–195`。
  照原作的怪處見 `docs/wiki/era/actions.md`「S28c2 補足」。

## S33（雜魚戰）

- 原作的重複函式、公式索引與省略參數照引擎規則保留，沒有自行修正；依據見 `../python/mob-battle.md`。
- 無 catalog 時雜魚顯示明確停止，沿用既有「catalog 不可時停止」限制；Web 預設提供原文 catalog。

## S48：自訂一人稱重入

- [x] **自訂一人稱重入保留完整編碼、性格預設重設字形**：S47 報告建議查明意圖後修正這兩項，使用者隨後要求選下一步繼續，本階段依該授權處理。
  `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_SELFCALL:1216–1217、1466–1475`
  將自訂碼種類 19 當標準碼，直接確認會截去高位；Python 保留入口原始碼，未改設定直接確認維持 `CFLAG:8`／`CSTR:4`。
  同函式 `:1304–1322` 未重設自訂重入的字形 3／4，性格預設會越界；Python 依首次自訂 `:1324–1326、1399–1400`
  切回預設的成功路徑重設為字形 0。新選擇取代原碼，取消不寫角色；不從非可逆顯示字形重建讀音。
  原作讀碼依據：`ERB/口上/口上システム関係/SELF_CALL.ERB@SELF_CALL_SUBSTRING:161–165`；其餘怪處保留，見 `../era/self-call-setting.md`。

## S42：醫療室

- [x] **S42隱藏手術確認修復與未完成支線截斷（2026-10-04使用者裁決）**：
  `ERB/ゲーム内_行動実行処理/ACTIONsub_DRUG_PREPARATION.ERB@DRUG_PREPARATION:229–276`
  明示0是／1否，但INPUT在標籤之前；非0後反覆PRINTW，不再INPUT。
  Python依最新裁決：0照原手術、1提示AMPUTEE原作移植未完成並停止、其他值提示後重讀；不扣資源、不改角色。
  原否分支是另提NPC處置方案，:245–266明示移植未完而停用，AMPUTEE呼叫也註解；修復維持停用及51隱藏。
  先前「1返回」推論已被使用者「提示未完成截斷」裁決取代；透過NotImplementedError進入既有HALTED，不輸出或執行草稿事件／結算。歷史證據見[醫療室查證](../era/drug-preparation.md)。

## S60：姓名原作錯誤安全網（W08）

- [ ] `W08` `ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_NAME_RANDOM:913–920`兩次WHILE誤檢查姓氏；手輸未定義姓氏語言可使空姓永久重抽。Python明確停止，避免本機掛死；此安全網待裁決，非玩法移植缺口。
- 備查：同檔`@FIRSTSETTING_CHARA_NAME:656`允許CHARANUM角色索引，原作即越界，Python明確停止；沒有猜修為<。固定姓名順序不影響回傳、中文第二字被覆寫等其餘原作怪處均保留，詳見[角色編輯](../era/character-editor.md)。

S60b補充：tutorial的PRINTW改為明確確認請求及Enter按鈕；其他舊WAIT未全面遷移，既有等待偏離仍未完成，不能勾選結案。[範圍與驗收](generic-input.md)。
