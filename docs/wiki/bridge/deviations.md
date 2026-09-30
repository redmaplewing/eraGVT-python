# 與原作的偏離（需使用者決定）

凡是 Python 版與原作行為不同的地方（簡化、跳過、近似規則、額外保存的資料…）都列在這裡，
程式對應位置標 `# DEVIATION:`。使用者決定後，在該項註明「已同意（日期）」或改回與原作一致並刪除該項。

**2026-09-29 使用者裁決（整體）**：以下所有項目暫時維持現狀，開發繼續推進；之後的進度可能給出合理解釋。
只有在某項偏離或原作 bug **已嚴重到無法推進開發**時，才回頭評估修正方式。新增項目仍照規則登記並在 session 報告列出。

格式：`- [ ] 內容（原作：檔案@函式／reference 位置；Python：模組@函式）— 為什麼要偏離／替代方案`
ERB 路徑相對 `source/earGVP/ERB/`。

## 狀態會不同

- [ ] **亂數**：用 Python `random.Random`（可 seed），不是 Emuera 的 MT 實作；RAND 的呼叫次數也不追求一致（例：`RESEARCH_QUOTA` 的 `RAND:5` 是否短路求值）。同 seed 不會得到原作同樣的結果。（原作：`reference/.../GameData/Variable/VariableEvaluator.cs`:36–52；Python：`eragvt.state.rng.GameRng`）— 要完全一致需移植 MTRandom 並逐一核對求值順序，成本高。
- [x] ~~**開局：身體資料生成未移植**~~（S09 解決）：`CHARA_MAKE_BASE_PROFILE` 已移植（`eragvt.game.opening.chara_make_base_profile`、
  `eragvt.game.body`）。查證結果：初期セットのキャラは `NO ≠ 0`（:498 條件不成立）→ 原作本來就不生成，BASE:40–48／CFLAG:33–34 為 0
  與原作一致（`docs/wiki/era/body-profile.md`）。S10：汎用キャラ的隨機生成（:507–980）與 AGE_SETTING 的年齢指定（CSTR:204–206）
  已移植；仍未移植：角色製作／狀態畫面的手動生成（UI）、TOINT 的 16／2 進與指數表記（停止）。
- [ ] **FLASHNEWS 未移植**：新聞產生（含亂數、寫入 `SAVESTR:20`、`FLAG:60`）沒有執行，畫面顯示「（未實作）」。（原作：`インターミッション画面/SHOP_FLASHNEWS.ERB@FLASHNEWS`:3–752；Python：`eragvt.game.shop.flashnews`）
- [ ] **全域資料（GLOBAL）不讀不寫**：永遠走「真正的初次啟動」路徑（MOB_FLAG 初始化為 100、不套用 GLOBAL 的 config／性嗜好フィルタ），也不存成就等全域資料。（原作：`オープニング処理.ERB@EVENTFIRST`:29–45、`バージョン間互換処理.ERB@UPDATE`:95–130；Python：`eragvt.game.opening.event_first`）— 等設定畫面／成就功能時一起做。
  S05 起戰鬥中的 `UNLOCK_ACHIEVEMENT`（タクティカルオーダー、絶体絶命ヒロイン等）與 `GET_STATE_ABLUP` 同樣不執行（`eragvt.game.battle.core.unlock_achievement`）。
  S04 起同理不執行：`SHOP_TURNEND.ERB@UPDATE_STATUS_RECORD`:263–349（歷代最高紀錄 GLOBAL:103–131／GLOBALS、SAVEGLOBAL）與 `SHOP_TROPHY.ERB@GET_STATE_TROPHY`:398–441→`UNLOCK_ACHIEVEMENT`（成就達成訊息不會顯示）。（Python：`eragvt.game.turnend.recalc_partymember`、`eragvt.game.action.get_state_trophy`）
  S08 起同理不執行：幽閉的 `COMMON_PRISON.ERB@COMMON_PRISON_EXP`:87 `GET_STATE_EXPUP`、救出時的 `UNLOCK_ACHIEVEMENT`（271／273：
  `BATTLE_COM_AFTER.ERB`:209／240）、`MESSAGE_PRISON_PRISENTENCE_FIRST`:9（hook 為無動作）。（Python：`eragvt.game.prison.commands.common_prison_exp`、
  `battle.source_check._rescue_captives`、`narration/hooks.py` PRISON_HOOK_LINES）
- [ ] **開局的 UI 跳過**（S10 改寫）：狀態已照原作預設路徑（NORMAL → キャラメイク不設定直接 `[1000]`＝汎用キャラ 3 名おまかせ生成
  → HEROINE_PRESET `[1]` 基本セット → 序章 `[0]`，`docs/wiki/era/flow.md` §1）；剩下的偏離只有**畫面**：模式選擇／キャラメイク／
  HEROINE_PRESET／序章畫面不顯示，改為標題 `[0]` 之後的 2 択「[0] おまかせで開始（原作既定）／[1] 初期セット『特装戦隊』で開始」
  （後者＝キャラメイクで `[200]`→`[0]`→`[1]はい`→`[1000]`）。模式固定 NORMAL（MODE_SELECT 沒有預設值，[1] 是第一個選項）。
  共通設定（FLAG:5–7・820–825）永遠是 GLOBAL 不存在時的 0。（Python：`eragvt.game.opening.event_first`、`session._new_game_input`）
  開局 `MESSAGE_FIRST` 口上仍不輸出（見下「口上」）。

- [ ] **S04 未翻的行動會停止遊戲**：（出撃已於 S05 接上，戰鬥內的停止見下一項）特別活動、拠点防衛、戦闘支援（本體）、情報収集、自由行動在 `action_main` 丟 `NotImplementedError`，Web session 捕捉後進入「停止」狀態（只能按「タイトルに戻る」）。同樣停止的還有：ENDING（全ボス撃破／**11 日目夜的日數超過**）、救出直後、妊娠・育兒・幽閉・悪堕ち等 S04 無法產生的狀態、鍛錬排程（CFLAG:110）、戦闘基礎 Lv5 的變身能力獲得。（原作：`ゲーム内_行動実行処理/ACTION.ERB`:74–175 等；Python：`eragvt.game.action`、`eragvt.game.turnend`、`eragvt.game.session._advance_turn`）— 各自屬 S05 以後；影響範圍見 `docs/wiki/era/actions.md`。
- [ ] **襲撃／救援、子触手襲来 會被跳過**：`RAID_HANTEI`（DAY ≥ 3 起依防衛力的亂數）與 `SMALL_TENTACLE_HANTEI`（夜、FLAG:44 > 0）判定成立時，原作會 `JUMP RAID_RESCUE／RAID_ATTACK`（戰鬥）或 `CALL SMALL_TENTACLE_ATTACK`；這裡只印「（未實作：…が発生しましたが、スキップします）」並當作沒發生。（原作：`ゲーム内_イベント発生/強制発生イベント/FORCE_襲撃or救援イベント発生.ERB`:94–105、`FORCE_深夜の子触手襲来.ERB`:48–53；Python：`eragvt.game.turnend.raid_hantei`／`small_tentacle_hantei`／`_skip_event`）— 通常遊玩一定會遇到，若改成停止則無法連續遊玩；戰鬥在 S05／S06 接上。
- [ ] **未移植的戰鬥分岐會停止遊戲**（S05 新增、S06 更新）：戰鬥中下列情況丟 `NotImplementedError` → Web「停止」。
  S06 接上了拘束後的性攻擊、拘束中指令、絶頂／射精、敗北（→ 幽閉）與指令 6・7・16・17・69・71・72；
  仍停止的一覽見 `docs/STATUS.md`「S06 後仍會停止的分岐」（ＳＰ變身／ＳＰバースト、バースト攻擊的效果、反擊、受精成立、
  強制自慰、動画流出、幽閉後的 TURNEND、悪堕ち／雜魚／ラスボス等；拡張度 CFLAG:34 != 0 於 S11 接上，只剩羞恥プレイ的
  動画サイト視窗 `MESSAGE_SEX_VIDEO_SITE_Window`）。
  （Python：`eragvt.game.battle.*` 各處 `raise NotImplementedError`、`battle.commands.run_com` 的 `# DEVIATION:`）
  — 依規格「未移植分岐必須停止」。
- [ ] **幽閉的未移植分岐會停止遊戲**（S08 新增）：受精成立（`NINSIN_HANTEI`:140 以降，幽閉中常見）、（膨乳化的
  `SET_PROFILE` 已於 S09 接上）、ラスボス／悪堕ちキャラ 的幽閉（`TENTACLE_ACCESS_PRISON` 的
  LASTBOSS 分岐、悪堕ち的 PALAM_HOSEI）、`CORRUPT_CHANGE_LOOKS_MAIN`:24–（設定 CONFIG_CHECK_PRISON_F(4) ON 時）、`RECOVER_CORRUPTION`、
  `RESCUE_CHILD`、TS 性別變化（`TS_MtoF` 等）、ラスボス出現後的淫紋陥落、ゲームオーバーモード（`CHANGE_GAMEOVER_MODE`：ENDING_1／4／5
  的本文顯示後停止）。（Python：`eragvt.game.prison.*`、`party`、`ending`、`turnend._inmon_fall` 的 `raise NotImplementedError`）
  — 依規格「牽涉未移植系統時照 S06 慣例停止」。
- [ ] **振り解く判定的 `LOCAL:O`**（S06 新增，**需裁決**）：`ゲーム内_戦闘処理/COMMON_BATTLE_HANTEI.ERB`:241／:245
  `SIF LOCAL:5 <= 45 && LOCAL:O > 49` 的 `O` 是英文字母，全作沒有這個識別子（grep 僅此 2 處）。1.824 在執行到該行時
  報錯停止（`GameProc/Process.ScriptProc.cs`:38–42、`GameData/Expression/ExpressionParser.cs`:264–269、
  `GameData/IdentifierDictionary.cs`:645），而振り解く的％顯示（`PRINT_COMNAME.ERB`:6–13）每次都會經過這裡，
  也就是原作（1.824）一被拘束就無法繼續。本作當作 `LOCAL:0`（體力氣力殘量％）的筆誤來判定。
  （Python：`eragvt.game.battle.hantei._hurihodoku`）— 替代方案：照 1.824 停止（等同無法玩拘束），或確認 +v10 的行為。
- [x] ~~**開局身體資料未生成對戰鬥的影響**~~（S09：**不是偏離**，移到下方「原作行為」）。
- [ ] **口上的狀態副作用**（S07 更新，**需裁決**）：口上函式本身若對非 LOCAL 變數代入（CFLAG・TALENT・BASE・CSTR…，覆蓋率報告的
  「非 LOCAL 変数 … への代入」，約 300 函式；例：`★KOJO_0_16_真面目/鍛錬.ERB` 的 TRAINING 系 9 函式寫 CFLAG），catalog 判為 unsupported，
  KOJO_ROOT 當作「找不到」（-1、不輸出）。原作會輸出口上並改變狀態。（Python：`eragvt.narration.service.call_kojo`）
  — 規格 S07「口上的狀態變化不做新移植」。替代：逐一以 hook 移植這些狀態變化。

## 只影響顯示

- [ ] **口上**（S07 更新）：SHOP 一口メッセージ・行動・戰鬥中的口上改由 catalog 輸出（`eragvt.narration`）。仍未輸出的：
  unsupported 的口上（見上「口上的狀態副作用」及覆蓋率報告）、開局 `MESSAGE_FIRST`（`opening.event_first` 沒有輸出／narration 參數，
  維持 FLAG:62＝0・FLAG:900＝0 的「找不到」處理）。無 `ERB/` 目錄時回落 `NullNarrationService`。
- [ ] **口上 catalog 的實行時失敗**（S07 新增）：執行中才發現的子集外（動態 CALLFORM 的呼叫先不可執行）或引擎會報錯停止的狀況
  （除以 0、範圍外參照），catalog 會回復輸出・亂數・LOCAL，口上當「找不到」、地の文印佔位。原作會報錯停止或照常執行。
  hook（狀態變化）已執行後才失敗者無法回復，改為停止（NotImplementedError）。（Python：`eragvt.narration.service._run`）
- [ ] **口上 catalog 的顯示簡化**（S07 新增，只影響顯示）：`SETFONT`（字型名）與 `FONTITALIC`（斜體）不反映；`CLEARLINE` 只刪已完成的行；
  RESULT／RESULTS／COUNT 放在口上專用的暫存（`state.temp.narr`），與 Python 移植部分不共用（原作是全域變數；口上函式讀取呼叫前別處設定的
  RESULT 時會不同）。（Python：`eragvt.narration.runtime`）
- [ ] **SHOW_SHOP 簡化**：狀態條（`COLOR_BAR` 的色階與長度）以 20 格單色近似；`SHOW_SHOP_STATUS_SIGN`（生理周期・疲勞等標記）、隊伍列表的欄寬對齊與第 2 行詳細、控えメンバー一覽未移植；`SHOP_NG_ACTION_INFO` 的紅字在函式結尾重設顏色（原作不重設）。（Python：`eragvt.game.shop`）
- [ ] **未實作的選單**：`[50]`、`[110]`〜`[180]`、`[700]`、`[800]` 只顯示「（未實作）」。（`[100]` 已於 S04 接上行動執行。）
- [ ] **WAIT／PRINTW 不阻塞**：Web 一次顯示到下一個 INPUT 為止，WAIT 位置以虛線標示，不需按鍵繼續。（Python：`eragvt.game.session`、`eragvt.web`）
- [ ] **存檔格式與檔名**：JSON（`saves/saveNN.json`），不是 Emuera 的 `.sav`；存檔說明文字（日時＋`@SAVEINFO`）與一覽格式照原作。
- [ ] **Web 專用按鈕**：頁尾「タイトルに戻る」（重建 session）是原作沒有的。
- [ ] **無效輸入訊息**：Emuera 以「刪一行＋暫時行」顯示「無効な値です」，這裡以一般行輸出。
- [ ] **SHOW_SHOP 的 TARGET == CHARANUM**：原作會因越界參照報錯，這裡視為「編成外」重新選擇 TARGET（`eragvt.game.shop.show_shop`）。

- [ ] **鍛錬畫面**：`SHOW_STATUS_BASE_TRAINING` 的素質一覧 `SHOW_STATUS_TALENT`（`ヒロイン関連/CHARA_STATUS.ERB`:251–953）未顯示；體力等條以 SHOW_SHOP 同樣的近似條顯示。`PRINTLC` 以 cp932 位元組數補空白到 26，不做原作依字型寬度削減尾端空白（`GameView/EmueraConsole.Print.cs@CreateTypeCString`:383–425）。（Python：`eragvt.game.action.show_status_base_training`、`eragvt.text.TextOutput.print_lc`）
- [ ] **戰鬥畫面簡略顯示**（S05 新增）：`@SHOW_STATUS`（`ゲーム内_戦闘処理/BATTLE_SHOW_STATUS.ERB`:3–351，含
  `ヒロイン関連/CHARA_STATUS.ERB@SHOW_STATUS_BASE_DISPBATTLE`、`SHOW_TRAIN_PALAM_STATUS`、`CLOTH_BATTLE_DISPHP`、
  `SHOW_DISTANCE_WINDOW`）只顯示名稱・Lv・體力／氣力／性耐性條・EX 值・狀態・心境・敵名 Lv・距離・剩餘回合・
  敵體力／射精（解析度不足時 ？？？）・油斷・敵能力・解析度；距離適性、スタイル、衣裝耐久、PALAM 表、距離視窗未顯示。
  這些函式內沒有代入與 RAND（grep 確認），不影響狀態。`[800]` ステータス畫面（`SHOW_STATUS_CHARA_SELECT`，5 頁）只顯示
  「未移植」一行。`SHOW_USERCOM` 只移植「不分類」版（`BATTLE_COM.ERB`:379–568，基本設定 FLAG:801 bit2 = 0），
  《危険度》的顏色照 `FORECAST_OUTPUT_SETCOLOR`。（Python：`eragvt.game.battle.train.show_status`／`show_usercom`／`usercom`）
- [ ] **性攻擊的地の文**（S06 新增、S07 更新）：S07 起 `地の文/MESSAGE_SEX*.ERB`、敗北 `MESSAGE_BATTLE_END_LOSS`、射精・處女喪失・
  ヒロイン側性攻撃的地の文由 catalog 輸出本文，其中的狀態變化行經 `narration/hooks.py`（140 行，對照 sexmsg）依 ERB 順序執行、
  RAND 也照 ERB 順序抽（亂數序列與 S06 不同）。catalog 不可執行（`MESSAGE_SEX_SPCOM7` 的 CFLAG:34 > 0 分岐等）或 Null 時才印
  「〈地の文：函式名〉」並走 S06 的 Python 移植（`eragvt.game.battle.core.run_chinobun`、`sexmsg._catalog`）。
- [ ] **幽閉的地の文與淫紋顯示**（S08 新增，只影響顯示）：`地の文/MESSAGE_PRISON.ERB`、`MESSAGE_OTHER.ERB` 的 PRISON 系、
  `MESSAGE_KYUUSHUTU.ERB`、刻印地の文由 catalog 輸出（狀態變化行 21 行經 `narration/hooks.py` PRISON_HOOK_LINES：FLAG:900、
  TALENT:膨乳改造値、TS 呼叫 → 停止、成就 → 無動作）；catalog 不可執行（Null 等）時印「〈地の文：…〉」並只做末尾的 KOJO_ROOT
  （`MESSAGE_KYUUSHUTU` 則以 Python 輸出同文）。淫紋圖樣 `CHARA_TATTOO.ERB@PRINT_TATTOO`:239–474／`@TATTOO_LIB`（無代入到狀態、
  無 RAND）因 `CHKFONT`（依安裝字型）catalog 不支援，改印「〈淫紋：PRINT_TATTOO n〉」一行。
  （Python：`eragvt.game.prison.*` 的 `run_chinobun`、`eragvt.game.tattoo.print_tattoo`）
- [ ] **INPUTS 只能輸入整數**（S11 新增）：Web 的輸入是整數，`MESSAGE_SEX_SPCOM7`:1236 的 INPUTS 以 `str(整數)` 比較
  （原作可輸入任意字串／空字串：`GameView/EmueraConsole.cs`:722–728）。只有 "1" 有意義，實際選項不變。
  （Python：`eragvt.game.battle.sexmsg.msg_spcom7`）
- [ ] **HTML_PRINT 的子集**（S11 新增，只影響顯示）：只支援原作用到的 `<font color>`／`<nonbutton title>`（tooltip 以 Web 的
  title 屬性顯示）；其他タグ停止。（Python：`eragvt.text.TextOutput.html_print`）
- [ ] **Web 停止狀態**：遇到未移植處理時顯示「（未實作のため停止しました：…）」並停住，是原作沒有的畫面（見上「S04 未翻的行動」）。
  S08：全滅（ENDING_1）與ソロ的 ENDING_4／5 在顯示結局本文後，因ゲームオーバーモード未移植而以此畫面停止（「タイトルに戻る」）。

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
  （`GAPING.ERB@PRINTFORM_GAPING_NOW`:800–808；呼叫者是 FLAG:801 bit 5 的戰鬥 PALAM 表示〔既定 OFF〕與ステータス畫面 PAGE5〔未移植〕），
  所以既定遊玩時從 0（rank 0）開始、第一次被插入就大幅上升（例：0 → 55、膣径 +3.8 cm）；GET_*_GAPING_EXP 的靜態 LOCAL 在 ARG < 3 時沿用
  上次值（:1018–1022）；V_GAPING 等的早期 RETURN 不還原 TARGET；いちゃラブ的処女地の文（MESSAGE_SEX.ERB:1301）因 SEX_V:221 先把
  処女改成 −1 而不會出現。**使用者裁決（2026-09-30）**：照原作，不在開局設定初期值（狀態畫面 PAGE5 移植後自然會在顯示時設定）。
