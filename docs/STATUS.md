# 現況（唯一真相，≤150 行）

更新：2026-09-30（S11）

## 已完成

- 建立 repo，`source/earGVP/` 原作基線入庫（唯讀）；`reference/emuera-1824/` 引擎原始碼（查證用）。
- **S01** 原作分析 wiki（`docs/wiki/era/`）＋骨架、CSV 載入器。**S02** 狀態模型（`docs/wiki/python/state.md`）、JSON 存讀檔、文字輸出層。
- **S03** 引擎規格查證、新遊戲、SHOP Web（`python -m eragvt`）、存讀檔（0–19＋自動 99）。**S04** 行動（休憩・鍛錬・出撃）與
  TURNEND／EVENTSHOP（`docs/wiki/era/actions.md`）。**S05** 戰鬥核心（`eragvt.game.battle`）。**S06** 拘束・性攻擊・敗北 → 幽閉。
- **S07** 口上／地の文 catalog（`eragvt.narration`，`docs/wiki/python/narration.md`；狀態變化行走 `narration/hooks.py`）。
  覆蓋率 13384 函式中可執行 12814（95.7%），`python -m eragvt --narration-report`。
- **S08** 幽閉（`docs/wiki/era/prison.md`）：PRISON_EVENT、救出、洗脳・悪堕ち、全滅／ソロ結局本文（ゲームオーバーモード未移植 → 停止）。
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

## S11 模擬（`python tools/sim.py --preset default|tokusou --seeds 0-249`）

方針：每次 SHOP 全員隨機預約 101–103（出撃・鍛錬・休憩）→ [100]，其他畫面從最近的按鈕隨機選（catalog）。
S10 的腳本未留存，「S10」欄是以同一 `tools/sim.py` 在 S10 HEAD 重跑的結果（S10 STATUS 記載的 4.58／17 是舊腳本，不可直接比）。

| 指標 | 預設 S10 | 預設 S11 | 初期セット S10 = S11 |
|---|---:|---:|---:|
| 停止前 SHOP 次數（平均／最多） | 6.47／19 | 11.44／32 | 10.91／32 |
| 敗北局／敗北後 SHOP 平均 | 0／— | 201／4.10 | 190／3.89 |

- 停止原因（預設 S10）：拡張度 153、いちゃラブ 92、強制自慰 3、動画サイト表示 2。
- 停止原因（預設 S11）：ゲームオーバーモード 88、受精成立 64、動画流出 33、戰後レイプ 14、強制自慰 14、ＳＰ変身 9、
  動画サイト表示（SPCOM7 輸入 1）9、COM17 回避補正 8、COM17 5、ＳＰバースト 5、ＳＰフルバースト 1。
- 停止原因（初期セット，S10 與 S11 完全相同＝CFLAG:34 = 0 路徑不變）：ゲームオーバーモード 90、受精成立 51、動画流出 35、
  ＳＰ変身 24、ＳＰバースト 14、強制自慰 13、COM17 回避補正 10、戰後レイプ 9、COM17 4。
- 預設開局的いちゃラブ：ABL 全 0 時發生機率 0（欲望×5 等），此方針下幾乎不發生；S10 的停止是在機率判定之前。

## 下一步

- 未指定 S12。依 S11 模擬頻度：ゲームオーバーモード（全滅後）、妊娠（受精成立以降）、動画流出、戰後レイプ・強制自慰、
  ＳＰ変身／バースト、悪堕ちキャラ。
- 需使用者決定：拡張度初期值（CFLAG:35／36）只在顯示時設定、既定遊玩從 0 開始（deviations.md「原作行為」S11）；
  初期セット角色是否偏離原作生成身體資料（同「原作行為」S09 項）。
- 口上 catalog 待擴充：改狀態的口上（hook 化）、GOTO、SPLIT／STRDATA、未實作式中関数（覆蓋率報告）。
- deviations.md 需裁決：振り解く `LOCAL:O`、口上的狀態副作用、口上 catalog 實行時失敗的回復、S08 以後新增項。

## 仍會停止的分岐（`NotImplementedError` → Web 停止）

頻度見上方 S11 模擬。其餘登記但罕見：
- 幽閉：ラスボス／悪堕ちキャラ 的幽閉、容貌變化（設定 ON）、RECOVER_CORRUPTION、RESCUE_CHILD、TS 性別變化、ラスボス出現後的淫紋陥落。
- TURNEND：AKUOTI_ATTACK（悪堕ち後）、寄生触手的暴走／共生取得、BIRTH_HANTEI／GROW_HANTEI、INTIMIDATION／KIDNAPPING。
- 指令：47 説得する、反擊（[反撃]スタイル、`HANGEKI_TO_TENTACLE`）；戰後妊娠判明（NINSIN_CHECK_AFTER）、戰後自慰。
- 動画サイト視窗（SPCOM7）、ステータス PALAM 表示（FLAG:801 bit 5）、素股焦らし失敗的處女喪失、觸手服／觸手拘束具、
  悪堕ち／雜魚／クズ市民／ラスボス／事件戰／エンドレス、デバッグ模式、`HATUJOU_TO_HAIRAN` 地の文。

## 已知問題

- 未決：`docs/wiki/bridge/unresolved.md`；偏離：`docs/wiki/bridge/deviations.md`（整體「暫時維持」，S06 以後新增項待裁決）。
- 無 BOM 的 7 個角色 CSV 在原版 1.824 會以 Shift-JIS 讀（亂碼）；本程式以 UTF-8 讀，可能是 +v10 差異，待實機確認。
- 開局：預設（NORMAL＋汎用キャラ 3 名おまかせ）與初期セット「特装戦隊」；其他初期セット／キャラメイク畫面的手動設定未移植。
- 可玩範圍：休憩・鍛錬・出撃（含被拘束的戰鬥、拡張度、敗北後的幽閉與救出）、夜間いちゃラブ。其他行動、11 日目夜的日數超過結局、
  妊娠等狀態會進入 Web「停止」畫面（deviations、上一節）。
- 初期セット選項的角色身體資料為 0（原作同樣不生成），戰鬥中女性敏捷 0・攻擊 2 倍（原作行為，是否偏離待決定）。
  預設開局的汎用キャラ會生成（體重正常）。角色製作／狀態畫面的手動生成未移植。
- 襲撃／救援（DAY ≥ 3）與子触手襲来成立時只顯示「スキップ」訊息（deviations）。
