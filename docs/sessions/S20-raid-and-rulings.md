# S20：襲撃／救援イベント戰＋使用者裁決的修正（2026-10-01）

路徑相對 `source/earGVP/ERB/`。

## Part A：襲撃／救援イベント戰
目前 `turnend.raid_hantei` 判定成立時只印「（未實作…スキップします）」並跳過（deviations.md「襲撃／救援 會被跳過」）——唯一還會跳過的事件。
1. `ゲーム内_イベント発生/強制発生イベント/FORCE_襲撃or救援イベント発生.ERB@RAID_HANTEI`（已移植判定部分對照確認），
   `JUMP RAID_RESCUE／RAID_ATTACK` 照引擎語意（JUMP＝不返回；查 `reference/emuera-1824` 並附行號）。
2. `イベントから派生する特殊戦闘/●イベント戦闘_襲撃共通.ERB`（RAID_ATTACK）、`●イベント戦闘_救援共通.ERB`（RAID_RESCUE、RAID_MISSION_SUCCESS／FAILURE），
   各イベント：救援 2（女子高救出）、3（女性自衛官小隊救援）、4（攫われた女性）、5（触手洞窟）；襲撃 3001〜3004；`特殊シチュエーション.ERB`。
   `EVENT_BATTLE_EXEC_{FLAG:45}` 等 TRYCCALLFORM 派發照原文；`BEGIN TRAIN` 接到既有戰鬥流程，FLAG:45 的戰後處理（`turnend.py` 的 FLAG:45 分岐）接上。
3. 若某イベント需要尚未移植的戰鬥種類（雑魚敵戰等），該イベント照慣例停止並記錄；其餘照常移植。クズ市民戰（6xxx）不在範圍。
4. 移除 `_skip_event`，更新 deviations.md 該條。

## Part B：使用者裁決的偏離（全部標 `# DEVIATION:`，記入 deviations.md 並寫明「使用者裁決 2026-10-01」）
1. **防衛力為負**：`AKUOTI_ATTACK` 的 `SQRT(FLAG:852)` 在 FLAG:852 < 0 時當 0 計算（原作會 CodeEE 停止）。
2. **クズ市民脅迫クールダウン**：CFLAG:72（原作只設 8、無遞減）改為每回合（半日）TURNEND 時 > 0 則 −1。
   遞減位置放在 `SHOP_TURNEND` 中 INTIMIDATION 判定（:88–99）之前，並在註解說明。
3. **夜這い淫乳條件**：`YOBAI_EVENT` 的 `TALENT:淫乳 * 3 + ABL:Ｃ感覚`（:160–177）改用 `ABL:Ｂ感覚`。
4. **夜這い奉仕的フェラ経験**：HOUSHI_4／5 的 `LOCAL:124 = LOCAL:324`（:3237、:3622）因在 VARSET LOCAL 之後恆 0；
   改為保留 VARSET 前的 LOCAL:324（有フェラ時フェラ経験 +1，與 :1738／:2063 的寫法一致）。
5. **子触手襲来**：襲擊成功時 FLAG:44 −1（與失敗分岐相同的減法）。
6. 夜這い HOUSHI_4 的處女喪失原因（CFLAG:206 寫在實行者）**暫不修改**，等使用者裁決。

## 不做
- クズ市民戰（6xxx）、雑魚敵戰本體、悪堕ち容姿、[反撃]。

## 測試（table-driven，expected 由 ERB 推導；Part B 由裁決內容推導並註明）
- RAID_HANTEI → RESCUE／ATTACK 各イベント的發生條件與戰鬥開始；勝敗後的 RAID_MISSION_SUCCESS／FAILURE。
- 整合：救援 1 例、襲撃 1 例走完並回 SHOP；存讀檔往返。
- Part B 每項至少一個 case（修改前後的差異）。

## 模擬
`tools/sim.py` 預設開局與初期セット各 250 場（seed 0–249，`--max-shop 200`）：停止原因、襲撃／救援實際次數，與 S19 對照寫進 STATUS。

## 完成條件
pytest 全綠；STATUS（≤150 行，必要時壓縮舊階段敘述）、deviations、unresolved 更新。結束時務必送出三段報告。

## Part C：使用者追加裁決（2026-10-01，S20 中途併入）
1. **C1 夜這い HOUSHI_4 處女喪失原因**：原作把 CFLAG:206 寫在實行者 LCOUNT（`FORCE_夜這い.ERB`:3088–3092），改寫在失去處女的對象。
   標 `# DEVIATION:`（使用者裁決），記入 deviations.md，補測試。（取代 Part B 第 6 項「暫不修改」。）
2. **C2 斜體支援**：`TextOutput` 的 Segment 加斜體屬性（FONTITALIC／FONTREGULAR），Web 模板以 CSS 顯示；akuoti 動画拡散與 narration runtime
   原本忽略 FONTITALIC 處改為實際套用，移除兩處 DEVIATION 與 deviations.md 的斜體部分。補測試（JSON 欄位增加時同步更新既有測試）。
3. **C3 調查（不改程式）**：悪堕ちキャラ幽閉的 PALAM_HOSEI 殘值（`COMMON_TENTACLE_DATA.ERB`:314–343、`EVENT_PALAM_UP.ERB`:134–140）：
   追查到達路徑與各路徑最後寫入 RESULT:1–11 的函式（附 ERB／reference 行號），結論寫入 unresolved.md 與最終報告；
   若固定則提出照原作移植方案（不實作），若不固定則列出變動來源。
