# 共用 RESULT 陣列（`GameState.result`，S21）

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
| `WindowDrawer.ERB`:330 `VARSET RESULT, 0`、:397–400、`TagSetText.ERB`:100／:218 | 全 0 | `narration.windowlib`（WINDOW_* 終了時に全消去） |
| 口上・地の文（`SELF_CALL.ERB`:356／:381–425、`KOJO_4_汎用豹変.ERB`:64 ほか） | 各種 | catalog（`narration.runtime` が `GameState.result` を読み書き） |

RESULT:0 だけの書き込み（単値 RETURN・関数終端・INPUT 等）は原則として模型化しない。例外（読む側があるもの）：`PALAM_HOSEI`（:435）・
`TENTACLE_SYASEI_UP` 終端・`PRINT_DISTANCE` 終端（悪堕ちキャラ戦の TENTACLE_SAKUSEI と COMF103 の不発 TRYCALLFORM が読む）。

未移植のため書き込みも無い来源：`FIRSTSETTING_RANDOMNAMING.ERB`:298／303、`FIRSTSETTING_CHARA.ERB`:1021、
`SHOW_STATUS_CHARA_SELECT_PAGE2.ERB`:289–304、`CALC_SEISAN.ERB`:137、`SEISAN_0_PART_TIME.ERB`:168、`ACTION_TRAINING.ERB@TRAINING_DAYTIME`:321
（呼出なし）、ラスボス／雑魚／クズ市民の触手データ（`TENTACLE_LASTBOSS_*`、`TENTACLE_MOB_*`〔:1196 等の VARSET・`RESULT:n +=` 含む〕、
`CITIZEN_1.ERB`:123）、`SHOP_FLASHNEWS.ERB`、`COLOR_TABLE.ERB`、`TRANS_SEX`／`SUCCESSION`／`FIRSTSETTING_CHARA_TRANSFORMATION` の GENERATE_CHAR_SIZE。
移植時は同じく `GameState.result` に書くこと。

## 読む側（殘值を使う所）

- `EVENT_PALAM_UP.ERB@EVENT_PALAM_HOSEI`:134–140（悪堕ちキャラによる幽閉 CFLAG:20 == 2）：`UP:k = RESULT:k / 100`（k = 0〜11）。
- `TENTACLE_SYASEI.ERB@TENTACLE_SAKUSEI`:585–586（悪堕ちキャラ戦、BOSS_0 不在）：RESULT:0。
- `COMF103.ERB`:197–200（悪堕ちキャラ戦の素股焦らし失敗）：RESULT:0（PRINT_DISTANCE 終端の 0）。
- `COMF100.ERB`:52–62 のフェラ誘発（悪堕ちキャラ戦）：直前の TENTACLE_SYASEI_CHECK の RESULT:0（局所変数で実装、値は同じ）。

## 限界（deviations「口上 catalog の表示簡化」・unresolved）

- RESULTS／COUNT は共用していない（catalog 専用の暫存）。
- catalog で実行できない口上・地の文（Null narration 含む）の中の書き込みは起きない（`SELF_CALL_ANALYSIS` は S21 の STRFINDU 追加で実行可能に）。
