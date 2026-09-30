# 現況（唯一真相，≤150 行）

更新：2026-09-30（S12）

## 已完成

- 建立 repo，`source/earGVP/` 原作基線入庫（唯讀）；`reference/emuera-1824/` 引擎原始碼（查證用）。
- **S01** 原作分析 wiki（`docs/wiki/era/`）＋骨架、CSV 載入器。**S02** 狀態模型（`docs/wiki/python/state.md`）、JSON 存讀檔、文字輸出層。
- **S03** 引擎規格查證、新遊戲、SHOP Web（`python -m eragvt`）、存讀檔（0–19＋自動 99）。**S04** 行動（休憩・鍛錬・出撃）與
  TURNEND／EVENTSHOP（`docs/wiki/era/actions.md`）。**S05** 戰鬥核心（`eragvt.game.battle`）。**S06** 拘束・性攻擊・敗北 → 幽閉。
- **S07** 口上／地の文 catalog（`eragvt.narration`，`docs/wiki/python/narration.md`；狀態變化行走 `narration/hooks.py`）。
  覆蓋率 13384 函式中可執行 12814（95.7%），`python -m eragvt --narration-report`。
- **S08** 幽閉（`docs/wiki/era/prison.md`）：PRISON_EVENT、救出、洗脳・悪堕ち、全滅／ソロ結局本文（S12 起接ゲームオーバーモード）。
- **S09** 身體資料（`eragvt.game.body`，`docs/wiki/era/body-profile.md`）：初期セット角色原作也不生成（NO ≠ 0）→ 敏捷 0・攻擊 2 倍是原作行為。
- **S10** 開局改回原作預設路徑（`eragvt.game.chara_make`，`docs/wiki/era/flow.md` §1）：標題 `[0]` 後 2 択「[0] おまかせ（汎用キャラ 3 名）／
  [1] 初期セット『特装戦隊』」。`event_first(state, data, preset=None)` 為預設；既有測試明確指定 `preset=PRESET_TOKUSOU`。
- **S11** 拡張度與いちゃラブセックス（設計與照原作的怪處：`docs/wiki/era/gaping.md`）。
  - `battle.gaping`：V_GAPING／A_GAPING／GET_V・A_GAPING_EXP（CFLAG:34 ≠ 0）、GAPING_RANK_STR、PRINT_TENTACLE_SIZE、PRINTFORM_GAPING_NOW；
    `PALAM_CALC_GAPING`・`PRISON_GAPING` 的停止點解除（PRISON_GAPING 的 GET_*_EXP 改為 OPTION 1，照原作）。
    `TextOutput.html_print`（HTML_PRINT；`<nonbutton title>` → Web tooltip）。
  - 新模組 `eragvt.game.lovesex`：LOVESEX_NIGHT／LOVESEX_KIND／SEX_V／SEX_A／SEX_V_CONDOM（INPUT）；`ninsin.after_pill`（INPUT）、
    NINSIN_HANTEI 的一般人父親分岐（`愛する人 = -3`）。`turnend.event_turnend` 改為 generator。地の文 4 函式走 catalog，
    `MESSAGE_KATAOMOI_NIGHT` 的 TALENT 代入 2 行進 `hooks.LOVESEX_HOOK_LINES`。
  - `MESSAGE_SEX_SPCOM7` 的 INPUTS（CFLAG:34 > 0）接上（generator），輸入 "1" 的動画サイト視窗未移植 → 停止。
  - 模擬腳本 `tools/sim.py`（之後各階段共用）。測試共 646 個（新增 `tests/test_gaping.py` 52、`tests/test_lovesex.py` 34）。

- **S12** ゲームオーバーモード（`docs/wiki/era/flow.md` §9）：`shop.change_gameover_mode`（FLAG:0 = 0、DAY:2 = DAY*2+TIME）、
  ENDING_1／4／5 不再停止（FLAG:999 = -998 → FORCEWAIT → 回到 EVENTEND／PRISON，下一次 PRISON 歸 0）。之後每回合 PRISON 對
  全員（CFLAG:0 2／3／9 也）執行，SHOP 隱藏選單。`GAME_MODE_CHECK`（FLAG:906 版，SAVEINFO 用）、USERSHOP [110]〜[160] 的原作條件、
  `AKUOTI_ATTACK` 的候補抽選（候補有才停止）。CHECK_GAMEOVER_F 的其餘分岐 S04〜S08 已移植，本階段逐一加測試。
  `tools/sim.py` 新增ゲームオーバーモード統計（並改為停止前先記錄敗北／進入）。測試共 705 個（新增 `tests/test_gameover.py` 59）。

## S12 模擬（`python tools/sim.py --preset default|tokusou --seeds 0-249`）

方針同 S11（每次 SHOP 全員隨機預約 101–103 → [100]，其他畫面隨機按鈕）。敗北局數比 S11 多是因為腳本改為停止前也記錄
（S11：停止發生在敗北那一步時不算），進入數與 S11 的「ゲームオーバーモード」停止數一致（88／90）。

| 指標 | 預設 S11 | 預設 S12 | 初期セット S11 | 初期セット S12 |
|---|---:|---:|---:|---:|
| 停止前 SHOP 次數（平均／最多） | 11.44／32 | 13.82／45 | 10.91／32 | 14.51／43 |
| ゲームオーバーモード進入局／進入後 SHOP 平均（最多） | 88（停止） | 88／6.75（22） | 90（停止） | 90／10.01（21） |

- 停止原因（預設 S12）：受精成立 137、動画流出 33、苗床出産 15、戰後レイプ 14、強制自慰 14、ＳＰ変身 9、動画サイト表示 9、
  COM17 回避補正 8、COM17 5、ＳＰバースト 5、ＳＰフルバースト 1。
- 停止原因（初期セット S12）：受精成立 122、動画流出 35、ＳＰ変身 24、苗床出産 19、ＳＰバースト 14、強制自慰 13、
  COM17 回避補正 10、戰後レイプ 9、COM17 4。
- 進入ゲームオーバーモード後的停止只有兩種：受精成立（幽閉中，預設 73／初期セット 71）、苗床出産（`BIRTH_AUTO_RANDOM`:671–，
  取り込まれ角色每回合 1/4，15／19）。非ゲームオーバー局的停止原因與 S11 相同。

## 下一步

- 候選（依 S12 模擬頻度）：**妊娠（受精成立以降＋苗床出産）**——現在最大停止原因，也是ゲームオーバーモード中唯一的停止；
  之後動画流出、戰後レイプ・強制自慰、ＳＰ変身／バースト、悪堕ちキャラ（AKUOTI_EVENT：ゲームオーバーモードで悪堕ちが居れば毎ターン）、狀態畫面、FLASHNEWS。
- 已裁決（2026-09-30）：拡張度初期值照原作不設定；初期セット身體資料問題因 S10 改回預設開局而不再需要偏離。
- 口上 catalog 待擴充：改狀態的口上（hook 化）、GOTO、SPLIT／STRDATA、未實作式中関数（覆蓋率報告）。
- deviations.md 需裁決：振り解く `LOCAL:O`、口上的狀態副作用、口上 catalog 實行時失敗的回復、S08 以後新增項。

## 仍會停止的分岐（`NotImplementedError` → Web 停止）

頻度見上方 S11 模擬。其餘登記但罕見：
- 幽閉：ラスボス／悪堕ちキャラ 的幽閉、容貌變化（設定 ON）、RECOVER_CORRUPTION、RESCUE_CHILD、TS 性別變化、ラスボス出現後的淫紋陥落。
- TURNEND：AKUOTI_EVENT（悪堕ちキャラが抽選に當選）、苗床出産（BIRTH_AUTO_RANDOM:671–）、ENDING_1 的エンドレス分岐、寄生触手的暴走／共生取得、BIRTH_HANTEI／GROW_HANTEI、INTIMIDATION／KIDNAPPING。
- 指令：47 説得する、反擊（[反撃]スタイル、`HANGEKI_TO_TENTACLE`）；戰後妊娠判明（NINSIN_CHECK_AFTER）、戰後自慰。
- 動画サイト視窗（SPCOM7）、ステータス PALAM 表示（FLAG:801 bit 5）、素股焦らし失敗的處女喪失、觸手服／觸手拘束具、
  悪堕ち／雜魚／クズ市民／ラスボス／事件戰／エンドレス、デバッグ模式、`HATUJOU_TO_HAIRAN` 地の文。

## 已知問題

- 未決：`docs/wiki/bridge/unresolved.md`；偏離：`docs/wiki/bridge/deviations.md`（整體「暫時維持」，S06 以後新增項待裁決）。
- 無 BOM 的 7 個角色 CSV 在原版 1.824 會以 Shift-JIS 讀（亂碼）；本程式以 UTF-8 讀，可能是 +v10 差異，待實機確認。
- 開局：預設（NORMAL＋汎用キャラ 3 名おまかせ）與初期セット「特装戦隊」；其他初期セット／キャラメイク畫面的手動設定未移植。
- 可玩範圍：休憩・鍛錬・出撃（含被拘束的戰鬥、拡張度、敗北後的幽閉與救出）、夜間いちゃラブ、全滅後的ゲームオーバーモード。其他行動、11 日目夜的日數超過結局、
  妊娠等狀態會進入 Web「停止」畫面（deviations、上一節）。
- 初期セット選項的角色身體資料為 0（原作同樣不生成），戰鬥中女性敏捷 0・攻擊 2 倍（原作行為，是否偏離待決定）。
  預設開局的汎用キャラ會生成（體重正常）。角色製作／狀態畫面的手動生成未移植。
- 襲撃／救援（DAY ≥ 3）與子触手襲来成立時只顯示「スキップ」訊息（deviations）。
