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
- [ ] `DIM.ERH`:20 `GFLAG`（「全領域参照用」）用途未調查。
