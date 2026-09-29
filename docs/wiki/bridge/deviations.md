# 與原作的偏離（需使用者決定）

凡是 Python 版與原作行為不同的地方（簡化、跳過、近似規則、額外保存的資料…）都列在這裡，
程式對應位置標 `# DEVIATION:`。使用者決定後，在該項註明「已同意（日期）」或改回與原作一致並刪除該項。

**2026-09-29 使用者裁決（整體）**：以下所有項目暫時維持現狀，開發繼續推進；之後的進度可能給出合理解釋。
只有在某項偏離或原作 bug **已嚴重到無法推進開發**時，才回頭評估修正方式。新增項目仍照規則登記並在 session 報告列出。

格式：`- [ ] 內容（原作：檔案@函式／reference 位置；Python：模組@函式）— 為什麼要偏離／替代方案`
ERB 路徑相對 `source/earGVP/ERB/`。

## 狀態會不同

- [ ] **亂數**：用 Python `random.Random`（可 seed），不是 Emuera 的 MT 實作；RAND 的呼叫次數也不追求一致（例：`RESEARCH_QUOTA` 的 `RAND:5` 是否短路求值）。同 seed 不會得到原作同樣的結果。（原作：`reference/.../GameData/Variable/VariableEvaluator.cs`:36–52；Python：`eragvt.state.rng.GameRng`）— 要完全一致需移植 MTRandom 並逐一核對求值順序，成本高。
- [ ] **開局：身體資料生成未移植**：`CHARA_MAKE_BASE_PROFILE`（年齡、身高體重三圍 `CHARA_SIZE_DEFAULT`、`GENERATE_BODYLINE`、髮色瞳色等的補完，含亂數）沒有執行，這些 BASE（40–48）／CSTR 維持 CSV 值或空。（原作：`SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_BASE_PROFILE`:493–984；Python：`eragvt.game.opening.chara_make_initialize`）— 約 500 行＋`CHARA_SIZE.ERB` 670 行，主選單與戰鬥用不到；建議排到角色製作完整版時一併翻。
- [ ] **FLASHNEWS 未移植**：新聞產生（含亂數、寫入 `SAVESTR:20`、`FLAG:60`）沒有執行，畫面顯示「（未實作）」。（原作：`インターミッション画面/SHOP_FLASHNEWS.ERB@FLASHNEWS`:3–752；Python：`eragvt.game.shop.flashnews`）
- [ ] **全域資料（GLOBAL）不讀不寫**：永遠走「真正的初次啟動」路徑（MOB_FLAG 初始化為 100、不套用 GLOBAL 的 config／性嗜好フィルタ），也不存成就等全域資料。（原作：`オープニング処理.ERB@EVENTFIRST`:29–45、`バージョン間互換処理.ERB@UPDATE`:95–130；Python：`eragvt.game.opening.event_first`）— 等設定畫面／成就功能時一起做。
  S05 起戰鬥中的 `UNLOCK_ACHIEVEMENT`（タクティカルオーダー、絶体絶命ヒロイン等）與 `GET_STATE_ABLUP` 同樣不執行（`eragvt.game.battle.core.unlock_achievement`）。
  S04 起同理不執行：`SHOP_TURNEND.ERB@UPDATE_STATUS_RECORD`:263–349（歷代最高紀錄 GLOBAL:103–131／GLOBALS、SAVEGLOBAL）與 `SHOP_TROPHY.ERB@GET_STATE_TROPHY`:398–441→`UNLOCK_ACHIEVEMENT`（成就達成訊息不會顯示）。（Python：`eragvt.game.turnend.recalc_partymember`、`eragvt.game.action.get_state_trophy`）
- [ ] **開局固定路徑**：模式固定 NORMAL、初期セット固定「特装戦隊」（301–303）、config 固定「基本セット」，不顯示模式選擇／角色製作／序章畫面。（Python：`eragvt.game.opening`）— S03 規格指定的最小路徑。

- [ ] **S04 未翻的行動會停止遊戲**：（出撃已於 S05 接上，戰鬥內的停止見下一項）特別活動、拠点防衛、戦闘支援（本體）、情報収集、自由行動在 `action_main` 丟 `NotImplementedError`，Web session 捕捉後進入「停止」狀態（只能按「タイトルに戻る」）。同樣停止的還有：ENDING（全ボス撃破／**11 日目夜的日數超過**）、救出直後、妊娠・育兒・幽閉・悪堕ち等 S04 無法產生的狀態、鍛錬排程（CFLAG:110）、戦闘基礎 Lv5 的變身能力獲得。（原作：`ゲーム内_行動実行処理/ACTION.ERB`:74–175 等；Python：`eragvt.game.action`、`eragvt.game.turnend`、`eragvt.game.session._advance_turn`）— 各自屬 S05 以後；影響範圍見 `docs/wiki/era/actions.md`。
- [ ] **襲撃／救援、子触手襲来 會被跳過**：`RAID_HANTEI`（DAY ≥ 3 起依防衛力的亂數）與 `SMALL_TENTACLE_HANTEI`（夜、FLAG:44 > 0）判定成立時，原作會 `JUMP RAID_RESCUE／RAID_ATTACK`（戰鬥）或 `CALL SMALL_TENTACLE_ATTACK`；這裡只印「（未實作：…が発生しましたが、スキップします）」並當作沒發生。（原作：`ゲーム内_イベント発生/強制発生イベント/FORCE_襲撃or救援イベント発生.ERB`:94–105、`FORCE_深夜の子触手襲来.ERB`:48–53；Python：`eragvt.game.turnend.raid_hantei`／`small_tentacle_hantei`／`_skip_event`）— 通常遊玩一定會遇到，若改成停止則無法連續遊玩；戰鬥在 S05／S06 接上。
- [ ] **未移植的戰鬥分岐會停止遊戲**（S05 新增、S06 更新）：戰鬥中下列情況丟 `NotImplementedError` → Web「停止」。
  S06 接上了拘束後的性攻擊、拘束中指令、絶頂／射精、敗北（→ 幽閉）與指令 6・7・16・17・69・71・72；
  仍停止的一覽見 `docs/STATUS.md`「S06 後仍會停止的分岐」（ＳＰ變身／ＳＰバースト、バースト攻擊的效果、反擊、受精成立、
  強制自慰、動画流出、幽閉後的 TURNEND、悪堕ち／雜魚／ラスボス、拡張度 CFLAG:34 != 0 等）。
  （Python：`eragvt.game.battle.*` 各處 `raise NotImplementedError`、`battle.commands.run_com` 的 `# DEVIATION:`）
  — 依規格「未移植分岐必須停止」。
- [ ] **振り解く判定的 `LOCAL:O`**（S06 新增，**需裁決**）：`ゲーム内_戦闘処理/COMMON_BATTLE_HANTEI.ERB`:241／:245
  `SIF LOCAL:5 <= 45 && LOCAL:O > 49` 的 `O` 是英文字母，全作沒有這個識別子（grep 僅此 2 處）。1.824 在執行到該行時
  報錯停止（`GameProc/Process.ScriptProc.cs`:38–42、`GameData/Expression/ExpressionParser.cs`:264–269、
  `GameData/IdentifierDictionary.cs`:645），而振り解く的％顯示（`PRINT_COMNAME.ERB`:6–13）每次都會經過這裡，
  也就是原作（1.824）一被拘束就無法繼續。本作當作 `LOCAL:0`（體力氣力殘量％）的筆誤來判定。
  （Python：`eragvt.game.battle.hantei._hurihodoku`）— 替代方案：照 1.824 停止（等同無法玩拘束），或確認 +v10 的行為。
- [ ] **開局身體資料未生成對戰鬥的影響（既有「身體資料生成未移植」的後果，需裁決）**：BASE:体重(44)／胸の重量(48) 為 0，
  原作的「胸部重量ペナルティ」式 `LOCAL:2 -= LOCAL:2 * (1+胸の重量) / (1+体重)` 會把女性角色的敏捷整個扣成 0
  （`ゲーム内_戦闘処理/COMMON_BATTLE_HANTEI.ERB`:606–614 被弾判定、:1097–1105 撤退判定），`DAMAGE` 的巨乳ボーナス
  `LOCAL:5 += LOCAL:5 * (1+胸の重量) / (1+体重)`（:1207–1214）讓傷害變 2 倍。照原作公式移植，結果是「幾乎必中＋攻擊 2 倍」。
  （Python：`eragvt.game.battle.hantei`）— 若要正常數值，需先移植 `CHARA_MAKE_BASE_PROFILE`／`CHARA_SIZE.ERB`。
- [ ] **口上的狀態副作用**：REST／鍛錬／MESSAGE_TURNEND 的 `KOJO_ROOT` 只做「找不到口上」路徑（FLAG:62 = 0、FLAG:900 = 0、RETURN -1）；原作若該角色有專用口上（如 KOJO_301_REST），口上函式本身可能改變變數，這部分未執行。（Python：`eragvt.game.action.kojo_root`）— 隨 S07 口上抽取處理。

## 只影響顯示

- [ ] **口上**：`MESSAGE_FIRST`、SHOP 一口メッセージ等口上文字未輸出（`NullNarrationService`），SHOP 以「無口上」的 4 行空行處理。（原作：`口上/口上システム関係/KOJO_ROOT.ERB`；Python：`eragvt.text.narration`）— S07 抽取管線處理。
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
- [ ] **性攻擊的地の文**（S06 新增）：`地の文/MESSAGE_SEX*.ERB`、`MESSAGE_SEX_COMSP.ERB`、`MESSAGE_SEX_COMEX.ERB`、
  射精・絶頂系（`MESSAGE_SEX.ERB`:764–1060 等）、敗北時 `MESSAGE_BATTLE_END_LOSS` 的本文不移植，改印一行
  「〈地の文：函式名〉」（`eragvt.game.battle.core.chinobun`）。本文中的**狀態變化**（TFLAG:21 撮影 bit、FLAG:900、
  SET_TENTACLE_SIZE_BY_MESSAGE、處女喪失、受精判定、TCVARn:25、CFLAG:206、氣絶 等）與 KOJO_ROOT 呼叫照原作位置移植
  （`battle.sexmsg`）。只為選文句而抽的 RAND 不抽（RAND 次數不同，已含在「亂數」項）。— 地の文 catalog 由 S07 抽取管線處理。
- [ ] **Web 停止狀態**：遇到未移植處理時顯示「（未實作のため停止しました：…）」並停住，是原作沒有的畫面（見上「S04 未翻的行動」）。

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
