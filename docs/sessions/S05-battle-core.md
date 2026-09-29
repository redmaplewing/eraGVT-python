# S05 — 戰鬥核心（出撃 → 遭遇 → TRAIN → 戰後 → 回合結束）

建議模型：Opus 5.5（effort high）。開場讀 `AGENTS.md`、`docs/STATUS.md`、`docs/PLAN.md`，
需要時查 `docs/wiki/era/battle-overview.md`、`flow.md` §0／§7、`actions.md`、`docs/wiki/python/state.md`。
路徑相對 `source/earGVP/ERB/`。

## 目標

SHOP 設定「出撃」→ `[100]` 後，能實際打一場 **BOSS 觸手戰**（開局可遭遇的對象）直到勝／敗／時間切れ，
戰後處理完回到 TURNEND → SHOP，並可存讀檔。S06 再補敵方性攻擊、連擊、反擊、戰報等。

## 交付物

1. **遭遇**：`ゲーム内_行動実行処理/ACTION.ERB`:74–98 → `ゲーム内_戦闘処理/ENCOUNT.ERB@ENCOUNT`:5
   （`ENCOUNT_ENEMY`／`ENCOUNT_BOSS`）→ 無則 `@MOB_TENTACLE_ENCOUNT`:429。基本セット下雜魚戰是否會發生先查清
   （config FLAG:802 位元）；會發生而本 session 不做者 → 登記 deviation 並以停止或跳過處理（說明理由）。
2. **TRAIN 流程**（引擎順序已在 flow.md §0 查證）：`BATTLE_TRAIN.ERB@EVENTTRAIN`（含 INITIATIVE／先制）→
   `BATTLE_SHOW_STATUS.ERB@SHOW_STATUS` → `@COM_ABLEn` → `BATTLE_COM.ERB@SHOW_USERCOM` → 輸入 →
   `@EVENTCOM` → `@COMn` → `RESULT != 0` 時 `BATTLE_COM_AFTER.ERB@SOURCE_CHECK` → `@EVENTCOMEND`。
3. **玩家指令**：至少 変身（0、201–203）、近／中／遠攻擊（1–3）、防御（4）、距離をとる（5）、ギブアップ（99）、
   撤退（USERCOM 999）完整翻寫，含命中／傷害判定（`COMMON_BATTLE_HANTEI.ERB`）與 `PALAM_CAL`／`PALAM_UP`
   中這些指令會走到的部分。其餘指令在 SHOW_USERCOM 照原作顯示，但選到時停止並登記 deviation。
4. **敵方行動**：`ENEMY_ACTION.ERB@ENEMY_ACTION` 的**非拘束**分岐與 `SELECT_TENTACLE_ACTION`（BOSS 觸手資料
   `触手データ/ボス触手/TENTACLE_BOSS_{n}_*.ERB` 需要的部分）。拘束後的性攻擊（SEX_COM／SEX_ROUTINE）屬 S06：
   本 session 若走到 → 停止並登記。
5. **結束與戰後**：SOURCE_CHECK 的勝利／敗北（敗北後的幽閉若未移植 → 停止並登記）／時間切れ（TFLAG:0 遞增：
   `BATTLE_COM_AFTER.ERB`:1313–1318）→ `BATTLE_TRAIN_AFTER.ERB@EVENTEND` → `BEGIN TURNEND`。
6. **session／Web**：`run_turn` 的 `Step.TRAIN` 接上戰鬥 generator；戰鬥輸入 phase；戰鬥中不可存檔（照引擎）。
7. **測試**：命中／傷害／PALAM 等數值用 `FixedRng` 固定亂數，expected 由 ERB 逐行推導（註解行號）；
   Web 整合 1 case（出撃 → 戰鬥數回合 → 撤退或結束 → 回到 SHOP）。
8. unresolved「雜魚／クズ市民戰的結束路徑」在本 session 查清並結案或寫明已查處。

## 原則

- 查證規則同 AGENTS.md（引擎附 cs:行號、原作附 ERB 行號，不准猜）；既有 deviations 維持現狀（使用者裁決）。
- 範圍控制：42K 行的戰鬥只翻「上述流程走得到」的函式；每個被略過的分岐都要能停止而不是默默走錯。

## 不做

- 性攻擊／拘束中指令、連擊、反擊、戰報（S06）；事件戰（襲撃・救援，S06 視情況）；口上。

## 驗收

- `pytest` 全綠；瀏覽器可「出撃 → 打一場 BOSS 戰（至少能用攻擊指令進行數回合並撤退或分出勝負）→ 回到 SHOP」並存讀檔。
- `docs/STATUS.md` 寫好 S06 的具體起點；`source/`、`reference/` 無變更；報告三段。
