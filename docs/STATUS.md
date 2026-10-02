# 現況（唯一真相，≤120 行）

更新：2026-10-02（S22）

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
- **S22** 共用 RESULTS（下節）。測試共 1344 個（新增 `tests/test_results_shared.py` 16）。

## S22 內容

- **引擎查證**（`docs/wiki/python/result.md`）：RESULTS 大小 100、**不存檔**（存檔版本維持 2）、新遊戲・讀檔時清空、BEGIN TRAIN 不清；
  RETURN／RETURNFORM 只收整數（無字串多值 RETURN）、#FUNCTION(S) 不可 CALL；寫 RESULTS 的內建：命令用式中関数・INPUTS 系・GETTIME
  （RESULTS:0）、無代入先的 STRDATA／HTML_TAGSPLIT、CHKDATA 系、FIND_CHARADATA（本作皆不用）、ARRAYCOPY。
- `GameState.results`（compare=False）。catalog 的 RESULTS（讀寫・VARSET・INPUTS・命令用式中関数）改用共用陣列，失敗回復時一併還原。
- 寫入來源（全域 grep：RESULTS:1 以後 66 行、VARSET 7＋口上 1、ARRAYCOPY 2）：STRMATCH（NANORI_FINAL）、TagSetText（WINDOW_*）、
  PRINT_TATTOO（佔位時也照 :245 VARSET＋TATTOO_LIB 寫）、TATTOO_ACCESS "POSITION_STR" 同步；未移植者列於 result.md（FIGHT_STYLE 等）。
- **名乗り改竄**：`CORRUPTTION_GET_NANORI_FINAL`:786–791 讀共用 RESULTS:2（使用者裁決照原作），停止點解除，unresolved 結案。
- RESULT:0「呼叫前值」再確認：不發 TRYCALLFORM 後的讀取，新增同步 `BATTLE_COM_AFTER.ERB`:1159（悪堕ちキャラ戦的素股焦らし次ターン指定，
  讀 HATUJOU_TO_HAIRAN 的 RETURN 0；原本是 NotImplementedError）。RESULTS:0 無讀呼叫前值處 → 維持不模型化（理由見 result.md）。

## S22 模擬（seed 0–249，`--max-shop 200`，4 並列分批）

4 設定（預設・初期セット・`--enable-akuoti`・`--corrupt 3`）的全部指標與 S21 完全相同（停止 0、全 250 局上限到達；
敗北後 SHOP 192.87／193.00／192.87／189.40，ゲームオーバーモード後 188.10／188.65／188.16／184.11）。名乗り改竄不成立路徑需 F(4) ON，模擬未到達。

## 下一步

- **自主推進（使用者指定 2026-10-02，依序）**：~~S22 RESULTS 共用~~ → **S23 [反撃]スタイル** → S24 設定畫面／プリセット → S25 狀態畫面
  → S26 FLASHNEWS → S27 ラスボス → S28 未移植行動（特別活動・防衛・支援・情報・自由）。其他候選：ランダム命名畫面、SHOP [112] 衣裝設定。
- 已裁決（2026-10-02）：名乗り改竄的 RESULTS:2 殘值照原作（S22 實作）；開局デフォルト悪堕ち的輸出丟棄維持現況。
- S23〜S25 移植 `FIGHT_STYLE.ERB@SET_FSTYLE_INFO`（RESULTS:0〜2）等時，寫入 `GameState.results`（result.md 未移植表）。
- 已裁決（2026-10-02）：PALAM_HOSEI 殘值照原作、防衛力負數 D1〜D4（S21 實作）。已裁決（2026-10-01）：S20 的 DEVIATION 6 項＋斜體。
- 已裁決（2026-09-30）：拡張度初期值照原作；S13 苗床出産的 static LOSEDEF 等怪處照原作。
- 口上 catalog 待擴充：改狀態的口上（hook 化）、入れ子內 $ラベル 的 GOTO（`KOJO_AEGI.ERB` $ＭＡＸ２，199 函式）、STRDATA、未實作式中関数。
- deviations.md 需裁決：振り解く `LOCAL:O`、口上的狀態副作用、口上 catalog 實行時失敗的回復、S08 以後新增項。

## 仍會停止的分岐（`NotImplementedError` → Web 停止）

S22 模擬 4 設定皆無停止。登記但罕見：
- 悪堕ち：悪堕ち戰中 TENTACLE_ACCESS 的數值鍵（安全網）。
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
- COUNT 仍未與 Python 共用（catalog 專用暫存，deviations「口上 catalog 的顯示簡化」）；RESULT／RESULTS 已共用。
