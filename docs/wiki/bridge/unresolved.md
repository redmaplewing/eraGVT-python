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
- [ ] `W08` 無 BOM 的 UTF-8 角色 CSV（`_ADD/Chara160–163`、`Chara18xx_New Generation/CHARA1805–1807`）— 原版 1.824 以 Shift-JIS 解碼（`Sub/EraStreamReader.cs`:42 `new StreamReader(stream, Config.Encode)`、`Config/Config.cs`:17 SHIFT-JIS），這 7 檔會亂碼、連 `番号` 都讀不到；本作附的是 `Emuera1824+v10.exe`，**可能是 +v10 差異**（自動判別 UTF-8）。目前以 UTF-8 讀（`csv_loader.read_enabled_lines`，`# UNVERIFIED`）。需要時請在實機確認這些角色能否出現。
- [ ] `W08` 無 BOM 的 ERB `ゲーム内_イベント発生/特別活動イベント.ERB`（S07 發現；全 ERB/ERH 中唯一）— 1.824 以 Shift-JIS 讀
  （同上 `EraStreamReader.cs`:42），函式名會亂碼而找不到；catalog 以 UTF-8 讀（`narration.extract.read_logical_lines`）。
  口上／地の文沒有呼叫此檔的函式，目前不影響。可能是 +v10 差異。
- [ ] `W08` 未定義識別子 `LOCAL:O`（`ゲーム内_戦闘処理/COMMON_BATTLE_HANTEI.ERB`:241／:245，振り解く判定）— 1.824 在第一次執行該行時
  才解析引數（`GameProc/Process.ScriptProc.cs`:38–42），`O` 找不到 → `IdentifierNotFoundCodeEE`（`GameData/IdentifierDictionary.cs`:645）
  → 停止。原作附的 `Emuera1824+v10.exe` 是否同樣報錯未確認（reference 只有 1.824）。目前當 `LOCAL:0`（deviations.md）。
  S27：`エンディング/SCORE.ERB`:150 `FOR CCOUNT, O, CHARANUM` 同類（クリア時必經），目前當 0（deviations.md「SCORE 的 FOR CCOUNT, O」）。
  **兩處按0處理已經使用者裁決，不重開決策；本項未決僅為原作附帶+v10與reference 1.824的引擎行為差異查證。**

## 原作邏輯

- [x] `TFLAG:0`（戰鬥回合數）遞增處 — `ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK`:1313–1318（先制攻擊中扣 `TFLAG:24`，否則 `TFLAG:0 += 1`）。
- [ ] `W08` 一覧:594 說回合上限在 `TCVARn:13`，程式實際用 `ERB/DIM.ERH`:280 `ターン上限` — 以程式為準。
- [x] 雜魚／クズ市民戰在體力・氣力・性耐性全 0 時的結束路徑 — `BEGIN AFTERTRAIN` 全作只有 6 處（grep：`BATTLE_COM_AFTER.ERB`:435 勝利、
  :950 敗北、:1095 強拘束敗北、:1130 時間切れ；`BATTLE_COM.ERB`:596／:614 撤退），`TFLAG:98` 只在 :129（=1 勝利）、:852、:973（=2 敗北）設定。
  :955／:1303 的一般敗北判定排除 MOB／CITIZEN，所以**雜魚戰全 0 也不會敗北**，只能以勝利・時間切れ（15 回合）・撤退結束；
  クズ市民戰則由 :850 的專用判定（全 0 且被拘束 → 監禁 `CFLAG:0 = 4`）敗北。基本設定（FLAG:802 bit4 = 0）下雜魚遭遇只有文章
  （`ENCOUNT.ERB@MOB_TENTACLE_ENCOUNT`:449–521），不進 TRAIN。
- [x] TRAIN 的輸入 — 本作 `COMABLE.ERB` 的 38 個 `@COM_ABLE` 在 `TCVARn:8 < 10` 時全部 RETURN 0（35 個有 `SIF TCVARn:8 < 10`，
  201–203 最後回傳 `COM_ABLE0` 的結果），引擎的選項清單（SystemProc@endCallComAbleXX:312–354）永遠是空的，輸入一律經 `@USERCOM`
  （`BATTLE_COM.ERB`:572–664）再 `DOTRAIN`。
- [x] 角色 CSV `相性` 的轉換 — 只在 `HEROINE_PRESET` 選 `[30]` 時經 `SYSTEM/キャラメイキング関連/FIRSTSETTING_CONVERTCSV.ERB@CONVERT_RELATION`:3–23 把「CSV 番号索引」複製到「登錄 index 索引」（直接使用 SELECT，不以 `CFLAG:240` 查找）。直接開始遊戲時不轉換；S51 已接通，保留正值覆寫、舊格與重入轉換，見 `../era/relation-setting.md`。引擎本身 RELATION 的索引是 CSV 番号（`VariableCode.cs`:146）。
- [x] `DIM.ERH`:20 `GFLAG`（「全領域参照用」）— 全 ERB 只有 `FORCE_夜這い.ERB` 使用（grep：DIM.ERH 以外僅此檔），YOBAI_EVENT:113 VARSET 後當夜這い組合表（S18，`eragvt.game.yobai`）。
- [x] 救出時間切れ `TFLAG:9`（S08）— 只有 `COMF15.ERB@KYUSHUTU_TIMEUP_HANTEI`:64 讀取（由 `BATTLE_COM_AFTER.ERB`:1115 TRYCALL），
  全 ERB（含口上）沒有代入處（`grep -P "TFLAG\s*:\s*9(?![0-9])"` 全 ERB／ERH 僅 1 筆）→ 地の文 `MESSAGE_KYUUSHUTU_TIMEUP` 不會出現。照原作（deviations「原作行為」）。
- [x] `@SHIFTFOWARD_CHARA`（`ヒロイン関連/SET_PARTYMEMBER.ERB`:48–64）— 全 ERB 沒有呼叫處（grep 只有定義行）→ 不移植。
- [x] `TOINT` 對 cp932 無法編碼字元的處理（S10→S50）— `Creator.Method.cs:2363`、`_Library/LangManager.cs:12–20`、
  `Config/Config.cs:134` 指定 Encoding(932)。已以 .NET Framework 4 實測全 BMP 長度、數字分類及非 BMP 替代；
  `chara_make.toint` 與 `colorbar.isnumeric` 共用完整數值解析，不再因未移植而停止，原引擎轉換錯誤仍保留；重現步驟見 `python/numeric-input.md`。
- [ ] `W06／W08` `SHOP.ERB@USERSHOP:288–294`的`CASE 169 && GAME_OPTION_CHECK_F(...)`式語意 — 舊S12記錄尚未結案；S43／S44已接通169／170／180（`game/session.py:283–297`與對應wiki），不再是只印未實作。需核對引擎CASE解析、原作實際入口與現行條件是否一致，必要時交使用者裁決；不能以目前測試通過代替查證。
- [ ] `W07／W08` `GAME_MODE_CHECK_F`／`GAME_MODE_CHECK`（GAMEMODE.ERB:124–137）以全域 `COUNT` 當 FOR 變數（S12）。呼叫端若在 `FOR COUNT`
  迴圈中呼叫 `CHECK_GAMEOVER_F()` 會被改寫；已移植的呼叫端（SHOP／SHOP_TURNEND／SET_PARTYMEMBER（CCOUNT）／PRISON（LOCAL:999））
  都不是用 COUNT 迴圈，Python 未模型化 COUNT。之後移植新呼叫端時需確認。
- [x] 悪堕ちキャラ戰（FLAG:110 > 0）中受精時 `NINSIN_HANTEI`:150–151 的 `TENTACLE_ACCESS "GETNAME"`（S13）— S19 確認：
  ENCOUNT_ENEMY:22 SAVESTR:13 = "BOSS"、ACTION.ERB:37–38 FLAG:10 = FLAG:11 = 0 → `TENTACLE_BOSS_0_GETNAME` 不存在，TRYCALLFORM 不發，
  RESULTS 為錯誤字串（`battle.core.tentacle_access`；deviations「原作行為」S19）。
- [x] 悪堕ちキャラによる幽閉（CFLAG:20 = 2）的 `EVENT_PALAM_HOSEI`（`EVENT_PALAM_UP.ERB`:134–140，S19）— `TENTACLE_ACCESS_PRISON`
  （`COMMON_TENTACLE_DATA.ERB`:314–343）對 CFLAG:20 = 2 無分岐，關數終端只設 RESULT:0 = 0（`Process.ScriptProc.cs`:61–67），RESULT:1〜11 為殘值。
  S20 調查：殘值依角色順序・其他幽閉者・觸手サイズ亂數・口上而變（路徑 a〜c）。**S21 結案**（使用者裁決 2026-10-02：照原作）：
  RESULT 改為 `GameState.result` 共用陣列，已移植的全部寫入來源同步寫入（一覽 `docs/wiki/python/result.md`），:136 讀共用陣列。
  測試 `tests/test_result_cloth_corrupt.py`（路徑 a／b 的代表情形）。
- [x] 悪堕ち容姿（`ヒロイン関連/悪堕ち/CORRPUTION.ERB`、`CORRUPTION_RECOVER.ERB`）— S21 移植（`eragvt.game.corruption`）。
- [x] `CORRPUTION.ERB@CORRUPTTION_GET_NANORI_FINAL`:786–791（S21）— `STRMATCH`（`コモン関数.ERB`:1378–1393）在名乗り（CSTR:3）中找不到
  原變身後名（CSTR:55）時不寫 RESULTS:2 → :787 讀到前一次的 RESULTS:2。**S22 結案**（使用者裁決 2026-10-02：照原作）：RESULTS 改為
  `GameState.results` 共用陣列（引擎：不存檔、讀檔／新遊戲清空；寫入來源一覽 `docs/wiki/python/result.md`），STRMATCH 同步寫入、:787 讀共用陣列，
  停止點解除。測試 `tests/test_results_shared.py`（不成立＋前值非空／空、連續 2 人）。
- [ ] `W08` `.NET string.IndexOf(string, int)`（STRFINDU，`Creator.Method.cs`:2273）是文化相依比較；S60姓名STRFIND、catalog／corruption 以 Python `str.find`（序數）
  實作。本作用到的字串（假名・漢字・記號）在 CompareOptions.None 下應一致，但 reference 內無法確認 .NET 文化表（S21）。
- [x] BEGIN 在被 CALL 的函式中（S28a）— 只設定 begintype 並 Return 一層，呼叫端繼續執行，最後一次的 BEGIN 在函式堆疊清空時生效
  （`GameProc/Function/Instraction.Child.cs@BEGIN_Instruction`:1681–1689、`GameProc/Process.State.cs@SetBegin`:203–228／`@Return`:355–425／`@Begin`:263–311）。
  `docs/wiki/era/actions.md`「S28a 補足」。
- [ ] `W07／W08` SCHEDULE 畫面（S28a）的 PRINT 行尾空白：原作行尾有半形空白（CRLF 前），Python 省略；只影響顯示寬度，未查 Emuera 是否保留引數行尾空白。
- [ ] `W08` `TIMES 變數, 實數`（S29，catalog）— 引擎以 `(decimal)double` 計算（`GameProc/Function/Instraction.Child.cs`:905–916），.NET 的
  double→decimal 轉換（有效數字 15 位捨入）不在 reference 內；catalog 以實數字面的原文作 Decimal（`narration.runtime.Interp._times`，`# UNVERIFIED`，
  與 `game.era.times` 同前提），有效數字 > 15 位者 unsupported。本作口上／地の文只有 `0.5`（二進位精確）與 `0.20`（double 略大於 0.2，
  乘整數後截斷結果與精確值相同），實際結果不受影響。
- [ ] `W07／W08` catalog 的 `run_function_gen` 等待 INPUTS 時ジャーナル區間保持開啟（S29）：若等待期間 Web 另外執行會寫 GameState 的 catalog 函式，
  其書き込み會被算進這個區間、重放時一併回復。目前 INPUTS 函式（`MESSAGE_SEX_SPCOM7` 動画サイト等）等待期間沒有其他 catalog 執行路徑，未發生。
- [ ] `W08` `SETCOLORBYNAME` 的色名大小寫（S30，catalog）— 引擎呼叫 `Color.FromName(字串)`（`GameProc/Function/ArgumentBuilder.cs`:364–373、
  `GameProc/Process.ScriptProc.cs`:408–420），名稱比對規則屬 .NET Framework（ColorConverter 的色名表），不在 reference 內。原作
  `地の文/MESSAGE_BATTLE.ERB`:364 寫 `HOTPINK`（KnownColor 名為 HotPink）；catalog 以「不分大小寫」處理（`narration.extract.DOTNET_NAMED_COLORS`，
  `# UNVERIFIED`），表只收本作用到的 HotPink・Fuchsia。已查：reference 全體 grep `FromName`（ArgumentBuilder.cs:366、Process.ScriptProc.cs:411／458、Creator.Method.cs:701、HtmlManager.cs:1011），皆只看 `A == 0`，比對規則不在 reference；各處的 transparent 判定用 OrdinalIgnoreCase 只是旁證。
- [x] `GETBGCOLOR`：S33 已建立 TextOutput 目前背景色，接通既有 SETBGCOLOR／RESETBGCOLOR 路徑及 Web。
  依據 `reference/emuera-1824/Emuera/GameData/Function/Creator.Method.cs:584–599`；來源與驗證見 `../python/narration.md` 的 S33 節。

## S56盤點新增

- [x] `W05／W08` 末王強化時敵方回復漏翻（S81結案）— `ERB/ゲーム内_戦闘処理/ENEMY_ACTION.ERB@ENEMY_ACTION:574–617`依敵類先取末王4%／雜魚16%／其他8%，再按`ERB/ゲーム内_戦闘処理/LASTBOSS_POWERUP.ERB@LASTBOSS_REST:16–22`套除數；已修正固定8%／除2。真鏈為SELECT_TENTACLE_ACTION→SOURCE_CHECK→ENEMY_ACTION（全ERB／ERH的TENTACLE_COM精確搜尋0）；末王1直接抽4，末王2可經FLAG902把2轉4。兩末王ON/OFF、截斷／封頂與真run_train已測，詳[戰鬥分派](../era/battle-dispatch.md)。HP強化與跨回合既有處理不變，無新偏離。


## S78套組10索引（W04／W08）

- [ ] `ERB/SYSTEM/キャラメイキング関連/初期セット/10_髙橋退魔団.ERB@SHOKISET_SELECT_10:43、51`兩次都寫第5人陥落經驗；第6人不增加。第36行註解明示兩角色初始同狀態，第44–50行正在設定第6人，故第51行疑似索引筆誤，但「應改6」是推論，尚待裁決。兩份CSV沒有定義該經驗；按原文將是5=2／6=0。
- 已查該函式全段與365／366模板、`CHARA_MAKE.ERB@CHARA_MAKE_MAIN:154–156、166–168、178–188`（進入該狀態加1、離開減1）及`ERB/ヒロイン関連/悪堕ち/CORRPUTION.ERB@CORRUPT_CHANGE_LOOKS_MAIN:57`（經驗>=3條件）。第6人離開狀態原文可減為-1；這是已知下游影響，不能自行修正。
- 本次分支因具體未成年模板的性經驗初始化保留未實作，見[套組範圍](../era/initial-presets.md)；索引裁決本身不會解除此範圍阻塞。沒有執行該初始化或建立其性經驗expected案例。

## S80觀眾妨礙空中回傳（W05／W08）

- [ ] `ERB/ゲーム内_戦闘処理/COMMON_BATTLE_FUNC.ERB@ACT_LIMIT:279–281`註解稱空中無效，執行碼卻在空中位元1成立時`RETURN 1`；`ERB/ゲーム内_戦闘処理/戦闘コマンド(ヒロイン)/COMF3.ERB@COM3:5–10`收到1即取消指令，先於空中旗標更新。已證實效果是「空中也取消行動，只不顯示妨礙」，S80照執行原文移植並測試；註解暗示作者想免疫只是推論。若要改成免疫需使用者另行裁決，本階段沒有修正。
