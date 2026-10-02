# 現況（唯一真相，≤120 行）

更新：2026-10-02（S21）

## 已完成（各階段細節見 git log 與 wiki）

- 基線：`source/earGVP/`（原作，唯讀）、`reference/emuera-1824/`（引擎原始碼，查證用）。
- **S01** 原作分析 wiki（`docs/wiki/era/`）＋骨架、CSV 載入器。**S02** 狀態模型（`docs/wiki/python/state.md`）、JSON 存讀檔、文字輸出層。
- **S03** 引擎規格查證、新遊戲、SHOP Web（`python -m eragvt`）、存讀檔（0–19＋自動 99）。
- **S04** 行動（休憩・鍛錬・出撃）與 TURNEND／EVENTSHOP（`docs/wiki/era/actions.md`）。**S05** 戰鬥核心。**S06** 拘束・性攻擊・敗北 → 幽閉。
- **S07** 口上／地の文 catalog（`eragvt.narration`，`docs/wiki/python/narration.md`）。**S08** 幽閉（`docs/wiki/era/prison.md`）。
- **S09** 身體資料（`docs/wiki/era/body-profile.md`）。**S10** 開局改回原作預設路徑（`docs/wiki/era/flow.md` §1）。
- **S11** 拡張度・いちゃラブ（`docs/wiki/era/gaping.md`）、模擬腳本 `tools/sim.py`。**S12** ゲームオーバーモード（`flow.md` §9）。
- **S13** 妊娠・出産・子供（`docs/wiki/era/pregnancy.md`）。**S14** 動画流出＋動画サイト視窗（catalog INPUTS／GOTO）。
- **S15** 戰後レイプ・自慰系。**S16** ＳＰ変身・バースト。**S17** 寄生。**S18** 強制發生事件（脅迫・夜這い・子触手）。
- **S19** 悪堕ちキャラ（`docs/wiki/era/akuoti.md`）：淫謀・洗脳／悪堕ちキャラ戰。**S20** 襲撃／救援イベント戰（`game.raid`）＋裁決修正 6 項＋斜體。
- **S21** 共用 RESULT＋触手拘束具＋悪堕ち容姿＋防衛力負數裁決（下節）。測試共 1328 個（新增 `tests/test_result_cloth_corrupt.py` 46）。

## S21 內容

- **共用 RESULT**（`GameState.result`，`docs/wiki/python/result.md`）：引擎上 RESULT 是存檔對象、大小 1000、多值 RETURN 只寫給定格數、
  函式終端只設 RESULT:0。存檔 `SAVE_VERSION = 2`（v1 migration）。已移植的 RESULT:1 以後寫入來源全部同步寫入（TENTACLE_ACCESS(_PRISON)、
  SET_TENTACLE_SIZE、PRISON_GAPING、COMMON_PRISON_EXP_SH、SEX_COMEX(_RANDOM)、ACT_HANTEI、TENTACLE_SYASEI 系、PALAM_UP:147、ABL_UP_EX、
  INMON_RECOVERY、淫謀動画拡散、GENERATE_CHAR_SIZE、WINDOW_*〔全消去〕）；catalog 的 RESULT 也改用同一陣列（失敗回復時一併復原）。
  悪堕ちキャラ幽閉的 PALAM_HOSEI 讀殘值（照原作，unresolved 結案）；TENTACLE_SAKUSEI／COMF103 的不發 TRYCALLFORM 讀 RESULT:0。
- **触手拘束具**（CFLAG:42 = 400）：イベント戰時間切れ後的強制裝着（SUBEVENT_BATTLE_SETTENTACLECLOTH）、每回合被姦（ACTTENTACLECLOTH：
  SEX_COMEX/2 → 補正 → COMMON_PALAM，照原作的添字錯位）、COMF103 素股焦らし失敗文（含處女喪失 :125–159）。拆除只在未移植的 [112] 衣裝設定
  （預設路徑不操作）、完堕ち、イベント戰衣裝還原。地の文 MESSAGE_SUBEVENT 走 catalog。
- **悪堕ち容姿**（`eragvt.game.corruption`）：CORRUPT_CHANGE_LOOKS_MAIN／CORRUPT_CHANGE_LOOKS／各 GET_CORRUPTED_*／SPNAME／THEME／NANORI_FINAL、
  RECOVER_CORRUPTION（定着・完堕ち）。接上 PRISON 悪堕ち、淫紋陥落、開局デフォルト悪堕ち、AFTER_RESCUED。基本セット（F(4) OFF）下不作用。
- **catalog 擴充**：SPLIT、STRFINDU／STRCOUNT／REPLACE／ISNUMERIC／TOINT → `MESSAGE_AKUOTI.ERB`・SETCOLOR_BY_STR・SELF_CALL_ANALYSIS 等可執行。
  覆蓋率 13384 中 12844（96.0%）。
- **Part D（使用者裁決 2026-10-02）**：AKUOTI_EVENT 的 SQRT 當 0（確認）、損失式防衛力項當 0（損失 0）、PERFORM_CHEERS_FIRST_HANTEI 的
  `SQRT(FLAG:852 + 625)` 負→0；未移植的 PASTIME_悪堕ち遭遇:19／ACTION_GATHER_INFORMATION:142 之後比照。

## S21 模擬（`tools/sim.py`，seed 0–249，`--max-shop 200`；4 並列分批，`--dump`／`--load` 合算）

| 指標 | 預設 S20→S21 | 初期セット S20→S21 | `--enable-akuoti` S19→S21 | `--corrupt 3` S19→S21 |
|---|---|---|---|---|
| 停止前 SHOP（平均／最多） | 201.00／201 → 同 | 199.47 → 201.00／201 | — → 201.00／201 | — → 201.00／201 |
| ゲームオーバーモード進入／進入後 SHOP 平均 | 250／188.10 → 同 | 248／188.67 → 250／188.65 | — → 250／188.16 | — → 250／184.11 |
| 敗北局／敗北後 SHOP 平均 | 250／192.87 → 同 | 250／191.47 → 250／193.00 | — → 250／192.87 | — → 250／189.40 |
| 停止 | 0 → 0 | 2（触手拘束具）→ 0 | 2（幽閉 PALAM 補正）→ 0 | 195（SQRT 178・補正 16 ほか）→ 0 |

- 全設定とも 250 局すべて上限到達。`--enable-akuoti`（預設）：AKUOTI_EVENT 44098／250 局、悪堕ちキャラ戰 0。
  `--corrupt 3`（預設）：AKUOTI_EVENT 41674／244、悪堕ちキャラ戰 459／204（勝 37・敗 344）、RAID_ATTACK 202。
- 預設・初期セットの襲撃／救援：RAID_ATTACK 82／86、RAID_RESCUE 38／21（S20 とほぼ同じ）。

## 下一步

- 候選：[反撃]スタイル、狀態畫面、設定畫面／プリセット、FLASHNEWS、ランダム命名畫面、ラスボス、SHOP [112] 衣裝設定（触手拘束具の取り外し）。
- 已裁決（2026-10-02）：PALAM_HOSEI 殘值照原作、防衛力負數 D1〜D4（S21 實作）。已裁決（2026-10-01）：S20 的 DEVIATION 6 項＋斜體。
- 已裁決（2026-09-30）：拡張度初期值照原作；S13 苗床出産的 static LOSEDEF 等怪處照原作。
- 口上 catalog 待擴充：改狀態的口上（hook 化）、入れ子內 $ラベル 的 GOTO（`KOJO_AEGI.ERB` $ＭＡＸ２，199 函式）、STRDATA、未實作式中関数。
- deviations.md 需裁決：振り解く `LOCAL:O`、口上的狀態副作用、口上 catalog 實行時失敗的回復、S08 以後新增項（含 S21 開局デフォルト悪堕ち的輸出丟棄）。

## 仍會停止的分岐（`NotImplementedError` → Web 停止）

S21 模擬 4 設定皆無停止。登記但罕見：
- 悪堕ち：名乗り改竄時 STRMATCH 不成立（RESULTS:2 殘值，unresolved）、悪堕ち戰中 TENTACLE_ACCESS 的數值鍵（安全網）。
- 襲撃／救援：ラスボス出現後（FLAG:100 = 0）の襲来、RAID_HANTEI のデバッグ入力、原作でも CodeEE になるエラー路。
- 幽閉：ラスボス 的幽閉、TS 性別變化、ラスボス出現後的淫紋陥落。
- 妊娠・子供：TS 変身キャラ妊娠時的女體化、子供名字等的手入力（INPUTS）與ランダム命名畫面、デバッグモード的妊娠確率輸入。
- TURNEND：ENDING_1 的エンドレス分岐。拉致監禁的救出（CFLAG:71）只能經情報収集（未移植）。
- 夜這い：TS キャラ的 `_ABLUP` 女体受容取得、`%CALLNAME:ARG%` 指向不存在角色（原作也報錯）。
- 指令：反擊（[反撃]スタイル、`HANGEKI_TO_TENTACLE`）、戰鬥基礎 Lv5 的變身能力獲得（SENGIUP）。
- ステータス PALAM 表示（FLAG:801 bit 5）、觸手服（ACTTENTACLESUIT・運動快感）、雜魚／クズ市民／ラスボス／事件戰／エンドレス、
  ボスの返り血（SUPART_BLOOD）、デバッグ模式、`HATUJOU_TO_HAIRAN` 地の文。

## 已知問題

- 未決：`docs/wiki/bridge/unresolved.md`；偏離：`docs/wiki/bridge/deviations.md`（整體「暫時維持」，S06 以後新增項待裁決）。
- 無 BOM 的 7 個角色 CSV 在原版 1.824 會以 Shift-JIS 讀（亂碼）；本程式以 UTF-8 讀，可能是 +v10 差異，待實機確認。
- 開局：預設（NORMAL＋汎用キャラ 3 名おまかせ）與初期セット「特装戦隊」；其他初期セット／キャラメイク畫面的手動設定未移植。
- 可玩範圍：休憩・鍛錬・出撃（含拘束戰鬥、拡張度、敗北後幽閉與救出、戰後レイプ、襲撃／救援イベント戰）、夜間いちゃラブ・自慰、
  妊娠・出産・子供、全滅後的ゲームオーバーモード。其他行動、11 日目夜的日數超過結局等會進入 Web「停止」畫面。
- 初期セット選項的角色身體資料為 0（原作同樣不生成），戰鬥中女性敏捷 0・攻擊 2 倍（原作行為，是否偏離待決定）。
- RESULTS／COUNT 仍未與 Python 共用（catalog 專用暫存，deviations「口上 catalog 的顯示簡化」）。
