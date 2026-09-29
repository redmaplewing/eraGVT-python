# 現況（唯一真相，≤150 行）

更新：2026-09-29（S05）

## 已完成

- 建立 repo，`source/earGVP/` 原作基線入庫（唯讀）；`reference/emuera-1824/` 引擎原始碼（查證用）。
- **S01**：原作分析 wiki（`docs/wiki/era/`）＋ `src/eragvt` 骨架、CSV 載入器。
- **S02**：狀態模型（`eragvt.state`）、版本化 JSON 存讀檔、文字輸出層、`NarrationService`。設計：`docs/wiki/python/state.md`。
- **S03**：查證補課 + 新遊戲 + SHOP Web。
  - Part 0：unresolved「Emuera 規格」全部對照引擎原始碼（僅剩無 BOM 檔編碼一項待實機確認）。修正：CSV 解析（省略／無法解析 → 1、
    不 trim、`;` 不處理、番号重複保留先者、JUEL 名稱查 palam）、存檔範圍（TFLAG 存、TCVARn 不存、遊戲代碼／版本檢查）、
    新遊戲 [0, 999]＋TARGET=1、`_Replace.csv`、自動按鈕（移植 ButtonStringCreator）、DAY 改為陣列、flow.md 引擎流程。
  - Part 1：`eragvt.game.opening`（EVENTFIRST 最小路徑：NORMAL＋特装戦隊 301–303，含 CHARA_MAKE_FINALIZE×2、LEVELSTATUS、
    CSVFIX、武器解碼、SET_LIMIT_DAY、RESEARCH_QUOTA）。
  - Part 2：`eragvt.game.shop`／`session`、`eragvt.web`（FastAPI＋Jinja2）。`python -m eragvt` 可在瀏覽器開新遊戲、
    看 SHOP、預約 101–108、切換操作角色、一括設定、存讀檔（0–19＋自動存檔 99）。測試共 227 個。
- **S04**：行動執行＋回合結束。`[100]` 確認後跑完一回合回到 SHOP（晝→夜→翌日晝），可重複並存讀檔。
  - `eragvt.game.action`：`ACTION_MAIN`（一次一人、FLAG:798/799、支援人數、控え・行動不能 → 強制休憩、
    `ACTION_NGREASON`）、`REST`、`TRAINING`（0–10 全選項、INPUT 以 generator 等待；BASEUP／SEIKAKU_HOSEI_F／
    SENGIUP／GET_EXP＋CHECK_LEVELUP／GET_SYUREN）。
  - `eragvt.game.turnend`：`run_turn`（JUMP／BEGIN 迴圈）、`EVENTTURNEND` 主幹（SET_PARTYMEMBER、ENDING 判定骨架、
    RECALC_PARTYMEMBER、BOSS_TENTACLE_RECOVER、DAILY_DEFENCE／POPULARITY、夜間事件的開始條件）、
    `EVENTSHOP` 一般分岐（PARASITE、SMALL_TENTACLE、BIRTH_AUTO_RANDOM、晝夜、RECOVERY_OVER_TIME、ESTRUS_CYCLE、
    日期、CALC_INCOME_EXPEND、新聞旗標、CHECK_SHIELD_ALL）。session 新增 `turn`／`halted` phase。
  - 各行動影響範圍與開局狀態下的事件觸發表：`docs/wiki/era/actions.md`。測試共 273 個。
- **S05**：戰鬥核心。出撃 → 遭遇 → 戰鬥（非拘束狀態）→ 撤退／勝利／時間切れ → EVENTEND → TURNEND → SHOP，可存讀檔。
  - `eragvt.game.battle`：`encount`（ENCOUNT／ENCOUNT_ENEMY／ENCOUNT_BOSS、MOB_TENTACLE_ENCOUNT 文章版、GET_EXP_BATTLE 等報酬）、
    `train`（UpdateInBeginTrain、EVENTTRAIN＋先制、SHOW_STATUS 簡略、SHOW_USERCOM 不分類版、USERCOM、DOTRAIN→EVENTCOM→COMn
    →SOURCE_CHECK→EVENTCOMEND＋自動 WAIT）、`commands`（COM_ABLE／0・201–203・1–3・4・5・99）、`hantei`（命中・傷害）、
    `palam`（PALAM_CAL／PALAM_UP）、`enemy`（ENEMY_ACTION 非拘束分岐、SELECT_TENTACLE_ACTION、ボス 1–7 資料）、
    `source_check`（勝利・時間切れ・狀態異常・回合）、`cheers`、`cloth`、`func`、`after`（EVENTEND 撤退／時間切れ・ボス勝利、
    刻印、蓄積ダメージ）、`ablup`（_ABLUP：珠→能力上昇、素質取得的一部分）。
  - `action_main` 出撃接上；`run_turn` 的 `Step.TRAIN` 以 generator 進入戰鬥（session 沿用 `turn` phase，戰鬥中不能存檔）。
  - 查清 unresolved「雜魚／クズ市民戰結束路徑」「TRAIN 輸入一律經 USERCOM」。基本設定下雜魚只有文章（不進 TRAIN）；
    ボス遭遇需 探索度 FLAG:47 ≥ ノルマ FLAG:46（開局 28，出撃一次 +6〜9），故前幾次出撃不會遇到ボス。測試共 303 個。


## 下一步

- deviations.md：使用者 2026-09-29 裁決「暫時維持現狀」。S05 新增 3 項（戰鬥停止分岐、身體資料 0 對戰鬥式的影響【需裁決】、
  戰鬥畫面簡略），另在「原作行為」補列照翻的疑似 bug。
- **S06：拘束與性攻擊**（規格待寫）。具體起點（路徑相對 `source/earGVP/ERB/ゲーム内_戦闘処理/`）：
  1. 拘束後的敵行動：`ENEMY_ACTION.ERB` 拘束分岐 → `TENTACLE_BOSS_{n}_SEX_ROUTINE`（`触手データ/ボス触手/`）、
     `戦闘コマンド(性攻撃)/`。現在停在 `battle/enemy.py` 的「拘束直後の性攻撃」`NotImplementedError`（隨機戰鬥幾回合就會遇到）。
  2. 拘束中的指令：`COMABLE.ERB` 的 8–15・40・44–47・100–104、`SHOW_USERCOM` 拘束分岐（`BATTLE_COM.ERB`:382–441）、
     `COMF8〜15`（振り解く・救出 等）。`battle/commands.py` 的 `_RESTRAINT_ONLY` 目前在拘束中會停止。
  3. 絶頂・射精：`PALAM_UP.ERB` 的絶頂處理（`battle/palam.py` 目前遇到可能絶頂就停）、`TENTACLE_SYASEI.ERB`、`GAPING.ERB`。
  4. 敗北：`BATTLE_COM_AFTER.ERB`:850–973 → 幽閉（`source_check._battle_lose` 停止中）與 `EVENTEND`:335–422。
  5. 其餘指令 6・7・16・17・69–74（`commands.run_com`）、反擊（`HANGEKI_STYLE.ERB`）、バースト。
  6. 之後：事件戰（襲撃／救援、`turnend._skip_event`）、拠点防衛、雜魚戰系統（CONFIG bit4）、ラスボス。

## 已知問題

- 未決：`docs/wiki/bridge/unresolved.md`；偏離：`docs/wiki/bridge/deviations.md`（尚未經使用者裁決）。
- 無 BOM 的 7 個角色 CSV 在原版 1.824 會以 Shift-JIS 讀（亂碼）；本程式以 UTF-8 讀，可能是 +v10 差異，待實機確認。
- 開局僅支援「NORMAL＋特装戦隊」；其他初期セット／自訂角色會 `NotImplementedError`。
- 可玩範圍：休憩・鍛錬・出撃（戰鬥到被拘束為止）。其他行動、拘束後、11 日目夜的日數超過結局、救出／妊娠等狀態會進入
  Web「停止」畫面（deviations）。
- 身體資料（体重・胸の重量）為 0，戰鬥中女性角色敏捷被扣成 0、傷害 2 倍（deviations，需裁決）。
- 襲撃／救援（DAY ≥ 3）與子触手襲来成立時只顯示「スキップ」訊息（deviations）。
