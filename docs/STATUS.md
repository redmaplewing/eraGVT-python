# 現況（唯一真相，≤120 行）

更新：2026-10-04（S44引退名簿／主動引退驗收完成）

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
- **S25** ステータス畫面（`eragvt.game.status_screen`／`status_talent`／`colorbar`／`export_csv`；5 頁＋頁內指令，入口 SHOP [110]・戰鬥 [800]・HEROINE_PRESET [20]〜；控えメンバー一覧 SHOP_SHOW_STATUS_RESERVE_LIST は未實作表示）。
- **S26** FLASHNEWS（`eragvt.game.flashnews`，SHOP_FLASHNEWS.ERB 全體）。**S26b** 事件戰ニュースの前回 RESULTS:0 を照原作、3003／3004 MISSION_CHECKER の括弧修正。
- **S27** ラスボス（Ｋ触手）＋結局（`docs/wiki/era/lastboss.md`；模擬：預設 249 上限＋1 HATUJOU、敗北後 192.92）。
- **S28a** 拠点防衛・戦闘支援・情報収集・スケジュール（SHOP [160]）・戦闘基礎 Lv5 變身能力・拉致監禁表示・ACTION_MAIN 終端（下節）。

- **S28b** 特別活動（`eragvt.game.seisan`：ACTION_SEISAN＋特別活動/ 全部、地の文 catalog；下節）。
- **S28c1** 自由行動（`eragvt.game.pastime`／`pastime_school`：ACTION_PASTIME＋一般自由行動事件 12 檔；下節）。
- **S28c2** 自由行動の本編ナンパ・酒ナンパ・痴漢（`eragvt.game.pastime_nanpa`：catalog の `run_event_gen` で原文 11 関数を実行；下節）。
- **S29** 口上／地の文的狀態書き込み（catalog が非 LOCAL 代入を GameState へ直接書く＋ジャーナルで失敗回復；下節）。
- **S30** catalog 剩餘的不可執行原因（ループ內 $ラベルへの GOTO・STRDATA・SETCOLORBYNAME・FINDCHARA・GETCOLOR・RANDCHOOSE 系；下節）。

## S44：SHOP引退名簿／主動引退

- S32–S43完成既有擴充，含SHOP衣裝／強化／醫療室／追加招募；醫療室未完成支線仍依裁決提示並截斷。
- S44接通SHOP [169]名簿／[170]主動引退；加入引退選項開啟，170另要求至少一名非MASTER角色。
- 依原作角色資格、999取消與雙重確認；INPUT_ROOP上界包含2，輸入2保留原作不執行行為。
- 手翻引退報告與分類計數，SAVESTR:50保存HTML原字串；DELCHARA壓縮列表、TARGET=0，其餘索引不自行修正。
- 名簿／報告PRINTW局部等待Enter，避免返回SHOP的LB遮掉內容；等待不寫RESULT／RESULTS，最後報告確認後才刪除角色。
- 定向102項：`102 passed, 1 warning in 7.51s`；含GameSession.screen與Web空白Enter實測，警告是既有Starlette/httpx。
- 主代理獨立完整pytest：`2875 passed, 1 warning in 369.55s (0:06:09)`。
- 標準500局：default246上限／4回標題、tokusou250上限，catalog失敗0；逐seed完整結果與S43一致。
- 10個50局獨立前景批次exit=0，seed全集與log／JSONL一致；模擬與audit留在`tmp/s44/`。
- 無新增UNVERIFIED／規則偏離；既有WAIT簡化在此局部補完。詳見`docs/wiki/era/retirement.md`。

## 口上 catalog 現況

- **S31** TURNEND／SHOP 口上 INPUT 依原作等待選擇並續行，巢狀呼叫共用輸入通道；回標題時關閉舊流程。
- S31 的 500 局 catalog 執行失敗皆為 0；實際設定：病嬌預設 34 局，豹變預設 1 局／初期セット 2 局。
- 口上／地の文函式可執行 13,384／13,384；另有194個雜魚專用顯示函式、10個市民檔顯示函式（含先載入的同名COM2）。
- S29 狀態寫入／回復、S30 指令補完、S31 選單等待、S32 文字片段詳見 `docs/wiki/python/narration.md`。

### 狀態畫面內仍會停止

P1 [12] 一人称設定畫面；P3 [0] 武器カスタマイズ；
P4 父親 CFLAG:9 指向不存在的ボス／ラスボス／モブ；HEROINE_PRESET [20]〜[29] 的不存在角色（原作也報錯）；色指定 R//G//B 的 16 進・指數表記。

### 設定項打開後會碰到未移植系統（S24，`flow.md` §10；預設 config 1 全 OFF）

[34] 雑魚戦（802 bit4）S33接通；[78] 裏プロフィール（805 bit6）與[11]／[15]〜[17]狀態顯示（801 bit1／5〜7）S34接通。
[54] 返り血（803 bit4）→ SUPART_BLOOD 停止；[72] 触手の子種からも娘的命名S35已接通；
[35] クズ市民→S36已接通；[55] ラスボス強化 所在系統未移植。[10]／[14] 素質表示 S25 起、[79] 有害ブログ S26 起生效。
`--config-preset 2／3` 正常設定已於S36驗收（原市民戰停止消除）。

## 下一步

- **自主推進（使用者指定 2026-10-02，依序）**：~~S22 RESULTS 共用~~ → ~~S23 [反撃]スタイル~~ → ~~S24 設定畫面／プリセット~~ → ~~S25 狀態畫面~~
  → ~~S26 FLASHNEWS~~ → ~~S26b RESULTS:0 殘值~~ → ~~S27 ラスボス～結局~~ → ~~S28 未移植行動（S28a〜S28c2）~~：**指定範圍全部完成**。
  使用者授權S44引退名簿／主動引退，完成本階段後停止；下一階段待使用者選定。
- 已裁決（2026-10-02）：名乗り改竄的 RESULTS:2 殘值照原作（S22 實作）；開局デフォルト悪堕ち的輸出丟棄維持現況。
- 已裁決（2026-10-02）：PALAM_HOSEI 殘值照原作、防衛力負數 D1〜D4（S21 實作）。已裁決（2026-10-01）：S20 的 DEVIATION 6 項＋斜體。
- 已裁決（2026-09-30）：拡張度初期值照原作；S13 苗床出産的 static LOSEDEF 等怪處照原作。
- 口上 catalog：TURNEND／SHOP 的動態 INPUT 已裁決並接通（S31）；GETBGCOLOR（背景色狀態）已於 S33 接通。
- deviations.md 需裁決：口上 catalog 實行時失敗的回復（S29 改寫：狀態也回復）、S08 以後新增項、S28c1 的 1 項（Null 時停止；夜間排程已裁決＝隨機）、S28c2 的 1 項（Null 時停止）。

## 仍會停止的分岐（`NotImplementedError` → Web 停止）

S23 模擬（含 [反撃] 人工設定）皆無停止。登記但罕見：
- 悪堕ち：悪堕ち戰中 TENTACLE_ACCESS 的數值鍵（安全網）。
- 襲撃／救援：生存ラスボス 0 での襲来（原作無限ループ）、RAID_HANTEI のデバッグ入力、原作でも CodeEE になるエラー路。
- ラスボス・結局：ENDING 後の JUMP SHOW_SHOP（原作もエラー）。
- 醫療室SHOP [113]隱藏[51]確認1：AMPUTEE原作移植未完成，依裁決提示並截斷，不執行支線。
- 幽閉：TS 性別變化。
- 妊娠・子供：TS 変身キャラ妊娠時的女體化、デバッグモード的妊娠確率輸入。
- 情報収集（S28a）：デバッグ入力。
- ACTION_MAIN 由 EVENTTURNEND 經 JUMP 而終端（雜魚戰候選全部禁用：原作也錯誤）。
- 夜這い：TS キャラ的 `_ABLUP` 女体受容取得、`%CALLNAME:ARG%` 指向不存在角色（原作也報錯）。
- 開局：HEROINE_PRESET 的 [30]（相関関係）、2 択畫面的 [300]（ゲームの説明）。狀態畫面內的停止見上節。設定項造成的停止見上表。
- 觸手服（ACTTENTACLESUIT・運動快感）、市民觀眾妨礙（ACT_LIMIT）／部分事件戰／エンドレス、
  ボスの返り血（SUPART_BLOOD）、デバッグ模式。

## 已知問題

- 未決：`docs/wiki/bridge/unresolved.md`；偏離：`docs/wiki/bridge/deviations.md`（整體「暫時維持」，S06 以後新增項待裁決）。
- 無 BOM 的 7 個角色 CSV 在原版 1.824 會以 Shift-JIS 讀（亂碼）；本程式以 UTF-8 讀，可能是 +v10 差異，待實機確認。
- 開局：預設（NORMAL＋汎用キャラ 3 名おまかせ）與初期セット「特装戦隊」，HEROINE_PRESET 可選 0〜3；其他初期セット／キャラメイク畫面的手動設定未移植。
- 可玩範圍：休憩・鍛錬（含スケジュール）・出撃・拠点防衛・戦闘支援・情報収集・特別活動・自由行動（含ナンパ等本編；含拘束戰鬥、拡張度、敗北後幽閉與救出、戰後レイプ、襲撃／救援イベント戰）、夜間いちゃラブ・自慰、
  妊娠・出産・子供、全滅後的ゲームオーバーモード、ラスボス戰～ENDING_2～引き継ぎ續行、日數超過 ENDING_3（回標題）。
- 初期セット選項的角色身體資料為 0（原作同樣不生成），戰鬥中女性敏捷 0・攻擊 2 倍（原作行為，是否偏離待決定）。
- COUNT 仍未與 Python 共用（catalog 專用暫存，deviations「口上 catalog 的顯示簡化」）；RESULT／RESULTS 已共用。
