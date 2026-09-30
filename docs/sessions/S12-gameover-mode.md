# S12：ゲームオーバーモード（全滅／洗脳／取り込まれ結局之後的持續遊玩）

## 背景
S08 起 `ENDING_1`（全滅）、`ENDING_4`、`ENDING_5` 印完本文後停止（`eragvt.game.ending` 的 NotImplementedError）。
S11 模擬（預設開局 250 場）中這是最大停止原因（88 場）。原作在結局後 `CALL CHANGE_GAMEOVER_MODE`
（`ゲーム内_イベント発生/オープニング処理_カスタムGAMEMODE.ERB`:112–114：`FLAG:0 = 0`、`DAY:2 = DAY*2+TIME`）、`FLAG:999 = -998`，
進入「全キャラが凌辱され続け、終わりはありません」的模式繼續遊玩。路徑相對 `source/earGVP/ERB/`。

## 範圍
1. **模式切換**：`CHANGE_GAMEOVER_MODE`、`CHECK_GAMEOVER_F`、`GAME_MODE_CHECK(_F)`（同檔 :112–140）、
   `FLAG:999 = -998` 的所有讀取處（全域搜尋，列出並逐一移植），ENDING_1／4／5 之後回到遊戲流程的路徑
   （ENDING.ERB:280–300、:560、:651 附近，以及呼叫端返回後的 TURNEND／SHOP 流程）。
2. **各處的 `CHECK_GAMEOVER_F()` 分岐**（共約 30 處，逐一照原文）：
   - `インターミッション画面/SHOP.ERB`（12 處：選單顯示、:405、:504／:534、:617 等）
   - `インターミッション画面/SHOP_TURNEND.ERB`（4 處：:186、:199、:380、:461）
   - `ヒロイン関連/SET_PARTYMEMBER.ERB`、`ゲーム内_イベント発生/敗北幽閉中イベント/PRISON.ERB`（`@PRISON` 的全員幽閉處理）、
     `ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB`、`地の文/MESSAGE_PRISON.ERB`（5 處，地の文走 S07 catalog）、
     `ENDING.ERB`（2 處）。
   - `ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB`、`強制発生イベント/FORCE_悪堕ちキャラの淫謀.ERB` 屬未移植系統：
     只在已移植流程會走到時處理，否則照慣例停止並記錄。
3. **Web**：遊戲結束畫面改為繼續遊玩；ゲームオーバーモード中的 SHOP 畫面照原作顯示（隱藏的選單、提示文字）。
   存讀檔往返要保留模式狀態（FLAG:0、DAY:2 等本來就在存檔內，確認即可）。
4. 既有 `ending.py` 的停止改為接續；ENDING 本文輸出不變。

## 不做
- 其他結局（ENDING_2／3／ラスボス等）與クリア實績（GLOBAL）、周回要素（FLAG:906）。
- 妊娠出產、悪堕ちキャラの淫謀（除非在本模式的既有流程中必經，屆時照慣例停止）。

## 查證要點
- `モードオプション`、`MODE_GAMEOVER` 等常數的定義位置與值（DIM.ERH／CSV定数定義），不得推測。
- FLAG:0 的各 bit 意義（時間制限等）照原文註解；清成 0 後各處受影響的判定要逐一確認。
- 引擎行為（BEGIN、RESTART 等若有使用）附 `reference/emuera-1824/...cs:行號`。

## 測試（table-driven，expected 由 ERB 推導）
- CHANGE_GAMEOVER_MODE 前後的 FLAG:0、DAY:2；CHECK_GAMEOVER_F／GAME_MODE_CHECK 的判定表。
- SHOP 在ゲームオーバーモード中的選單顯示差異（對照 :133–277 的條件）。
- TURNEND：:199、:380、:461 分岐。
- 整合：全滅 → ENDING_1 → ゲームオーバーモード → TURNEND → SHOP 至少 2 回合；存讀檔往返。

## 模擬
`tools/sim.py`（S11 起共用）跑預設開局與初期セット各 250 場（seed 0–249）：停止原因頻度、停止前 SHOP 次數，
並記錄進入ゲームオーバーモード後平均能再走幾回合。與 S11 對照寫進 STATUS。

## 完成條件
pytest 全綠；STATUS、deviations、unresolved 更新；必要時在 `docs/wiki/era/flow.md` 補一節「ゲームオーバーモード」。
