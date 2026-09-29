# 未決問題

格式：`- [ ] 問題（來源：檔案@函式）— 目前的推測／需要誰決定`

## Emuera 規格（需對照 Emuera 原始碼或實機）

- [ ] DOTRAIN 內部順序 `@EVENTCOM → @COMn → @SOURCE_CHECK → @EVENTCOMEND`、SHOP 階段 `@EVENTSHOP` 只在進入時呼叫一次、TURNEND 無 BEGIN 時自動進 SHOP（來源：`docs/wiki/era/flow.md` §0）— 依 eramaker 慣例推定，S05 前確認。
- [ ] 角色 CSV 省略值時（`素質,0,;処女`）預設為 1；非素質欄位省略值是否也是 1（來源：`src/eragvt/data/csv_loader.py@_apply_chara_row`）— 目前一律當 1；原作只有素質省略值。
- [ ] `CSV/Chara/Chara299.CSV`:17–19 `フラグ,40,100.`（尾端句點）Emuera 怎麼讀 — 目前當 100。
- [ ] `CSV/Chara/Chara998_AA表示.CSV` 的 `基礎,40,xx`、`素質,200,変身能力` Emuera 是略過、當 0、還是報錯 — 目前略過並記警告；998 是範本／AA 顯示用，應不影響遊戲。
- [ ] `_Replace.csv` `BAR文字1, `（值是一個半形空白）是否被 Emuera trim 成空字串 — 影響狀態列的長條顯示，Web 版可自訂，優先度低。

- [ ] Emuera 新遊戲時的初始角色列表與 TARGET／ASSI 預設值（推測：chara 0 為 MASTER，再加「最初からいるキャラ」999；原作 `SWAPCHARA 0,1`／`DELCHARA 1` 後只剩 999）（來源：`ゲーム内_イベント発生/オープニング処理.ERB@EVENTFIRST`:63–64）— `GameState.new` 直接建成「只有 999」，TARGET=0、ASSI=-1。
- [ ] Emuera 存檔實際包含哪些內建變數（TFLAG 是否存、PALAMLV 等）（來源：`src/eragvt/state/game_state.py@GameState`）— 目前存 DAY/TIME/MONEY/TARGET/ASSI/FLAG/TFLAG/ITEM/SAVESTR + 角色全部變數；本作無法在戰鬥中存檔，多存 TFLAG 無害。
- [ ] Emuera 自動按鈕（`[n]` 文字）的精確範圍規則（來源：`src/eragvt/text/output.py@split_buttons`）— 目前「到下一個 `[n]` 或字串尾」；Web 版以可用為準，不必完全重現。

## 原作邏輯

- [ ] `TFLAG:0`（戰鬥回合數，一覧:459）在全部 ERB 找不到遞增處（grep `TFLAG:0`／`TFLAG ++` 皆無），但時間切れ判定用它（`ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK`:1113）— 推測是 Emuera 或舊版 eramaker 的內建行為，或某處用了間接寫法；S05 必須解。
  - 2026-09-29 本機追加調查：別名 `TFLAG:TFターン`（`REPORT.ERH`:15 `#DIM CONST TFターン = 0`）只有讀取；無索引 `TFLAG ++` 也沒有。全部寫入只有 `VARSET TFLAG`（3 個イベント戦闘共通檔）與 `BATTLE_COM_AFTER.ERB`:1107 `TFLAG:0 -= 1`（註解「このターンは時間経過させない」）。一覧:459 另說「戰鬥開始直前為 -1」。結論：ERB 內確定沒有遞增，遞增發生在引擎側或已失傳；S05 應直接做 bridge 決策（例：每完成一輪指令後 +1），記在 `docs/wiki/bridge/` 並以該決策寫測試，不必再全域 grep。
- [ ] 一覧:594 說回合上限在 `TCVARn:13`，程式實際用 `ERB/DIM.ERH`:280 `ターン上限` — 以程式為準。
- [ ] 雜魚／クズ市民戰在體力・氣力・性耐性全 0 時的結束路徑（`BATTLE_COM_AFTER.ERB@SOURCE_CHECK`:955 排除 MOB/CITIZEN）— S05 調查。
- [ ] 角色 CSV `相性,對方番号,值` 如何轉成以 `CFLAG:240`（固有番號）為索引的 RELATION（來源：`●GVTフラグ一覧.txt`:741）— 轉換處未調查，S03 開局時需要。
- [ ] `DIM.ERH`:20 `GFLAG`（「全領域参照用」）用途未調查。
