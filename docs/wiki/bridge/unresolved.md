# 未決問題

格式：`- [ ] 問題（來源：檔案@函式）— 目前的推測／已查過哪些地方`
引擎原始碼路徑相對 `reference/emuera-1824/Emuera/`。

## Emuera 規格

- [x] DOTRAIN 內部順序 — `GameProc/Process.SystemProc.cs@doTrain`:430–485：`@EVENTCOM` → `@COMn` → `RESULT != 0` 時才 `@SOURCE_CHECK` → SOURCE 清空 → `@EVENTCOMEND`。BEGIN TRAIN 時 TFLAG/TSTR 清零（`GameData/Variable/VariableEvaluator.cs@UpdateInBeginTrain`:1422）。TRAIN 的輸入若是可用指令番號會直接 DOTRAIN，不經 `@USERCOM`（SystemProc@trainWaitInput:395–427）。
- [x] SHOP／TURNEND 的流程 — SystemProc@beginShop:614–628（EVENTSHOP）→ @endCallEventShop:630–640（自動存檔）→ @endAutoSave:670–680（SHOW_SHOP）；@USERSHOP 後回到 SHOW_SHOP（@endCallEventBuy:737–755）；@beginTurnend:602–612 只呼叫 EVENTTURNEND，沒有 BEGIN 就結束會報「予期しないスクリプト終端」（@endNormal:993–996），**不會**自動進 SHOP。已更新 `docs/wiki/era/flow.md` §0。
- [x] 角色 CSV 省略值 — 省略或無法解析一律 1，不限素質（`GameData/ConstantData.cs`:1276–1277）。已照改 `csv_loader`。
- [x] `フラグ,40,100.` — `tryToInt64` 讀到非數字即停止 → 100（`ConstantData.cs@tryToInt64`:1064–1104、`Sub/LexicalAnalyzer.cs@ReadInt64`:133）。
- [x] `基礎,40,xx`／`素質,200,変身能力` — 值無法解析 → 1（同上 :1276–1277），**不是**略過。已照改。
- [x] `_Replace.csv` `BAR文字1, ` — 值 trim 後為空 → 該行不生效，BAR 字元維持預設 `*`（`Config/ConfigData.cs@LoadReplaceFile`:539–551、:129）。
- [x] 新遊戲的初始角色列表 — SystemProc@endOpenning:197–209：`ResetData` → 依檔名番號加入角色 0 → 加入「最初からいるキャラ」（999）→ `@EVENTFIRST`。`GameState.new` 已照此建立 [0, 999]。
- [x] TARGET／ASSI 初始值 — `ResetData` → `SetDefaultValue` 設 TARGET=1、ASSI=-1（`GameData/Variable/VariableData.cs`:644–647）。
- [x] 存檔包含哪些變數 — 內建整數陣列 0x00–0x3B（含 **TFLAG**）、SAVESTR、TSTR、RANDDATA、角色全部內建變數、SAVEDATA 的 `#DIM`；`#DIM CHARADATA`（無 SAVEDATA）的 **TCVARn 不存**（`VariableCode.cs`:31–175、`VariableData.cs`:663–760、`CharacterData.cs`:289–350、`GameProc/UserDefinedVariable.cs`:150–152、315–320）。已改 `Character` 不存 TCVARn。RANDDATA 雖會存，但只在 `INITRAND`／`DUMPRAND` 使用（`GameProc/Function/Instraction.Child.cs`:1252、1266），本作 ERB 沒用到（grep 0 件）。
- [x] 自動按鈕 `[n]` 的範圍 — 已移植 `GameView/ButtonStringCreator.cs@syn`:35–167 與 `PrintStringBuffer.cs@fromCssToButton`:275（換行時整行判定；只有 1 個 `[n]` 時整段都是按鈕）。
- [ ] 無 BOM 的 UTF-8 角色 CSV（`_ADD/Chara160–163`、`Chara18xx_New Generation/CHARA1805–1807`）— 原版 1.824 以 Shift-JIS 解碼（`Sub/EraStreamReader.cs`:42 `new StreamReader(stream, Config.Encode)`、`Config/Config.cs`:17 SHIFT-JIS），這 7 檔會亂碼、連 `番号` 都讀不到；本作附的是 `Emuera1824+v10.exe`，**可能是 +v10 差異**（自動判別 UTF-8）。目前以 UTF-8 讀（`csv_loader.read_enabled_lines`，`# UNVERIFIED`）。需要時請在實機確認這些角色能否出現。
- [ ] 無 BOM 的 ERB `ゲーム内_イベント発生/特別活動イベント.ERB`（S07 發現；全 ERB/ERH 中唯一）— 1.824 以 Shift-JIS 讀
  （同上 `EraStreamReader.cs`:42），函式名會亂碼而找不到；catalog 以 UTF-8 讀（`narration.extract.read_logical_lines`）。
  口上／地の文沒有呼叫此檔的函式，目前不影響。可能是 +v10 差異。
- [ ] 未定義識別子 `LOCAL:O`（`ゲーム内_戦闘処理/COMMON_BATTLE_HANTEI.ERB`:241／:245，振り解く判定）— 1.824 在第一次執行該行時
  才解析引數（`GameProc/Process.ScriptProc.cs`:38–42），`O` 找不到 → `IdentifierNotFoundCodeEE`（`GameData/IdentifierDictionary.cs`:645）
  → 停止。原作附的 `Emuera1824+v10.exe` 是否同樣報錯未確認（reference 只有 1.824）。目前當 `LOCAL:0`（deviations.md）。

## 原作邏輯

- [x] `TFLAG:0`（戰鬥回合數）遞增處 — `ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK`:1313–1318（先制攻擊中扣 `TFLAG:24`，否則 `TFLAG:0 += 1`）。
- [ ] 一覧:594 說回合上限在 `TCVARn:13`，程式實際用 `ERB/DIM.ERH`:280 `ターン上限` — 以程式為準。
- [x] 雜魚／クズ市民戰在體力・氣力・性耐性全 0 時的結束路徑 — `BEGIN AFTERTRAIN` 全作只有 6 處（grep：`BATTLE_COM_AFTER.ERB`:435 勝利、
  :950 敗北、:1095 強拘束敗北、:1130 時間切れ；`BATTLE_COM.ERB`:596／:614 撤退），`TFLAG:98` 只在 :129（=1 勝利）、:852、:973（=2 敗北）設定。
  :955／:1303 的一般敗北判定排除 MOB／CITIZEN，所以**雜魚戰全 0 也不會敗北**，只能以勝利・時間切れ（15 回合）・撤退結束；
  クズ市民戰則由 :850 的專用判定（全 0 且被拘束 → 監禁 `CFLAG:0 = 4`）敗北。基本設定（FLAG:802 bit4 = 0）下雜魚遭遇只有文章
  （`ENCOUNT.ERB@MOB_TENTACLE_ENCOUNT`:449–521），不進 TRAIN。
- [x] TRAIN 的輸入 — 本作 `COMABLE.ERB` 的 38 個 `@COM_ABLE` 在 `TCVARn:8 < 10` 時全部 RETURN 0（35 個有 `SIF TCVARn:8 < 10`，
  201–203 最後回傳 `COM_ABLE0` 的結果），引擎的選項清單（SystemProc@endCallComAbleXX:312–354）永遠是空的，輸入一律經 `@USERCOM`
  （`BATTLE_COM.ERB`:572–664）再 `DOTRAIN`。
- [x] 角色 CSV `相性` 的轉換 — 只在 `HEROINE_PRESET` 選 `[30]` 時經 `SYSTEM/キャラメイキング関連/FIRSTSETTING_CONVERTCSV.ERB@CONVERT_RELATION`:3–23 把「CSV 番号索引」複製到「登錄 index 索引」（index = `CFLAG:240`）。直接開始遊戲時不轉換。引擎本身 RELATION 的索引是 CSV 番号（`VariableCode.cs`:146）。
- [x] `DIM.ERH`:20 `GFLAG`（「全領域参照用」）— 全 ERB 只有 `FORCE_夜這い.ERB` 使用（grep：DIM.ERH 以外僅此檔），YOBAI_EVENT:113 VARSET 後當夜這い組合表（S18，`eragvt.game.yobai`）。
- [x] 救出時間切れ `TFLAG:9`（S08）— 只有 `COMF15.ERB@KYUSHUTU_TIMEUP_HANTEI`:64 讀取（由 `BATTLE_COM_AFTER.ERB`:1115 TRYCALL），
  全 ERB（含口上）沒有代入處（`grep -P "TFLAG\s*:\s*9(?![0-9])"` 全 ERB／ERH 僅 1 筆）→ 地の文 `MESSAGE_KYUUSHUTU_TIMEUP` 不會出現。照原作（deviations「原作行為」）。
- [x] `@SHIFTFOWARD_CHARA`（`ヒロイン関連/SET_PARTYMEMBER.ERB`:48–64）— 全 ERB 沒有呼叫處（grep 只有定義行）→ 不移植。
- [ ] `TOINT` 對 cp932 無法編碼字元的處理（S10）— `Creator.Method.cs@ToIntMethod`:2363 以 `LangManager.GetStrlenLang`（`_Library/LangManager.cs`:17–20，
  `Encoding(932).GetByteCount`）判定全角；無法編碼字元的位元組數取決於 .NET 的替換 fallback，reference 內查不到。預設路徑不會遇到
  （年齢指定 CSTR:204–206 只來自角色 CSV／製作畫面），`eragvt.game.chara_make.toint` 遇到時停止。
- [ ] `SHOP.ERB@USERSHOP`:288–293 `CASE 169 && GAME_OPTION_CHECK_F(OPTION_加入引退有り)` 等（S12 發現）— CASE 引數整個是式，
  照字面會變成 `RESULT == (169 && …)`（0／1），[169]／[170]／[180] 可能永遠不會命中。未查 `SELECTCASE` 的 CASE 式解析
  （`GameProc/Function/Instraction.Child.cs` 的 CASE 相關處）。INSTANT 模式專用、預設路徑不經過；Python 仍只印「（未實作）」。
- [ ] `GAME_MODE_CHECK_F`／`GAME_MODE_CHECK`（GAMEMODE.ERB:124–137）以全域 `COUNT` 當 FOR 變數（S12）。呼叫端若在 `FOR COUNT`
  迴圈中呼叫 `CHECK_GAMEOVER_F()` 會被改寫；已移植的呼叫端（SHOP／SHOP_TURNEND／SET_PARTYMEMBER（CCOUNT）／PRISON（LOCAL:999））
  都不是用 COUNT 迴圈，Python 未模型化 COUNT。之後移植新呼叫端時需確認。
- [x] 悪堕ちキャラ戰（FLAG:110 > 0）中受精時 `NINSIN_HANTEI`:150–151 的 `TENTACLE_ACCESS "GETNAME"`（S13）— S19 確認：
  ENCOUNT_ENEMY:22 SAVESTR:13 = "BOSS"、ACTION.ERB:37–38 FLAG:10 = FLAG:11 = 0 → `TENTACLE_BOSS_0_GETNAME` 不存在，TRYCALLFORM 不發，
  RESULTS 為錯誤字串（`battle.core.tentacle_access`；deviations「原作行為」S19）。
- [ ] 悪堕ちキャラによる幽閉（CFLAG:20 = 2）的 `EVENT_PALAM_HOSEI`（`EVENT_PALAM_UP.ERB`:134–140，S19）— `TENTACLE_ACCESS_PRISON`
  （`COMMON_TENTACLE_DATA.ERB`:314–343）對 CFLAG:20 = 2 無分岐，關數終端只設 RESULT:0 = 0（`Process.ScriptProc.cs`:61–67），
  RESULT:1〜11 為殘值 → `UP:k = RESULT:k / 100`（覆寫）。**S20 調查結論：不固定**。
  - 引擎：RESULT:1 以上只由多值 `RETURN a, b, …`（`GameProc/Function/Instraction.Child.cs`@RETURN_Instruction:1995–2022 →
    `VariableEvaluator.cs@SetResultX`:1732–1740，只寫給定個數）、ERB 的 `RESULT:n =` 代入、VARSIZE 命令（2D/3D）、ENCODETOUNI、
    INPUTMOUSEKEY 寫入；本作後三者未使用（grep 0 件）。RESULT 是跨呼叫的全域變數。
  - 到達路徑（TARGET 的 CFLAG:20 = 2 且 CFLAG:0 ∈ {1,2,3,9}）：①`SHOP_TURNEND.ERB`:105 PRISON → `PRISON.ERB`:28 PRISON_EVENT →
    PRISON_COMABLE → `PRISON_COMn`（例 `PRISON_COM0_Ｃ責め.ERB`:180）→ `COMMON_PRISON.ERB`:38 → `EVENT_PALAM_UP.ERB`:24 → :136；
    ②ゲームオーバーモード中（PRISON.ERB:13 `CHECK_GAMEOVER_F()`）CFLAG:20 = 2 のまま陥落した 2／3／9 のキャラも同じ路；
    ③悪堕ちキャラ自身が CFLAG:20 = 2 の場合の AKUOTI_EVENT 被調教系（`FORCE_悪堕ちキャラの淫謀.ERB`:1609–1710 の COMMON_PRISON）。
    CFLAG:20 = 2 の設定は `BATTLE_COM_AFTER.ERB`:1069 のみ（悪堕ちキャラが【寄生】持ち・CONFIG_CHECK_MANIAC_F(13)）。
  - 各路で :136 直前に RESULT:1〜11 を最後に書く候補（どれが最後かは状況次第）：
    a) 同じ PRISON ループで先に処理された、ボスに幽閉されたキャラ：その :136 の `TENTACLE_ACCESS_PRISON`:327（`TENTACLE_BOSS_n_PALAM_HOSEI`
       の 12 値、例 `TENTACLE_BOSS_1_Ｃ触手.ERB`:125）→ その後の `PRISON_GAPING`（各 PRISON_COMn で COMMON_PRISON の**後**、例 COM0:190）
       内の `SET_TENTACLE_SIZE`（`GAPING.ERB`:1069–；ボスは `TENTACLE_BOSS_n_TENTACLE_SIZE` の RETURN 8 値〔RAND 含む〕、悪堕ち相手は
       :1098–1101 で RESULT:0〜7 = ABL×10+50／1）→ `GAPING.ERB`:1336 `RETURN ARG:2, ARG:3`（RESULT:0〜1）。
       → RESULT:1 = 前のキャラの A 拡張経験予定値、:2〜7 = 前のキャラの触手サイズ・本数、:8〜11 = 前のボスの補正値。
    b) 当該キャラの前回の PRISON_EVENT（a が無い場合）：自分の PRISON_GAPING（RESULT:0〜1）と SET_TENTACLE_SIZE（:1098–1101、
       RESULT:2〜3 = 悪堕ちキャラの Ａ／Ｂ感覚×10+50、:4〜7 = 1）。RESULT:8〜11 はさらに古い書き込み。
    c) その間に走る他の書き込み：同じ EVENTTURNEND の RECALC_PARTYMEMBER → INMON_RECOVERY（`SHOP_TURNEND.ERB`:859–860 RESULT:1）、
       前回の AKUOTI_EVENT（`FORCE_悪堕ちキャラの淫謀.ERB`:706–716 RESULT:1）、口上・地の文中の `SELF_CALL_ANALYSIS`
       （`口上システム関係/SELF_CALL.ERB`:356 RESULT:0〜4）・`CHECK_SINGLE_SOUND`（:381–425 RESULT:0〜2）、PRISON_COM100／104／300 の
       `COMMON_PRISON_EXP_SH`（`COMMON_PRISON.ERB`:71 RESULT:0〜3、ただし COMMON_PRISON の後）、戦闘の `SEX_COMEX`（`SEX_COMEX.ERB`:338
       RESULT:0〜11）・`TENTACLE_SYASEI.ERB`:119–607（0〜3）・`COMMON_BATTLE_HANTEI.ERB`:410–415（0〜1）・`ABL_UP_CHECK.ERB`:1235（0〜3）・
       `PALAM_UP.ERB`:147（RESULT:1）・`TENTACLE_ACCESS`:253／307（0〜11）。
  - 結論：キャラの並び・他の幽閉者の有無・その回の触手サイズ乱数・口上の内容で変わる。照原作移植するには全域 RESULT 陣列を
    Python 側で模型化し、上記すべての書き込み元（移植済み部分）で更新する必要がある（大規模）。代案（要裁決）：殘值を特定の値とみなす
    DEVIATION（例：全て 100 = ボスの既定補正と同じ → UP = 1、または 0 → UP = 0）。現状は停止のまま。
- [ ] 悪堕ち容姿（`ヒロイン関連/悪堕ち/CORRPUTION.ERB`、`CORRUPTION_RECOVER.ERB`，S19 未移植）— CORRUPT_CHANGE_LOOKS_MAIN:20–21 在
  `CONFIG_CHECK_PRISON_F(4) == 0`（基本セット）時直接 RETURN；CFLAG:80 bit2（AFTER_RESCUED:29 的 RECOVER_CORRUPTION 條件）只在 :65 設定
  → 預設設定下兩者都到不了。設定 ON 時仍停止。
