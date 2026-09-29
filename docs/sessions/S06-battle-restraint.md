# S06 — 戰鬥補完：拘束・性攻擊・絶頂・敗北（垂直切片完成）

建議模型：Opus 5.5（effort high）。開場讀 `AGENTS.md`、`docs/STATUS.md`（「下一步 → S06」有具體起點）、`docs/PLAN.md`，
需要時查 `docs/wiki/era/battle-overview.md`、`docs/wiki/python/state.md`。路徑相對 `source/earGVP/ERB/ゲーム内_戦闘処理/`。

## 目標

一場 BOSS 戰從開始到結束都不會因「未移植」停住（常見路徑：被拘束 → 性攻擊 → 振り解く／絶頂 → 勝利／敗北／時間切れ），
戰後回到 TURNEND → SHOP 並可存讀檔。＝PLAN 的垂直切片：「可玩一整回合含一場戰鬥並存讀檔」。

## 交付物（依優先順序；後面的做不完就停止＋登記，不要犧牲前面的正確性）

1. **拘束後的敵行動**：`ENEMY_ACTION.ERB` 拘束分岐、`ENEMY_ACTION_SEX_ROUTINE`（:1162）、
   `TENTACLE_BOSS_{n}_SEX_ROUTINE`（`触手データ/ボス触手/`，開局可遇的 BOSS 1–7）、`戦闘コマンド(性攻撃)/SEX_COMABLE.ERB`、
   `SEX_COM0–20`（本體；口上呼叫只走 NarrationService 的「無口上」路徑）、必要的 `SEX_COMEX`／`AUTO_V_DEFENCE`。
2. **拘束中的玩家指令**：`COMABLE.ERB` 與 `COMF8–15`（振り解く・暴れる・耐える・なすがまま・受け入れる・奉仕する・
   Ｖ挿入防御・救出する）、`40`、`44–47`、`100–104`，`SHOW_USERCOM` 拘束分岐（`BATTLE_COM.ERB`:382–441）。
3. **絶頂・射精**：`PALAM_UP.ERB` 絶頂處理（`PALAM_CALC_ECSTASY`、刻印取得等 S05 停下的部分）、`TENTACLE_SYASEI.ERB`、
   `GAPING.ERB` 中常見路徑用到的部分；懷孕判定若走到可停止並登記。
4. **敗北**：`BATTLE_COM_AFTER.ERB`:850–1100 的敗北處理 → 幽閉狀態設定、`BATTLE_TRAIN_AFTER.ERB@EVENTEND` 敗北分岐（:335–422 附近）。
   幽閉後的夜間 `PRISON` 本體若未移植 → 停止並登記（但戰鬥本身與 EVENTEND 要能走完）。
5. **剩餘指令**：6・7・16・17・69–74、反擊（`HANGEKI_STYLE.ERB`）、バースト。時間不夠可延後，但要登記。
6. **測試**：各新移植函式 table-driven（`FixedRng`，expected 由 ERB 逐行推導、註解行號）；
   整合：以固定 seed 從開局跑「出撃 → 戰鬥到結束 → SHOP」的 end-to-end 測試，並覆蓋「被拘束」路徑至少一次；
   Web 整合 1 case（戰鬥結束後存讀檔）。瀏覽器實測一場完整戰鬥。

## 原則

- 查證規則同 AGENTS.md；既有 deviations 維持現狀（使用者裁決），包含「身體資料 0 對戰鬥式的影響」——不要自行補身體資料。
- 大量的性攻擊文字屬地の文／口上：只移植狀態變化與必要的非口上輸出；口上一律走 NarrationService。

## 不做

- 事件戰（襲撃・救援）、拠点防衛、雜魚戰系統、ラスボス、幽閉中的夜間事件本體、口上／地の文 catalog（S07）。

## 驗收

- `pytest` 全綠；固定 seed 的 end-to-end 戰鬥測試通過；瀏覽器可玩完一場戰鬥並存讀檔。
- `docs/STATUS.md` 寫好 S07（口上／地の文抽取管線）與「S06 後仍會停止的分岐一覽」；`source/`、`reference/` 無變更；報告三段。
