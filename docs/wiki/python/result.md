# 共用 RESULT／RESULTS 陣列（`GameState.result`：S21、`GameState.results`：S22）

原作的 RESULT 是跨函式的全域整數陣列，有幾處讀「前一次留下的值」（例：悪堕ちキャラ幽閉的 `EVENT_PALAM_HOSEI`）。
S21 起 Python 移植部分與口上／地の文 catalog 共用 `GameState.result`（`IntArray`）。引擎路徑相對 `reference/emuera-1824/Emuera/`，
ERB 路徑相對 `source/earGVP/ERB/`。

## 引擎規格

| 事項 | 依據 |
|---|---|
| 整數 1 維、大小 1000（VariableSize.csv 未指定） | `GameData/Variable/VariableCode.cs`:44（0x0A）、`GameData/ConstantData.cs`:147–148 |
| 存檔對象（0x0A < `__COUNT_SAVE_INTEGER_ARRAY__` 0x3C）→ 讀檔時以存檔值覆寫 | `GameData/Variable/VariableToken.cs`:74–77、`VariableData.cs@SaveToStream`:663–674 |
| 新遊戲 `ResetData` 清零；BEGIN TRAIN 不清 | `VariableData.cs@SetDefaultValue`:532–、`VariableEvaluator.cs@UpdateInBeginTrain`:1422–1460 |
| 多值 `RETURN a, b, …`：只寫給定個數，其餘保留 | `GameProc/Function/Instraction.Child.cs@RETURN_Instruction`:2006–2023 → `VariableEvaluator.cs@SetResultX`:1732–1740 |
| 函式終端（無 RETURN）：只有 RESULT:0 = 0（#FUNCTION 除外） | `GameProc/Process.ScriptProc.cs`:61–67 |
| 式中関数當命令用：結果進 RESULT:0（字串進 RESULTS:0） | `Instraction.Child.cs`:390–409 |
| 寫多格的內建命令：VARSIZE（`VariableEvaluator.cs@VarSize`:1664–1682）、ENCODETOUNI（`Process.ScriptProc.cs`:705–718）、INPUTMOUSEKEY（`Process.cs@InputResult5`:240–248） | 本作 ERB 0 件（grep） |
| `VARSET RESULT[, 0]`：全 1000 格 | `Instraction.Child.cs`（VARSET） |

存檔：`SAVE_VERSION = 2`（版本 1 → 2 的 migration 補空的 `result`）。

## RESULT:1 以後的寫入來源（全域 grep，S21）

查法（`LC_ALL=C.UTF-8 grep -P`）：多值 RETURN `^\s*RETURN\s+[^;\n]*,` 94 件（口上以外 84、口上 10；其中 `コモン関数.ERB`:592–634 的 7 件是
單值〔逗號在函式引數內〕）；直接代入 `RESULT\s*:\s*[^ =\n]+\s*(op)?=` 147 件（RESULT:0 以外 137 件，含 `TALENT:RESULT:…` 等添字用法、
`;` 註解）；`VARSET RESULT` 10 件；RETURNFORM／VARSIZE／ENCODETOUNI／INPUTMOUSEKEY 0 件。

| 來源 | 寫入 | Python |
|---|---|---|
| `COMMON_TENTACLE_DATA.ERB@TENTACLE_ACCESS`:253 ＋ボスの `_PALAM_HOSEI`（例 `TENTACLE_BOSS_1_Ｃ触手.ERB`:125） | 0〜11 | `battle.core.tentacle_palam_hosei` |
| 同 `@TENTACLE_ACCESS_PRISON`:327（ボス）；CFLAG:20 == 2 は分岐なし → RESULT:0 = 0 只 | 0〜11／0 | `prison.event.tentacle_access_prison` |
| S27：`@TENTACLE_ACCESS`:306 ＋ `TENTACLE_LASTBOSS_1_PALAM_HOSEI`（Ｋ触手.ERB:123）；`@TENTACLE_ACCESS_PRISON`:339（CFLAG:20 == 1 も BOSS 側の値） | 0〜11 | `battle.core.tentacle_palam_hosei`／`prison.event.tentacle_access_prison` |
| S27：`GAPING.ERB@SET_TENTACLE_SIZE`:1135 ＋ `TENTACLE_LASTBOSS_1_TENTACLE_SIZE`（Ｋ触手.ERB:257） | 0〜7 | `battle.gaping.set_tentacle_size` |
| `GAPING.ERB@SET_TENTACLE_SIZE`：ボス `_TENTACLE_SIZE` 8 值（:1128）、悪堕ち寄生 :1098–1101、終端 RESULT:0 = 0 | 0〜7 | `battle.gaping.set_tentacle_size` |
| `GAPING.ERB@PRISON_GAPING`:1336 | 0〜1 | `prison.commands.prison_gaping` |
| `COMMON_PRISON.ERB@COMMON_PRISON_EXP_SH`:71 | 0〜3 | `prison.commands.common_prison_exp_sh` |
| `SEX_COMEX.ERB`:123（RANDOM）、:338 | 0〜1、0〜11 | `battle.sexcom.sex_comex_random`／`sex_comex` |
| `COMMON_BATTLE_HANTEI.ERB@ACT_HANTEI_CHARA_TO_TENTACLE`:410／:412 | 0〜1 | `battle.hantei.act_hantei_chara_to_tentacle` |
| `TENTACLE_SYASEI.ERB`：CHECK :119〜215、POINT :568、SAKUSEI :575／:607 | 0〜3 | `battle.syasei` |
| `PALAM_UP.ERB`:147 `RESULT:1 *= 4` | 1 | `battle.palam`（PALAM_UP） |
| `ABL_UP_CHECK.ERB@ABL_UP_EX`:1235 | 0〜3 | `battle.ablup._abl_up_ex` |
| `SHOP_TURNEND.ERB@INMON_RECOVERY`:859–860 | 1 | `turnend.inmon_recovery` |
| `FORCE_悪堕ちキャラの淫謀.ERB`:706–716（動画拡散） | 1 | `akuoti._video` |
| `CHARA_SIZE.ERB@GENERATE_CHAR_SIZE`:283（TOP_UNDER :380 は上書きされる） | 0〜7 | `body.generate_char_size(…, result)`（呼出元が `st.result` を渡す） |
| `SHOW_STATUS_CHARA_SELECT_PAGE2.ERB@GET_COLOR_BY_RANK`:289–304（S25） | 0〜2 | `status_screen.get_color_by_rank` |
| `CHARA_SIZE.ERB@TOP_UNDER`:380（PAGE5:198 から直接呼出、続く CUP_SIZE が RESULT:0 を上書き；S25） | 0〜1 | `status_screen._apperance` |
| `SHOP_FLASHNEWS.ERB`：:540／:607 `RESULT:1 = RANDCHOOSE_F()`、`@FLASHNEWS_CHOOSEHEROINE`:920／:922（2 値 RETURN）、`@FLASHNEWS_CHOOSEIDOL`:939–987（RESULT:1）・:1000、FLASHNEWS の RETURN／終端（RESULT:0 = 0；S26） | 0〜1 | `flashnews` |
| `WindowDrawer.ERB`:330 `VARSET RESULT, 0`、:397–400、`TagSetText.ERB`:100／:218 | 全 0 | `narration.windowlib`（WINDOW_* 終了時に全消去） |
| S28b：`特別活動/CALC_SEISAN.ERB`:137、`SEISAN_0_PART_TIME.ERB@SEISAN_PART_TIME_SHINBUN`:168（2 値 RETURN）、各 SEISAN の単値 RETURN・関数終端・`RESULT:0 = …`（SEISAN_5:30／:51／:73）、呼び出す AFTER_PILL（終端 0）・NINSIN_HANTEI | 0〜1 | `seisan`（後続の読み：SEISAN_2:70・SEISAN_5:56–91） |
| S28c1：`自由行動中イベント/` の Python 移植（RETURN／関数終端・INPUT の RESULT:0、CLOTH_NO_INNER、NINSIN_HANTEI）、catalog 実行の `MESSAGE_PASTIME_FitnessClub` 等（`RETURN EROEVENT`）。`DOT_AFTER` は `RETURN RESULT`（不変：`seisan._dot_after` も訂正） | 0 | `pastime`／`pastime_school`（運動する:59 が Fitness の RESULT:0 を読む） |
| 口上・地の文（`SELF_CALL.ERB`:356／:381–425、`KOJO_4_汎用豹変.ERB`:64 ほか） | 各種 | catalog（`narration.runtime` が `GameState.result` を読み書き） |

RESULT:0 だけの書き込み（単値 RETURN・関数終端・INPUT 等）は原則として模型化しない。例外（読む側があるもの）：`PALAM_HOSEI`（:435）・
`TENTACLE_SYASEI_UP` 終端・`PRINT_DISTANCE` 終端（悪堕ちキャラ戦の TENTACLE_SAKUSEI と COMF103 の不発 TRYCALLFORM が読む）。

未移植のため書き込みも無い来源：`FIRSTSETTING_RANDOMNAMING.ERB`:298／303、`FIRSTSETTING_CHARA.ERB`:1021、
`ACTION_TRAINING.ERB@TRAINING_DAYTIME`:321
（呼出なし）、ラスボス／雑魚／クズ市民の触手データ（`TENTACLE_LASTBOSS_*`、`TENTACLE_MOB_*`〔:1196 等の VARSET・`RESULT:n +=` 含む〕、
`CITIZEN_1.ERB`:123）、`COLOR_TABLE.ERB`、`TRANS_SEX`／`SUCCESSION`／`FIRSTSETTING_CHARA_TRANSFORMATION` の GENERATE_CHAR_SIZE。
移植時は同じく `GameState.result` に書くこと。

## 読む側（殘值を使う所）

- `EVENT_PALAM_UP.ERB@EVENT_PALAM_HOSEI`:134–140（悪堕ちキャラによる幽閉 CFLAG:20 == 2）：`UP:k = RESULT:k / 100`（k = 0〜11）。
- `TENTACLE_SYASEI.ERB@TENTACLE_SAKUSEI`:585–586（悪堕ちキャラ戦、BOSS_0 不在）：RESULT:0。
- `COMF103.ERB`:197–200（悪堕ちキャラ戦の素股焦らし失敗）：RESULT:0（PRINT_DISTANCE 終端の 0）。
- `COMF100.ERB`:52–62 のフェラ誘発（悪堕ちキャラ戦）：直前の TENTACLE_SYASEI_CHECK の RESULT:0（局所変数で実装、値は同じ）。

## RESULT:0「呼び出し前の値」の再確認（S22）

RESULT:0 は CALL の戻りで必ず書かれる（RETURN → SetResultX／RESULT = 0、関数終端 → 0：`Process.ScriptProc.cs`:61–67）ので、
呼び出し前の値が読まれるのは「TRYCALL(FORM) の不発（`Instraction.Child.cs`:2310–2317）」と「関数先頭で呼出元の RESULT を読む」場合だけ。
口上・地の文以外の `TRYCALL`／`TRYCALLFORM`（TRYC 系は CATCH があるので除外）直後の RESULT 読みを全件確認：
既存の対処（COMF100／COMF102／COMF103、TENTACLE_SAKUSEI）に加え、`BATTLE_COM_AFTER.ERB`:1151–1160（素股焦らしの次ターン指定）の
悪堕ちキャラ戦（FLAG:11 = 0 → `TENTACLE_BOSS_0_REACTION_REF` 不在）を S22 で同期：直前の `CALL HATUJOU_TO_HAIRAN`（:1147）の
早退 `RETURN 0`（`ゲーム内_戦闘処理/SUBEVENT_BATTLEE.ERB@HATUJOU_TO_HAIRAN:515–527`）寫入 `st.result[0]`，
S32 補上成功路徑的 `RETURN 1`（同函式 :585）；:1159 沿用此共用值，RESULT 其他元素保持原值。
他（`TENTACLE_ACCESS` の数値キー〔悪堕ちキャラ戦〕は既存の停止、COM_ABLE・TRAINING_HOSEI_CHILD・KYUSHUTU_* は関数が存在、
GAPING:1131／:1138・CLOTH_WEAR:931／:1526・CHARA_MAKE:319 は未移植）。

# RESULTS（`GameState.results`，S22）

## 引擎規格

| 事項 | 依據 |
|---|---|
| 字串 1 維、大小 100（本作 VariableSize.csv 未指定） | `GameData/Variable/VariableCode.cs`:110（0x02）、`GameData/ConstantData.cs`:154–155 |
| **不存檔**：0x02 ≥ `__COUNT_SAVE_STRING_ARRAY__`（0x01）且無 `__SAVE_EXTENDED__` | `VariableCode.cs`:104–110、`VariableData.cs@SaveToStream`:663–674、`VariableIdentifier.cs`:248–256 |
| 新遊戲 ResetData・讀檔時 SetDefaultValue → 全 ""（null） | `VariableEvaluator.cs@ResetData`:1132–1139、`@LoadFromStream`:2173／`@LoadFromStreamBinary`:2339 → `VariableData.cs`:558–574 |
| BEGIN TRAIN 不清（只清 TSTR） | `VariableEvaluator.cs@UpdateInBeginTrain`:1422–1460 |
| `RETURN` 只收整數（`INT_ANY`）→ **沒有字串的多值 RETURN**；RETURNFORM 也是整數 | `Instraction.Child.cs@RETURN_Instruction`:1997–2023、`@RETURNFORM_Instruction`:1954–1993 |
| `#FUNCTION(S)` 不可 CALL（CodeEE），RETURNF 的值只回到式中，不寫 RESULTS | `Process.CalledFunction.cs`:117–120、`Process.State.cs@ReturnF`:502–525 |
| 式中関数當命令用：字串結果進 RESULTS:0 | `Instraction.Child.cs@METHOD_Instruction`:390–409 |
| INPUTS／TINPUTS／ONEINPUTS 系：RESULTS:0 | `Process.cs@InputString`:257–260 |
| GETTIME：RESULTS:0（日時字串） | `Process.ScriptProc.cs`:368–379 |
| STRDATA 無引數 → RESULTS:0（本作 STRDATA 全部有代入先：grep） | `ArgumentBuilder.cs@VAR_STR_ArgumentBuilder`:1270–1290、`Process.ScriptProc.cs`:730–755 |
| HTML_TAGSPLIT 無代入先 → RESULTS、CHKDATA／CHKCHARADATA → RESULTS:0、FIND_CHARADATA → RESULTS:0〜 | `ArgumentBuilder.cs`:1520–1545、`Creator.Method.cs`:425–505（本作 0 件：grep） |
| SPLIT：代入先必須（第 3 引數），不會隱含寫 RESULTS；PRINTDATA 的引數是整數變數 | `ArgumentBuilder.cs`:1494–1514、:1248–1267 |
| `ARRAYCOPY "a", "RESULTS"`：短的一方的長度 | `Process.ScriptProc.cs`:661–700 → `VariableEvaluator.cs@CopyArray`:764–775 |

因此 Python 端：`GameState.results`（`StrArray`，compare=False，不寫入存檔 → **SAVE_VERSION 不升**，讀檔／新遊戲為空）。
`set_results_array(list)` = `VARSET RESULTS, ""`＋ARRAYCOPY。

## RESULTS:1 以後的寫入（全域 grep，S22）

查法：`RESULTS\s*:\s*(?!0(?![0-9]))[^\s=]+` 口上以外 66 行（讀寫混在）、口上 0 行；`VARSET RESULTS` 7 件（WEAPON_NAME:18、
CHARA_TATTOO:245／:482、TagSetText:101／178／219／270）＋口上 1 件（KOJO_0_21_ヤンデレ:38）；`ARRAYCOPY … "RESULTS"` 2 件（TagSetText:179／:271）；
RESULTS を代入先にする SPLIT・STRDATA・HTML_TAGSPLIT・FIND_CHARADATA 0 件。

| 來源 | 寫入 | Python |
|---|---|---|
| `汎用関数/コモン関数.ERB@STRMATCH`:1378–1393（呼出は `CORRPUTION.ERB`:786 のみ） | 成立 0〜2、不成立 0〜1 | `corruption.corruption_get_nanori_final`（＋catalog） |
| `TagSetText.ERB@CUT_TAGSET_TEXT`／`@SHAPE_TAGSET_TEXT`（VARSET＋ARRAYCOPY） | 全 100 | `narration.windowlib`（WINDOW_* 終了時に最後の SHAPE／CUT の結果） |
| `CHARA_TATTOO.ERB@PRINT_TATTOO`:245 VARSET、`@TATTOO_LIB`:482／:1406–1407 | 全／0〜1 | `tattoo.print_tattoo`（catalog 不可の佔位時も同じ結果を書く） |
| `口上/…/KOJO_0_21_ヤンデレ.ERB`:38 VARSET、その他口上・地の文 | 各種 | catalog（`narration.runtime` が `GameState.results` を読み書き、失敗時は復元） |
| `FIGHT_STYLE.ERB@SET_FSTYLE_INFO`:118–165（0〜2；S25：PAGE3:69 から） | 0〜2 | `status_screen.set_fstyle_info` |
| `イベントから派生する特殊戦闘/{2,3,4,5,3003,3004}*.ERB@EVENT_BATTLE_FLASHNEWS_n`（`RESULTS'=…`；FLASHNEWS:74–87 の TRYCALLFORM 先；S26） | 0 | `raid.event_battle_flashnews` |
| 未移植：WEAPON_CUSTOMIZE:28／44／60 からの SET_FSTYLE_INFO、`WEAPON_NAME.ERB`:18 VARSET・`GENERATE_WEAPON_STR_JP.ERB`:3505–3553（1）、`FIRSTSETTING_TITLE.ERB`:154／173／187（1〜3；CHARA_MAKE:215 のメニューからのみ）、`FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_NAME_RANDOM`:1018–1019（1〜2） | — | 移植時は `GameState.results` に書くこと |

RESULTS:0 の前回値を読む箇所（S26、S26b で照原作）：`SHOP_FLASHNEWS.ERB`:75／:79／:83／:87 `LOCALS'=RESULTS`。下節「事件戰ニュースの前回値」。

讀 RESULTS:1 以後：`CORRPUTION.ERB`:787（RESULTS:2：**前回の値を読みうる唯一の箇所**）、他（FIRSTSETTING_CHARA:540–541、WEAPON_CUSTOMIZE、
WEAPON_NAME:31、SHOW_STATUS PAGE3:71–72、CHARA_TATTOO:454、WindowDrawer:95–106）はいずれも直前の同一処理が書いた値。

## RESULTS:0

RESULTS:0 だけの書き込み（`RESULTS = …`、命令としての式中関数、INPUTS 系、GETTIME）は原則として模型化しない（Python の戻り値で受け渡し）。
理由：RESULTS を含む行（口上以外 469、口上 30：`grep -c`）の読み側を全件確認し、すべて同じ流れの直前の書き込み（TENTACLE_ACCESS は :201 で必ず
エラー文字列を書いてから TRYCALLFORM、TATTOO_ACCESS "POSITION_STR"・SEIKAKU_CHECK "STRING"（CHARA_SEIKAKU.ERB:17–31 どの経路も書く）・TOFULL・SUBSTRING(U)・INPUTS 等）を読んでいて、
呼び出し前の値を読む箇所は無い（**S26 訂正**：`SHOP_FLASHNEWS.ERB`:75–87 の `LOCALS'=RESULTS` は TRYCALLFORM 先が書かない場合に前回値を読む。
下節参照）。例外として同期しているもの：STRMATCH・NANORI_FINAL の REPLACE（:794–807）、TATTOO_ACCESS "POSITION_STR"、
WINDOW_*、PRINT_TATTOO（上表）、**@SAVEINFO**（S26b：`shop.save_info`）。

### 事件戰ニュースの前回値（S26b）

- **前回値を読むのは 2 路だけ**：FLAG:60 は各 n の ABANDON／SUCCESS／FAILURE が設定し（`Sif !FLAG:60`）、3001／3002／6001／6002 は
  その代入もコメント（3001:54–74、3002:136–156、6001:36–56、6002:34–54）→ `EVENT_BATTLE_FLASHNEWS_3001` 等は呼ばれない。
  書かない ARG は 3004 の 0（3004:286–287：時間切れで 3004:208 の被害条件に当たる → 103004）と 5 の -1（5:481：敗北 → 120005）。
  2・3 の -1 は "" を書く → :85–87 で ARG 0 に戻る。
- **戰後 SHOP までの最後の書き込みは @SAVEINFO**：EVENTEND（BATTLE_TRAIN_AFTER.ERB:536 `BEGIN TURNEND`）→ EVENTTURNEND（SHOP_TURNEND.ERB:59–63
  `BEGIN SHOP`；ENDING の FLAG:64 ≠ 0 路は Python 未移植で停止）→ @EVENTSHOP → オートセーブ（emuera.config:8「オートセーブを行なう:YES」、
  EVENTTURNEND 実行中は SystemState が Normal：`Process.SystemProc.cs@beginTurnend`:602–612、`Process.State.cs@Begin`:271–273 →
  `@endCallEventShop`:630–640）→ `@beginAutoSave`:642–654 が @SAVEINFO を呼ぶ（@SYSTEM_AUTOSAVE は本作に無い：grep）→ `@endAutoSave`:670–680
  → @SHOW_SHOP。@SAVEINFO（`オープニング処理.ERB`:583–614）は :585 GETTIME（日時）→ :604 `SUBSTRING LOCALS:2, 1, 3` で RESULTS:0 =
  "408"（GameBase.csv バージョン 408 → "1408" の 1〜3 文字目）。その後 @SHOW_SHOP:1–40（LB のみ）と FLASHNEWS:1–74（TENTACLE_SURVIVE "NUM"
  は TENTACLE_ACCESS を呼ばない）に書き込みは無い → **原作のニュース欄は「FLASH NEWS：《408》」**。戰鬥中・EVENTEND・TURNEND・EVENTSHOP の
  書き込み（下表）はすべて @SAVEINFO に上書きされるので、この 2 路の結果には影響しない。
- 讀檔直後（`@endEventLoad`:775–780：オートセーブなし）は RESULTS が ""（存檔しない）→ 5 は ARG 0 の文、3004 は通常抽選。EVENTLOAD の UPDATE
  が書くのは版数が古いときの :828–834 だけ（Python は 408 以外を未移植で停止）。
- 戰後路上の RESULTS:0 書き込み元（調査用；全域：代入 `^\s*RESULTS(:0)?\s*('=|+=|=)` 152 行〔口上 5〕、文字列を返す式中関数の命令用法
  （`Creator.cs` の methodList から抽出）REPLACE 25・SUBSTRING 14・SUBSTRINGU 18・TOFULL 11・CSVCSTR 1、INPUTS 系／GETTIME 30 行）：
  TENTACLE_ACCESS:201＋各 `_GETNAME`（全 ARGS で エラー文字列 → NAME／GETNAME は名前）、疲労表示 TOFULL（BATTLE_COM_AFTER:17–18、
  BATTLE_COM:804–805、BATTLE_TRAIN_AFTER:469–470）、COM_ATTACK_COMMON:160／292・COMF6・COMF47 の TOFULL、RAID_ATTACK:84／RAID_RESCUE:76 の
  TINPUTS（既定路 "WARNING"）、CLOTH_HOSEI:71–87 の SUBSTRING と 3004 の BATTLE_EVENT_CLOTH_STATUS:9（CLOTH_STATUS_990〜992 経由）、
  SEIKAKU_CHECK／SYUZOKU_CHECK "STRING"、口上・地の文（catalog が同期）。**模型化したのは @SAVEINFO だけ**（他は上書きされ読まれない）。
  今後「前回の RESULTS:0」を読む箇所が戰鬥中に見つかったら、上の書き込み元の同期が必要。

## 限界（deviations「口上 catalog の表示簡化」・unresolved）

- COUNT は共用していない（catalog 専用の暫存；Python は COUNT を模型化していない。unresolved `GAME_MODE_CHECK`）。
- catalog で実行できない口上・地の文（Null narration 含む）の中の書き込みは起きない（`SELF_CALL_ANALYSIS` は S21 の STRFINDU 追加で実行可能に）。
