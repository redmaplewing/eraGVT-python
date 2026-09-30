# 現況（唯一真相，≤150 行）

更新：2026-09-30（S08）

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


- **S06**：拘束與性攻擊。出撃 → 戰鬥 → 被拘束（性攻擊・拘束中指令）→ 脫出／勝利／時間切れ／撤退 → SHOP，或敗北 → 幽閉（停在 TURNEND）。
  - `battle.enemy`：ENEMY_ACTION 拘束分岐（:969–1009、再行動・連續行動）；`sexcom`：SEX_COMABLE、SEX_COM0–20、SPCOM0–15、
    SEX_COMEX(_RANDOM)、AUTO_V_DEFENCE（INPUT）、ボス 1–7 SEX_ROUTINE／REACTION_REF、ENEMY_ACTION_SEX_ROUTINE；`sexmsg`：性攻擊地の文
    中的狀態變化（本文以「〈地の文：…〉」一行代替，deviations）；`gaping`（觸手サイズ・拡張度；CFLAG:34 = 0 時不動作）、
    `syasei`（TENTACLE_SYASEI_UP／CHECK／POINT、SAKUSEI）、`ninsin`（受精判定到成立前）。
  - `palam.palam_up` 全面移植（結界消耗、絶頂・我慢・懇願、キャラ射精／噴乳、體力氣力性耐性低下、刻印、JUMP SOURCE_CHECK）；
    `source_check`：暴れる、拘束中自動振り解き、麻痺・腰くだけ・恍惚持續、BATTLE_LOSE（:969–1095 → 幽閉）；`hantei`：振り解く判定、
    暴れる傷害；`cheers`：性攻擊時的觀眾反應；`after`：EVENTEND 敗北分岐（:335–422）、SUBEVENT_RELEASE_ECSTASY。
  - `restraint`：COM_ABLE 8–15・40・44–47・70・100–104、COMF8–14・40・44–46・100–104；`train.show_usercom` 拘束分岐（:382–441）；
    `commands`：COM6 背後に回る・7 見切り・16／17 切替・69 何もしない・71／72 EX ゲージ。
  - 修正 S05：`message_branch_faith_down` 性抵抗分岐的文與旗標、`SENGIUP` 的 `&&`／`||` 優先順位（同順位・左結合）。
  - 測試共 349 個（新增 `tests/test_battle_restraint.py`、Web 拘束戰→存讀檔 1 case）；Chromium 實機跑完拘束戰→SHOP。

- **S07**：口上／地の文抽取管線（`eragvt.narration`，設計：`docs/wiki/python/narration.md`）。執行期從 `source/earGVP/ERB` lazy 抽取
  （啟動約 0.5 秒、不落地），「文字輸出＋條件分岐」子集以執行器求值（RAND 照 ERB 順序、引擎語意附 reference 行號）。
  - `NarrationService` 改為 `call_kojo(ctx, C_NO, code)`（KOJO_ROOT.ERB:46–90 派發）／`run_function(ctx, 函式, args)`；
    `action.kojo_root_full` 移植 KOJO_ROOT 全體。Web 預設用 `CatalogNarrationService`（無 `ERB/` 時 Null）。
  - 接上：SHOP 一口メッセージ、全 `kojo_root` 呼叫點、性攻擊地の文（`sexmsg` 33 函式＋COM15–20，狀態變化行 140 行經 `narration/hooks.py`
    依 ERB 順序執行）、射精・處女喪失・ヒロイン側性攻撃・敗北 `MESSAGE_BATTLE_END_LOSS`（`core.run_chinobun`）。
  - 修正 S06：地の文中的 `KOJO_ROOT`（LOSTVIRGIN、SYASEI_*、SEX_ATTACK104）在 Null／佔位路徑也照原作呼叫。
  - 覆蓋率（`python -m eragvt --narration-report`）：口上／地の文函式 **13384，可執行 12814（95.7%）**。unsupported 第一原因前 10：
    GOTO 199、CFLAG 代入 186、TALENT 代入 32、NAME／CSTR／BASE 代入 各 20、CDFLAG 代入 13、未對應變數 TCVAR 12、STRDATA 9、SPLIT 8。
    （「代入」＝口上本身改狀態，依規格不移植 → 當「找不到」，deviations 需裁決。）
  - 隨機方針 40 場模擬（seed 0–39）：catalog 實行時失敗 0、例外 0；停止原因同 S06。測試共 381 個（新增 `tests/test_narration.py` 32）。

- **S08**：幽閉（設計與 CFLAG 對照：`docs/wiki/era/prison.md`）。敗北 → TURNEND（SET_PARTYMEMBER／SHIFTBACK_CHARA 把離隊者移到最後）→
  每回合 PRISON_EVENT（17 種幽閉指令、EVENT_PALAM_UP、刻印、淫紋、汚染度）→ 脫出／救出（ボス擊破、指令 15、AFTER_RESCUED／
  RECOVER_TO_PARTY）或 洗脳・悪堕ち・取り込まれ；全滅 ENDING_1 與ソロ ENDING_4／5 顯示本文後停止（ゲームオーバーモード未移植）。
  - 新模組：`eragvt.game.prison`（event／commands／event_palam）、`party`、`tattoo`、`ending`；`turnend.inmon_recovery` 全移植
    （救出後淫紋進行 → 悪堕ち／自ら幽閉）、PARASITE 前半（寄生経験・順応値，事件本體停止）；`_ABLUP, 1`、淫壷取得、
    NINSIN_HANTEI 的 ARG:2 父親指定；SHOP `[130] 状況の確認`（SHOP_SHOW_SITUATION_LIST 全體）。
  - 地の文（MESSAGE_PRISON／OTHER 的 PRISON 系／KYUUSHUTU／刻印）走 catalog；狀態變化 21 行進 `hooks.PRISON_HOOK_LINES`。
  - Web：@EVENTSHOP 內的未移植也改為「停止」（先前會例外）。測試共 481 個（新增 `tests/test_prison.py` 100，含 Web 敗北→幽閉→SHOP→存讀檔 E2E）。
  - 幽閉單獨壓力測試（30 seed × ボス 7 種、catalog）：取り込まれ 119／受精成立停止 67／SET_PROFILE 停止 24，catalog 失敗 0；
    洗脳選項 ON＋半數触手の虜：洗脳 54／悪堕ち 55／受精 76／SET_PROFILE 25。

## 下一步

- 未指定 S09。候選：妊娠（NINSIN_SUBMIT 以降；戰鬥・幽閉兩處最常見的停止）、ゲームオーバーモード（CHANGE_GAMEOVER_MODE：
  全滅後的繼續）、動画流出（DOUGA_RYUSUTU）、ＳＰ変身／ＳＰバースト／バースト攻擊、身體資料生成（SET_PROFILE／CHARA_SIZE：
  也解決女性敏捷 0・傷害 2 倍的 deviation）、悪堕ちキャラ（AKUOTI_ATTACK、悪堕ち戰、容貌變化）。
- 口上 catalog 待擴充：改狀態的口上（hook 化）、GOTO、SPLIT／STRDATA、未實作式中関数（覆蓋率報告）。
- deviations.md 需裁決：振り解く `LOCAL:O`、口上的狀態副作用、口上 catalog 實行時失敗的回復、S08 新增項。

## S08 後仍會停止的分岐（`NotImplementedError` → Web 停止）

隨機方針 250 場模擬（`GameRng` seed 0–249，全員隨機預約、戰鬥隨機按鈕、catalog）依頻度：全滅 ENDING_1 後的ゲームオーバーモード 116、
動画流出 39、受精成立 30、ＳＰ変身 20、ＳＰバースト 11、バースト攻擊（COM17）的回避補正 10／攻擊 7、膨乳化 SET_PROFILE 7、
強制自慰 6、戰後レイプ 4。敗北後平均再走 1.5 個半日（最多 7；幽閉最多 8 回）——女性角色敏捷 0・傷害 2 倍（deviation）使敗北極快，
3 人常在數回合內全滅。其餘登記但罕見：
- 幽閉：ラスボス／悪堕ちキャラ 的幽閉、容貌變化（設定 ON）、RECOVER_CORRUPTION、RESCUE_CHILD、TS 性別變化、ラスボス出現後的淫紋陥落。
- TURNEND：AKUOTI_ATTACK（悪堕ち後）、寄生触手的暴走／共生取得、BIRTH_HANTEI／GROW_HANTEI、INTIMIDATION／KIDNAPPING。
- 指令：47 説得する、反擊（[反撃]スタイル、`HANGEKI_TO_TENTACLE`）；戰後妊娠判明（NINSIN_CHECK_AFTER）、戰後自慰。
- 拡張度（CFLAG:34 != 0）、素股焦らし失敗的處女喪失、觸手服／觸手拘束具、悪堕ち／雜魚／クズ市民／ラスボス／事件戰／エンドレス、
  デバッグ模式、`HATUJOU_TO_HAIRAN` 地の文。

## 已知問題

- 未決：`docs/wiki/bridge/unresolved.md`；偏離：`docs/wiki/bridge/deviations.md`（整體「暫時維持」，S06–S08 新增項待裁決）。
- 無 BOM 的 7 個角色 CSV 在原版 1.824 會以 Shift-JIS 讀（亂碼）；本程式以 UTF-8 讀，可能是 +v10 差異，待實機確認。
- 開局僅支援「NORMAL＋特装戦隊」；其他初期セット／自訂角色會 `NotImplementedError`。
- 可玩範圍：休憩・鍛錬・出撃（含被拘束的戰鬥、敗北後的幽閉與救出）。其他行動、11 日目夜的日數超過結局、妊娠等狀態會進入
  Web「停止」畫面（deviations、上一節）。
- 身體資料（体重・胸の重量）為 0，戰鬥中女性角色敏捷被扣成 0、傷害 2 倍（deviations，需裁決）。
- 襲撃／救援（DAY ≥ 3）與子触手襲来成立時只顯示「スキップ」訊息（deviations）。
