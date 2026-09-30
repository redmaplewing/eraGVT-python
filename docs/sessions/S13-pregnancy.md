# S13：妊娠系統（受精成立 → 妊娠進行 → 出産・苗床出産 → 子供）

## 背景
S12 後最大的停止原因是受精成立（預設開局 250 場中 137 場），ゲームオーバーモード中也只會停在受精成立與苗床出産。
目前的停止點：`battle/ninsin.py`（NINSIN_SUBMIT 以降、父親 ID 各分岐）、`battle/after.py:74`（NINSIN_CHECK_AFTER）、
`turnend.py:340`（BIRTH_HANTEI）、`turnend.py:869`（BIRTH_AUTO_RANDOM）、`battle/func.py:195`（ACT_LIMIT 妊娠後期）。
路徑相對 `source/earGVP/ERB/`。

## 範圍
1. **受精與妊娠進行**：`ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB` 全體——
   NINSIN_HANTEI 尚未移植的父親分岐（:11–165，PAPA_ID 0／≤ -100／悪堕ちキャラ）、NINSIN_CHECK_AFTER（:169）、
   NINSIN_FLAG（:195）、NINSIN_TS_FIX、BIRTH_HANTEI（:277）、BIRTH_TENTACLES（:416）、ABL_UP_BIRTH、NUM_CHILD_TENTACLE、
   BIRTH_AUTO_RANDOM（:606）、NINSIN_SUBMIT（:752）、CHECK_HININ_F／CHECK_PREGNANT_F、PREGNANT_RANDOM_SIZE、
   PREGNANCY_BOOB_EXPAND／BELLY_EXPAND（S09 的 `game.body` 重用）。
2. **行動限制**：`ACT_LIMIT` 的妊娠後期分岐（`battle/func.py:195`），以及 SET_PARTYMEMBER 的妊娠出撃／防衛不可（S08 已移植判定，確認接上）。
3. **出生的子供**：`PREGNANT_CHILD_BIRTH.ERB`、`PREGNANT_CHILD_BIRTH_N.ERB`——
   BIRTH_DAUGHTER_TENTACLE_ORIGIN／HUMAN_ORIGIN、ADD_CHILD（新角色的生成，S10 的 `game.chara_make` 與 `game.body` 重用）、
   GROW_HANTEI、CHILD_GROW_1／2、TRAINING_HOSEI_CHILD。RESCUE_CHILD 若由已移植流程（S08 救出）呼叫則一併移植。
   若某分岐需要大量未移植系統（例如角色製作 UI 的互動），照慣例停止並記錄，**但預設路徑上會走到的部分必須完成**。
4. **文字**：`地の文/MESSAGE_NINSIN.ERB` 與出産相關地の文走 S07 catalog；狀態變化以 hooks 表移植並對照測試。
5. **顯示**：SHOP／狀態列已有的妊娠顯示（若有）接上，不新增畫面。

## 不做
- 動画流出、悪堕ちキャラの淫謀本體（受精判定中讀到悪堕ちキャラ時，只移植判定所需的部分）。

## 查證要點
- 妊娠相關 CFLAG／TALENT 番號與意義照 `CSV定数定義/` 與原文註解。
- ADDCHARA／ADDVOIDCHARA、SWAPCHARA、CSV 番號與 NO 的處理照 `reference/emuera-1824/...cs:行號`（S02／S10 已查證者引用即可）。

## 測試（table-driven，expected 由 ERB 推導）
- NINSIN_HANTEI 各父親分岐、NINSIN_SUBMIT／NINSIN_FLAG 的狀態變化。
- BIRTH_HANTEI 的經過日數與出産判定、BIRTH_TENTACLES／苗床出産（FixedRng）。
- ADD_CHILD：新角色的 NO、CALLNAME、TALENT、身體資料（照原文分岐手算）。
- 整合：受精 → 數回合 → 出産 → 子供加入 → SHOP；存讀檔往返。

## 模擬
`tools/sim.py` 跑預設開局與初期セット各 250 場（seed 0–249）：停止原因頻度、停止前 SHOP 次數、ゲームオーバーモード後的回合數，與 S12 對照寫進 STATUS。

## 完成條件
pytest 全綠；STATUS、deviations、unresolved 更新；`docs/wiki/era/pregnancy.md`（< 300 行）說明妊娠狀態機與 CFLAG 對照。
