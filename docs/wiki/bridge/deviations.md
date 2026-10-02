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
- [ ] **FLASHNEWS 未移植**：新聞產生（含亂數、寫入 `SAVESTR:20`、`FLAG:60`）沒有執行，畫面顯示「（未實作）」。
  ゲームオーバーモードの固定ニュース（`FLAG:60 = 10001`，:91–；DAY:2 起算的經過ターン數）也不顯示（FLAG:60／DAY:2 照原作設定）。（原作：`インターミッション画面/SHOP_FLASHNEWS.ERB@FLASHNEWS`:3–752；Python：`eragvt.game.shop.flashnews`）
  S14：動画流出的 CFLAG:284 在 FLASHNEWS 只由 `@FLASHNEWS_CHOOSEIDOL`（"内容"，:974–982）讀取，用來加重「動画流出」新聞的
  RANDCHOOSE 權重（結果只進新聞本文／SAVESTR:20），屬於未移植的新聞產生本體，不另外移植。
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
- [x] ~~**襲撃／救援 會被跳過**~~（S20 解決）：`RAID_HANTEI` 成立時照原作 `JUMP RAID_RESCUE／RAID_ATTACK` → イベント戦（`eragvt.game.raid`）。ラスボス出現後（FLAG:100 = 0）の襲来は ENCOUNT_BOSS のラスボス分岐が未移植のため停止。
- [ ] **未移植的戰鬥分岐會停止遊戲**（S05 新增、S06 更新）：戰鬥中下列情況丟 `NotImplementedError` → Web「停止」。
  S06 接上了拘束後的性攻擊、拘束中指令、絶頂／射精、敗北（→ 幽閉）與指令 6・7・16・17・69・71・72；
  S16 接上 ＳＰ変身（73）・ＳＰバースト（70）・ＳＰフルバースト（74）與バースト攻撃（TCVARn:217）的全部補正；
  仍停止的一覽見 `docs/STATUS.md`「S06 後仍會停止的分岐」（反擊、受精成立、
  強制自慰、動画流出、幽閉後的 TURNEND、悪堕ち／雜魚／ラスボス等；拡張度 CFLAG:34 != 0 於 S11 接上，只剩羞恥プレイ的
  動画サイト視窗 `MESSAGE_SEX_VIDEO_SITE_Window`）。
  （Python：`eragvt.game.battle.*` 各處 `raise NotImplementedError`、`battle.commands.run_com` 的 `# DEVIATION:`）
  — 依規格「未移植分岐必須停止」。
- [ ] **幽閉的未移植分岐會停止遊戲**（S08 新增）：（受精成立・苗床出産・`RESCUE_CHILD` 已於 S13 接上；膨乳化的
  `SET_PROFILE` 已於 S09 接上）、ラスボス／悪堕ちキャラ 的幽閉（`TENTACLE_ACCESS_PRISON` 的
  LASTBOSS 分岐、悪堕ち的 PALAM_HOSEI）、`CORRUPT_CHANGE_LOOKS_MAIN`:24–（設定 CONFIG_CHECK_PRISON_F(4) ON 時）、`RECOVER_CORRUPTION`、
  TS 性別變化（`TS_MtoF` 等）、ラスボス出現後的淫紋陥落（ゲームオーバーモードは S12 接上；ENDING_1 的
  エンドレス分岐 :266–293 仍停止）、悪堕ちキャラの淫謀（`AKUOTI_EVENT`，防衛力 0 時悪堕ちキャラ一在就必定發生）。
  （Python：`eragvt.game.prison.*`、`party`、`ending`、`turnend._inmon_fall`、`turnend.akuoti_attack` 的 `raise NotImplementedError`）
  — 依規格「牽涉未移植系統時照 S06 慣例停止」。
- [ ] **妊娠・子供的未移植分岐會停止遊戲**（S13 新增）：TS 変身キャラ妊娠時的女體化（`TRANS_SEX.ERB@TS_MtoF`：
  `PREGNANT_SOURCE_NINSIN.ERB@NINSIN_TS_FIX`:263–267、`@NINSIN_FLAG`:248–256）、手入力（INPUTS）的選項：子供名字 [1]
  （`PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD`:419–427、`@BIRTH_DAUGHTER_TENTACLE_ORIGIN`:235–243）、変身後名 [1]〜[4]（含
  ランダム命名畫面 `FIRSTSETTING_RANDOMNAMING(_ALL)`）、変身後呼び名・かけ声・名乗り口上的「自分で設定」
  （`FIRSTSETTING_CHARA_TRANSFORMATION.ERB`）、デバッグモード的妊娠確率輸入（`NINSIN_HANTEI`:125–138）。
  （Python：`eragvt.game.battle.ninsin`、`eragvt.game.child`、`eragvt.game.firstsetting` 的 `raise NotImplementedError`）
  — Web 只能輸入整數（見下「INPUTS 只能輸入整數」）；隨機命名畫面與 TS 系統屬之後的階段。
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
  S14：含 INPUTS 的函式以「重放」執行（`run_function_gen`，`docs/wiki/python/narration.md`），若 INPUTS 之前已有 hook／KOJO_ROOT 的
  狀態變化則無法重放 → 停止（本作現有的 INPUTS 函式 `MESSAGE_SEX_SPCOM7`／動画サイト在 INPUTS 前都沒有狀態變化）。
- [ ] **口上 catalog 的顯示簡化**（S07 新增，只影響顯示）：`SETFONT`（字型名）不反映（`FONTITALIC` 斜體 S20 起反映：`TextOutput.set_italic`）；`CLEARLINE` 只刪已完成的行；
  RESULTS／COUNT 放在口上專用的暫存（`state.temp.narr`），與 Python 移植部分不共用（原作是全域變數）。RESULT 於 S21 改為共用
  （`GameState.result`，`docs/wiki/python/result.md`）；但 Python 移植部分只寫 RESULT:1 以後的來源與少數 RESULT:0，口上讀「呼叫前的 RESULT:0」時
  仍可能不同。（Python：`eragvt.narration.runtime`）
  S14：`DRAWLINEFORM 文字列` 畫成與 DRAWLINE 相同的區切線（原作以該字串重複到畫面寬：`GameView/EmueraConsole.Print.cs@getStBar`:543–560；
  動画サイト :1335 的 `―`）；動画サイトの `PRINT_TAGSET_TEXT` 的 `@F:` フォント指定不反映（本作未使用），既定色的 `SETCOLOR 0x{GETCOLOR}`
  以「回到呼叫前的顏色」表示（顯示相同）。（Python：`eragvt.narration.runtime`、`eragvt.narration.windowlib`）
- [ ] **SHOW_SHOP 簡化**：狀態條（`COLOR_BAR` 的色階與長度）以 20 格單色近似；`SHOW_SHOP_STATUS_SIGN`（生理周期・疲勞等標記）、隊伍列表的欄寬對齊與第 2 行詳細、控えメンバー一覽未移植；`SHOP_NG_ACTION_INFO` 的紅字在函式結尾重設顏色（原作不重設）。（Python：`eragvt.game.shop`）
- [ ] **未實作的選單**：`[50]`、`[110]`〜`[180]`、`[700]`、`[800]` 只顯示「（未實作）」。（`[100]` 已於 S04 接上行動執行。）
  S12：`[110]`〜`[160]` 先照 USERSHOP:246–285 的條件判斷（ゲームオーバーモード中 [111]〜[150] 不做任何事、[110] 先 LIMIT TARGET、
  [160] 無可選角色時印原作訊息），條件成立時才顯示「（未實作）」。
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
  這些函式內沒有 RAND；代入只有 `STATUS_PRINT_CHARGE`（CHARA_STATUS.ERB:1477–1489，每回合無條件）的 TCVARn:206（[反撃]バースト的蓄積限度），S16 起照原文計算（`train.status_charge_limit`），其餘不影響狀態。`[800]` ステータス畫面（`SHOW_STATUS_CHARA_SELECT`，5 頁）只顯示
  「未移植」一行。`SHOW_USERCOM` 只移植「不分類」版（`BATTLE_COM.ERB`:379–568，基本設定 FLAG:801 bit2 = 0），
  《危険度》的顏色照 `FORECAST_OUTPUT_SETCOLOR`。（Python：`eragvt.game.battle.train.show_status`／`show_usercom`／`usercom`）
- [ ] **性攻擊的地の文**（S06 新增、S07 更新）：S07 起 `地の文/MESSAGE_SEX*.ERB`、敗北 `MESSAGE_BATTLE_END_LOSS`、射精・處女喪失・
  ヒロイン側性攻撃的地の文由 catalog 輸出本文，其中的狀態變化行經 `narration/hooks.py`（140 行，對照 sexmsg）依 ERB 順序執行、
  RAND 也照 ERB 順序抽（亂數序列與 S06 不同）。S14 起 `MESSAGE_SEX_SPCOM7`（含 INPUTS 與動画サイト）也由 catalog 執行。catalog 不可執行或 Null 時才印
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
  S14：動画サイト（`MESSAGE_WindowLibrary_VideoHostSite.ERB`:1343 INPUTS）也同樣；按鈕值 "0"〜"4"／"99" 都是數字，其他輸入走
  :1346–1347「上次看的下一段」，只差在不能輸入空字串（原作空字串也走這條），結果相同。（Python：`eragvt.narration.service.run_function_gen`）
- [ ] **HTML_PRINT 的子集**（S11 新增，只影響顯示）：只支援原作用到的 `<font color>`／`<nonbutton title>`（tooltip 以 Web 的
  title 屬性顯示）；其他タグ停止。（Python：`eragvt.text.TextOutput.html_print`）
- [ ] **子供加入時的キャラ設定畫面**（S13 新增，只影響顯示）：`ADD_CHILD`:515 的一人称設定（`FIRSTSETTING_CHARA_SELFCALL`）與
  :1078 的プロフィール設定（`CHARA_SIZE_UI.ERB@SIZE_SETTING`）不顯示，照 AGENTS.md 以「什麼都不改、直接按 [99] 決定」的狀態變化執行
  （CSTR:4 = 一人称、パーソナリティ前詰め、身體資料照 GENERATE_CHAR_SIZE 重算；顯示部分無代入・無 RAND）。フィート選擇畫面
  （[0]はい）有移植，種族／フィート說明（`SYUZOKU_INFO`／`FEAT_INFO`）走 catalog，不可執行時印「〈SYUZOKU_INFO n〉」。
  （Python：`eragvt.game.firstsetting.selfcall_default`／`size_setting_default`／`feat_select_ui`）
- [ ] **Web 停止狀態**：遇到未移植處理時顯示「（未實作のため停止しました：…）」並停住，是原作沒有的畫面（見上「S04 未翻的行動」）。
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
  （`GAPING.ERB@PRINTFORM_GAPING_NOW`:800–808；呼叫者是 FLAG:801 bit 5 的戰鬥 PALAM 表示〔既定 OFF〕與ステータス畫面 PAGE5〔未移植〕），
  所以既定遊玩時從 0（rank 0）開始、第一次被插入就大幅上升（例：0 → 55、膣径 +3.8 cm）；GET_*_GAPING_EXP 的靜態 LOCAL 在 ARG < 3 時沿用
  上次值（:1018–1022）；V_GAPING 等的早期 RETURN 不還原 TARGET；いちゃラブ的処女地の文（MESSAGE_SEX.ERB:1301）因 SEX_V:221 先把
  処女改成 −1 而不會出現。**使用者裁決（2026-09-30）**：照原作，不在開局設定初期值（狀態畫面 PAGE5 移植後自然會在顯示時設定）。
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
  [反撃]バーストの蓄積ダメージ TCVARn:205 只在 ＥＸ反撃（`HANGEKI_STYLE.ERB`:67，未移植）增加，限度 TCVARn:206 只在狀態列顯示
  （`STATUS_PRINT_CHARGE`）時計算；ＳＰフルバースト在変身能力ありのキャラ不看ゲージ（`COMABLE.ERB`:808–815 原作註解自承）。
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
  3003／3004 的 MISSION_CHECKER（:78／:378）`&&`／`||` 同優先度左結合 → 未受凌辱而敗北（TFLAG:98 = 2、TFLAG:21 & 7 = 0）判為「成功」；
  3004 TURNEND 的白濁シャワー（:344–354）只 RESETCOLOR 不 FONTREGULAR → 其後文字保持太字；3002 繁殖袋路 :25 `PRINTFORM`（無換行）
  與下一行相連；救援 5（触手洞窟）以 FLAG:111 == 0 為條件（同回合 AKUOTI_EVENT 留下的 FLAG:111 會讓 `5 触手洞窟.ERB`:146–302 的 CASE 0／1／2（知性 > 600）不加任何シチュエーション，ターン上限照設）；
  `CLOTHDATA※イベント専用装備.ERB` 的 `@CLOTH_STATUS_991` 定義兩次（:73／:88），引擎用先定義的 :73（HP0）；3004 以外 FLAG:45 的 992 インナー
  走 CATCH 既定值（HP80・SEITAISEI95）；FLAG:999 ≠ 0（デバッグ以外の値も）時 FLAG:45 不抽選 → EVENT_BATTLE_SITUATION_0 不存在的錯誤路。

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
  - D4：未移植的 `PASTIME_悪堕ち遭遇.ERB`:19、`ACTION_GATHER_INFORMATION.ERB`:142 的同類 SQRT，之後移植時比照（程式尚無）。
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
