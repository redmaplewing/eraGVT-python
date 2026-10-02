# 現況（唯一真相，≤120 行）

更新：2026-10-02（S25）

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
- **S23** [反撃]スタイル（`battle/hangeki.py`，`--style 反撃` 人工模擬）。
- **S24** 設定畫面／開局プリセット／GLOBAL（`eragvt.game.config`，`docs/wiki/era/flow.md` §10）。
- **S25** ステータス畫面（下節）。

## S25 內容（`eragvt.game.status_screen`／`status_talent`／`colorbar`／`export_csv`）

- `SHOW_STATUS_CHARA_SELECT` 5 頁全移植（戰鬥／素質・性成長／武器／相関／プロフィール），入口：SHOP [110]、戰鬥 [800]、
  HEROINE_PRESET [20]〜[29]（全域 grep 只有這 3 處）。翻頁 [1]/[2]/[1000]〜[5000]、[100]/[200] 換人（戰鬥中不可）、[999] 返回。
- 固有指令：P1 [0] 口上設定循環・[10] 主観モード・[11] 呼び名（FIRSTSETTING_CHARA_CALLNAME）・[13] 変身後名等；P2 [0] EXPORT_CSV（全移植）；
  P5 [10] 通常／変身時切替・[20] 身體資料生成（GENERATE_BODYLINE→AGE→SIZE_DEFAULT→SIZE_SETTING 以 [99] 代替）。
- PAGE5 顯示時 PRINTFORM_GAPING_NOW 設定拡張度初期值（S11 裁決）；SET_FSTYLE_INFO 寫共用 RESULTS:0〜2、GET_COLOR_BY_RANK／TOP_UNDER 寫 RESULT。
- 共用部品：COLOR_BAR／COLORSENTENCE_BAR（SHOP・鍛錬・戰鬥的近似條改為原文）、COLORCHIP、TALENT_INFO（ERB 抽取表）、
  SHOW_STATUS_TALENT（2 形式，鍛錬畫面也接上）；HTML_PRINT 新增 `<br>`／`<nobr>`／`<shape type='space'>`。
- 測試共 1469 個（新增 `tests/test_status_screen.py` 29、`test_web.py` 1）。`test_hangeki` 統合測試的方針排除 [800]、`test_parasite` 改 seed 0（經路變化）。
- `SHOP_SHOW_STATUS_RESERVE_LIST`（控えメンバー）屬 SHOP 一覽系（`SHOP_SHOW_STATUS_LIST.ERB`），不在本階段，仍印未實作。

### 模擬（seed 0–249，`--max-shop 200`，4 並列分批；戰鬥中隨機按 [800] 會進入狀態畫面）

- 預設：上限 246、停止 4（既有停止點 HATUJOU_TO_HAIRAN 地の文：經路改變後到達）；敗北後 SHOP 189.76、ゲームオーバー後 188.29。
- 初期セット：250 局全部上限；敗北後 SHOP 192.95、ゲームオーバー後 188.55。狀態畫面新增停止 0（3 局抽樣：各頁 113 次、EXPORT_CSV 2 次）。

### 狀態畫面內仍會停止

P1 [11]→[1] 呼び名手入力（INPUTS）、[12] 一人称設定畫面、[13] 各項的手入力／ランダム命名；P3 [0] 武器カスタマイズ；
P4 父親 CFLAG:9 指向不存在的ボス／ラスボス／モブ；HEROINE_PRESET [20]〜[29] 的不存在角色（原作也報錯）；色指定 R//G//B 的 16 進・指數表記。

### 設定項打開後會碰到未移植系統（S24，`flow.md` §10；預設 config 1 全 OFF）

[34] 雑魚戦（802 bit4）→ MOB_TENTACLE_BATTLE 停止；[78] 裏プロフィール（805 bit6）→ MAKESEXUALPROFILE 停止；[11]／[15]〜[17] 調教ステータス表示
（801 bit1／5〜7）→ 戰鬥中停止；[54] 返り血（803 bit4）→ SUPART_BLOOD 停止；[72] 触手の子種からも娘 → 命名 INPUTS 停止；
[35] クズ市民・[55] ラスボス強化・[79] 有害ブログ 無作用（所在系統未移植）。[10]／[14] 素質表示 S25 起生效。
`--config-preset 2／3` 模擬（S24）：250 局全部停止於雑魚戦。

## 下一步

- **自主推進（使用者指定 2026-10-02，依序）**：~~S22 RESULTS 共用~~ → ~~S23 [反撃]スタイル~~ → ~~S24 設定畫面／プリセット~~ → ~~S25 狀態畫面~~
  → **S26 FLASHNEWS** → S27 ラスボス → S28 未移植行動（特別活動・防衛・支援・情報・自由）。其他候選：ランダム命名畫面、SHOP [112] 衣裝設定。
- 已裁決（2026-10-02）：名乗り改竄的 RESULTS:2 殘值照原作（S22 實作）；開局デフォルト悪堕ち的輸出丟棄維持現況。
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
- 開局：HEROINE_PRESET 的 [30]（相関関係）、2 択畫面的 [300]（ゲームの説明）。狀態畫面內的停止見上節。設定項造成的停止見上表。
- 戰鬥 PALAM 表示（FLAG:801 bit 5）、觸手服（ACTTENTACLESUIT・運動快感）、雜魚／クズ市民／ラスボス／事件戰／エンドレス、
  ボスの返り血（SUPART_BLOOD）、デバッグ模式、`HATUJOU_TO_HAIRAN` 地の文。

## 已知問題

- 未決：`docs/wiki/bridge/unresolved.md`；偏離：`docs/wiki/bridge/deviations.md`（整體「暫時維持」，S06 以後新增項待裁決）。
- 無 BOM 的 7 個角色 CSV 在原版 1.824 會以 Shift-JIS 讀（亂碼）；本程式以 UTF-8 讀，可能是 +v10 差異，待實機確認。
- 開局：預設（NORMAL＋汎用キャラ 3 名おまかせ）與初期セット「特装戦隊」，HEROINE_PRESET 可選 0〜3；其他初期セット／キャラメイク畫面的手動設定未移植。
- 可玩範圍：休憩・鍛錬・出撃（含拘束戰鬥、拡張度、敗北後幽閉與救出、戰後レイプ、襲撃／救援イベント戰）、夜間いちゃラブ・自慰、
  妊娠・出産・子供、全滅後的ゲームオーバーモード。其他行動、11 日目夜的日數超過結局等會進入 Web「停止」畫面。
- 初期セット選項的角色身體資料為 0（原作同樣不生成），戰鬥中女性敏捷 0・攻擊 2 倍（原作行為，是否偏離待決定）。
- COUNT 仍未與 Python 共用（catalog 專用暫存，deviations「口上 catalog 的顯示簡化」）；RESULT／RESULTS 已共用。
