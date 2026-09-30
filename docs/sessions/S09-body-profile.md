# S09：身體資料生成（CHARA_MAKE_BASE_PROFILE／CHARA_SIZE_DEFAULT／SET_PROFILE）

## 目標
開局時角色的身體資料（年齡、身高、體重、三圍、胸の重量等 BASE:40–48 與相關 CSTR）目前沒有生成，
導致戰鬥的「胸部重量ペナルティ」把女性角色敏捷扣成 0、傷害 2 倍（deviations.md「開局身體資料未生成對戰鬥的影響」）。
本階段照原作生成身體資料，解除這個偏離，並讓 `SET_PROFILE` 的呼叫點（膨乳化等）不再停止。
路徑相對 `source/earGVP/ERB/`。

## 範圍
1. **開局生成**：`SYSTEM/キャラメイキング関連/CHARA_MAKE_DEFAULT.ERB@CHARA_MAKE_BASE_PROFILE`:493–984 與它呼叫的
   `CHARA_SIZE_UI.ERB@CHARA_SIZE_DEFAULT`（:2148 起）、`GENERATE_BODYLINE`、髮色瞳色等補完。
   接到 S03 的開局流程（`eragvt.game.opening`）；`FIRSTSETTING_CHARA.ERB`:331／:418／:486 的呼叫位置與順序照原文。
   只移植「預設生成」路徑；角色製作 UI 的手動編輯畫面（CHARA_SIZE_UI 的互動部分）不做，
   但若 UI 路徑與預設路徑共用計算函式，共用部分照原文移植。
2. **SET_PROFILE**：`FIRSTSETTING_CHARA_TALENT.ERB@SET_PROFILE`（:4 起）及其依賴。接上已移植流程中的呼叫點：
   `PRISON_COM105_膨乳化.ERB`:70（S08 目前在此停止）、`FIRSTSETTING_CHARA_SYUZOKU.ERB`:162（若開局流程會走到）。
   其餘呼叫點（出產、藥物調合、追加妖精、子觸手襲來）屬未移植系統，不在範圍。
3. **亂數**：一律經注入的 `GameRng`，依 ERB 求值順序抽。這會改變開局之後的亂數序列：
   受影響的既有 seed 測試 expected 依 ERB 重新推導並附行號，**不可**照 Python 輸出改。
4. **顯示**：SHOP 或狀態畫面已有顯示身體資料的地方（若既有移植有用到 BASE:40–48／相關 CSTR），確認顯示正確。
5. **偏離收尾**：更新 deviations.md——「開局：身體資料生成未移植」與「身體資料未生成對戰鬥的影響」兩條改為已解決（或縮小範圍並說明剩餘）。
   把 S08 的 SET_PROFILE 停止點從停止清單移除。

## 查證要點
- BASE／CSTR 番號與名稱照 `CSV/Base.csv`、`CSV/CSTR.csv`、`CSV定数定義/` 確認，不得自行命名。
- 用到的內建函式（例如 RAND 範圍、LIMIT、POWER、文字列函式）的語意查 `reference/emuera-1824/...cs:行號`。
- 若原作對特定角色 CSV 已有身體資料值，生成時「保留 CSV 值還是覆寫」照原文判定條件移植。

## 測試（table-driven，expected 由 ERB 推導）
- CHARA_SIZE_DEFAULT：數個代表組合（性別／種族／體型相關 TALENT）在 FixedRng 下的輸出，手算自原文。
- SET_PROFILE：膨乳化前後的變化。
- 開局整合：新遊戲後三名角色的 BASE:40–48 非 0 且在原作範圍內（範圍取自原文）。
- 戰鬥：胸部重量ペナルティ在正常體重下的敏捷值（以 `battle.hantei` 的既有式手算）。
- 全部既有測試仍綠（受亂數序列影響者依上述規則更新）。

## 模擬
重跑隨機方針 250 場（seed 0–249）：記錄停止原因頻度、敗北後平均存活半日數，與 S08（平均 1.5，最多 7）對照，寫進 STATUS。

## 完成條件
pytest 全綠；STATUS 更新；deviations／unresolved 更新；必要時 `docs/wiki/era/body-profile.md`（< 300 行）。
