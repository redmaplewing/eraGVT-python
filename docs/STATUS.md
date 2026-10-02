# 現況（唯一真相，≤120 行）

更新：2026-10-02（S23）

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
- **S21** 共用 RESULT＋触手拘束具＋悪堕ち容姿＋防衛力負數裁決（`docs/wiki/python/result.md`、`eragvt.game.corruption`）。
- **S22** 共用 RESULTS（`docs/wiki/python/result.md`）：不存檔、名乗り改竄讀 RESULTS:2、BATTLE_COM_AFTER:1159 同步。
- **S23** [反撃]スタイル（下節）。測試共 1384 個（新增 `tests/test_hangeki.py` 40）。

## S23 內容

- `battle/hangeki.py`＝`HANGEKI_STYLE.ERB@HANGEKI_TO_TENTACLE`（成否表 :9–52、ＥＸ反撃體勢＋自分の行動、TCVARn:205 蓄積、COM_ATTACK_COMMON 再攻擊、
  戦技經驗・SENGIUP、行動ポイント +2、べとべと回復）；`ENEMY_ACTION.ERB`:933–934 呼叫（體液分岐補 LOCAL:2）。
- `COMF4.ERB`:24–30 [反撃]的防禦＝ＥＸ反撃；`COM_ATTACK_COMMON.ERB`:417–426 反撃準備；完全防御文 PRINTDATAL（:1206–1209）。
  地の文 MESSAGE_BATTLE_CHARA_HANGEKI(_EX)／ATTACK_HANGEKI 走 catalog，悪堕ち戰的 MESSAGE_OTHER_* 亦同。
- `体勢：反撃成功`（302）全作無代入 → ATTACK_HANGEKI 地の文與「反撃成功時の攻撃力」照原作不會發生（deviations S23 記錄，非偏離）。
- `FIGHT_STYLE.ERB@SET_FSTYLE_INFO` 戰鬥中不呼叫（只有武器カスタマイズ與狀態畫面 PAGE3）→ 留給 S25（寫 `GameState.results`）。
- 到達條件：預設（汎用キャラ）與初期セット 0（CSTR:15–17 全「通常」）都不會是 [反撃]；只有武器カスタマイズ（未移植）、
  錦木千束／長沢雪／船田純的 CSV 武器、森亜るるか口上。`tools/sim.py --style 反撃` 為人工設定（全員全距離 [反撃]）。

## S23 模擬（seed 0–249，`--max-shop 200`，4 並列分批）

預設・初期セット與 S22 完全相同（停止 0；敗北後 SHOP 192.87／193.00、ゲームオーバーモード後 188.10／188.65），反撃路徑 0 次。
人工 `--preset tokusou --style 反撃`：停止 0，HANGEKI 呼叫 1345（成功 472）、COM4 ＥＸ反撃 420、反撃準備 1633、[反撃]完全防御文 133。
`--corrupt 3 --style 反撃`：停止 0，HANGEKI 1604（成功 665，含敵行動 5 押し倒す・6 波動）。バースト過剰蓄積 0 次（單元測試覆蓋）。

## 下一步

- **自主推進（使用者指定 2026-10-02，依序）**：~~S22 RESULTS 共用~~ → ~~S23 [反撃]スタイル~~ → **S24 設定畫面／プリセット** → S25 狀態畫面
  → S26 FLASHNEWS → S27 ラスボス → S28 未移植行動（特別活動・防衛・支援・情報・自由）。其他候選：ランダム命名畫面、SHOP [112] 衣裝設定。
- 已裁決（2026-10-02）：名乗り改竄的 RESULTS:2 殘值照原作（S22 實作）；開局デフォルト悪堕ち的輸出丟棄維持現況。
- S23〜S25 移植 `FIGHT_STYLE.ERB@SET_FSTYLE_INFO`（RESULTS:0〜2）等時，寫入 `GameState.results`（result.md 未移植表）。
- 已裁決（2026-10-02）：PALAM_HOSEI 殘值照原作、防衛力負數 D1〜D4（S21 實作）。已裁決（2026-10-01）：S20 的 DEVIATION 6 項＋斜體。
- 已裁決（2026-09-30）：拡張度初期值照原作；S13 苗床出産的 static LOSEDEF 等怪處照原作。
- 口上 catalog 待擴充：改狀態的口上（hook 化）、入れ子內 $ラベル 的 GOTO（`KOJO_AEGI.ERB` $ＭＡＸ２，199 函式）、STRDATA、未實作式中関数。
- deviations.md 需裁決：振り解く `LOCAL:O`、口上的狀態副作用、口上 catalog 實行時失敗的回復、S08 以後新增項。

## 仍會停止的分岐（`NotImplementedError` → Web 停止）

S23 模擬（含 [反撃] 人工設定）皆無停止。登記但罕見：
- 悪堕ち：悪堕ち戰中 TENTACLE_ACCESS 的數值鍵（安全網）。
- 襲撃／救援：ラスボス出現後（FLAG:100 = 0）の襲来、RAID_HANTEI のデバッグ入力、原作でも CodeEE になるエラー路。
- 幽閉：ラスボス 的幽閉、TS 性別變化、ラスボス出現後的淫紋陥落。
- 妊娠・子供：TS 変身キャラ妊娠時的女體化、子供名字等的手入力（INPUTS）與ランダム命名畫面、デバッグモード的妊娠確率輸入。
- TURNEND：ENDING_1 的エンドレス分岐。拉致監禁的救出（CFLAG:71）只能經情報収集（未移植）。
- 夜這い：TS キャラ的 `_ABLUP` 女体受容取得、`%CALLNAME:ARG%` 指向不存在角色（原作也報錯）。
- 指令：戰鬥基礎 Lv5 的變身能力獲得（SENGIUP；反撃成功也會經由此處）。
- ステータス PALAM 表示（FLAG:801 bit 5）、觸手服（ACTTENTACLESUIT・運動快感）、雜魚／クズ市民／ラスボス／事件戰／エンドレス、
  ボスの返り血（SUPART_BLOOD）、デバッグ模式、`HATUJOU_TO_HAIRAN` 地の文。

## 已知問題

- 未決：`docs/wiki/bridge/unresolved.md`；偏離：`docs/wiki/bridge/deviations.md`（整體「暫時維持」，S06 以後新增項待裁決）。
- 無 BOM 的 7 個角色 CSV 在原版 1.824 會以 Shift-JIS 讀（亂碼）；本程式以 UTF-8 讀，可能是 +v10 差異，待實機確認。
- 開局：預設（NORMAL＋汎用キャラ 3 名おまかせ）與初期セット「特装戦隊」；其他初期セット／キャラメイク畫面的手動設定未移植。
- 可玩範圍：休憩・鍛錬・出撃（含拘束戰鬥、拡張度、敗北後幽閉與救出、戰後レイプ、襲撃／救援イベント戰）、夜間いちゃラブ・自慰、
  妊娠・出産・子供、全滅後的ゲームオーバーモード。其他行動、11 日目夜的日數超過結局等會進入 Web「停止」畫面。
- 初期セット選項的角色身體資料為 0（原作同樣不生成），戰鬥中女性敏捷 0・攻擊 2 倍（原作行為，是否偏離待決定）。
- COUNT 仍未與 Python 共用（catalog 專用暫存，deviations「口上 catalog 的顯示簡化」）；RESULT／RESULTS 已共用。
