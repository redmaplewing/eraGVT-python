# 未決問題

格式：`- [ ] 問題（來源：檔案@函式）— 目前的推測／需要誰決定`

## Emuera 規格（需對照 Emuera 原始碼或實機）

- [x] DOTRAIN 內部順序 — **已由引擎原始碼確認**（`reference/emuera-1824/Emuera/GameProc/Process.SystemProc.cs`:430–485）：`@EVENTCOM` → `@COMn` → 若 `RESULT != 0` 才 `@SOURCE_CHECK` → SOURCE 清空（`UpdateAfterSourceCheck`）→ `@EVENTCOMEND`。**`@COMn` 回傳 RESULT 0 時跳過 SOURCE_CHECK 與 EVENTCOMEND**（原推測未涵蓋）。BEGIN TRAIN 時 TFLAG/TSTR 全清零（`VariableEvaluator.cs@UpdateInBeginTrain`:1422）。
- [ ] SHOP 階段 `@EVENTSHOP` 呼叫時機、TURNEND 無 BEGIN 時的去向 — 查 `Process.SystemProc.cs@beginTurnend`/`beginShop`（:602–640）。
- [ ] 角色 CSV 省略值時（`素質,0,;処女`）預設為 1；非素質欄位省略值是否也是 1（來源：`src/eragvt/data/csv_loader.py@_apply_chara_row`）— 目前一律當 1；原作只有素質省略值。
- [ ] `CSV/Chara/Chara299.CSV`:17–19 `フラグ,40,100.`（尾端句點）Emuera 怎麼讀 — 目前當 100。
- [ ] `CSV/Chara/Chara998_AA表示.CSV` 的 `基礎,40,xx`、`素質,200,変身能力` Emuera 是略過、當 0、還是報錯 — 目前略過並記警告；998 是範本／AA 顯示用，應不影響遊戲。
- [ ] `_Replace.csv` `BAR文字1, `（值是一個半形空白）是否被 Emuera trim 成空字串 — 影響狀態列的長條顯示，Web 版可自訂，優先度低。

- [x] Emuera 新遊戲時的初始角色列表 — **已確認**（`Process.SystemProc.cs@endOpenning`:197–209）：`ResetData` → 加入 CSV 番號 0（本作 `Chara000汎用キャラ(女性)`）→ 若 `GameBase.csv`「最初からいるキャラ」>0 再加入（本作 999）→ 呼叫 `@EVENTFIRST`。原作再 `SWAPCHARA 0,1`／`DELCHARA 1` 後只剩 999，與 S02 `GameState.new` 結果一致。TARGET／ASSI 初始值仍待查 `ResetData`。
- [ ] Emuera 存檔實際包含哪些內建變數 — S02 以推測決定（含 TFLAG），**屬未查證**。待查 `VariableCode.cs` 存檔旗標與 `VariableData.cs` 存檔實作後照原作修正（`VariableCode.cs`:38 TFLAG 無存檔旗標，初步看**不存**）。
- [ ] Emuera 自動按鈕（`[n]` 文字）的精確範圍規則（來源：`src/eragvt/text/output.py@split_buttons`）— 目前「到下一個 `[n]` 或字串尾」；Web 版以可用為準，不必完全重現。

## 原作邏輯

- [x] `TFLAG:0`（戰鬥回合數）遞增處 — **已找到**：`ゲーム内_戦闘処理/BATTLE_COM_AFTER.ERB@SOURCE_CHECK`:1313–1318，先制攻擊中（`TFLAG:24 > 0`）扣 `TFLAG:24`，否則 `TFLAG:0 += 1`；戰鬥開始前由各イベント戦闘共通檔設 `-1`（例 `●イベント戦闘_襲撃共通.ERB`:127）。之前「ERB 內沒有遞增」的結論是錯的：grep 結果被 `WAITFLAG:0` 擠滿後用 `head` 截斷而漏看。
- [ ] 一覧:594 說回合上限在 `TCVARn:13`，程式實際用 `ERB/DIM.ERH`:280 `ターン上限` — 以程式為準。
- [ ] 雜魚／クズ市民戰在體力・氣力・性耐性全 0 時的結束路徑（`BATTLE_COM_AFTER.ERB@SOURCE_CHECK`:955 排除 MOB/CITIZEN）— S05 調查。
- [ ] 角色 CSV `相性,對方番号,值` 如何轉成以 `CFLAG:240`（固有番號）為索引的 RELATION（來源：`●GVTフラグ一覧.txt`:741）— 轉換處未調查，S03 開局時需要。
- [ ] `DIM.ERH`:20 `GFLAG`（「全領域参照用」）用途未調查。
