# S23：[反撃]スタイル（反撃準備・ＥＸ反撃・HANGEKI_TO_TENTACLE）

自主推進（使用者指定 2026-10-02）的第 2 階段。路徑相對 `source/earGVP/ERB/`。

## 背景
[反撃]スタイル相關的停止點（`grep -rn NotImplementedError src | grep 反撃`）：
- `battle/commands.py`：反撃成功時の攻撃（`MESSAGE_BATTLE_CHARA_ATTACK_HANGEKI`）、反撃準備、ＥＸ反撃
- `battle/enemy.py`：[反撃]スタイルの完全防御文（PRINTDATAL）、`HANGEKI_TO_TENTACLE`
S16 已接上バースト側的 [反撃] 攻擊力與蓄積傷害加算；S16 報告指出「[反撃] 的蓄積傷害目前恆 0（只有ＥＸ反撃會累積）」。

## 範圍
1. `ゲーム内_戦闘処理/HANGEKI_STYLE.ERB` 全體，以及 `COMMON_BATTLE_HANTEI.ERB`、`ENEMY_ACTION.ERB`、`BATTLE_COM_AFTER.ERB`、`COMBO_ATTACK.ERB`、
   `戦闘コマンド(ヒロイン)/COMF4.ERB`、`COM_ATTACK_COMMON.ERB` 中 [反撃] 相關而尚未移植的分岐（全域 grep `反撃|HANGEKI`，先看總筆數，逐處對照）。
2. 地の文 `地の文/MESSAGE_BATTLE.ERB` 的反撃系（含 `MESSAGE_BATTLE_CHARA_ATTACK_HANGEKI`）走 S07 catalog；狀態變化以 hooks 表。
3. `武器と衣装/武器カスタマイズ関連/FIGHT_STYLE.ERB` 中戰鬥實際用到的部分（例：`SET_FSTYLE_INFO` 等）；其寫入 RESULTS:0〜2 者必須寫進 S22 的共用 RESULTS
   （見 `docs/wiki/python/result.md`）。武器客製化 UI 不在範圍。
4. 預設開局／初期セット的角色是否會有 [反撃]スタイル：查原文確認到達條件，寫進報告；若隨機模擬到不了，`tools/sim.py` 加一個測試用選項
   （例：指定角色的スタイル為 [反撃]，明示為人工狀態）以驗證路徑。
5. 雜魚敵（TENTACLE_MOB_901／902 等）中的 [反撃] 分岐不在範圍（雜魚戰未移植）。

## 測試（table-driven，expected 由 ERB 推導）
反撃準備 → 敵攻擊 → 反撃成功／失敗、ＥＸ反撃、蓄積傷害累積與過剰蓄積、完全防御文；整合：[反撃]スタイル角色打完一場ボス戰。

## 模擬
`tools/sim.py` 預設、初期セット各 250 場（seed 0–249，`--max-shop 200`），加上 [反撃]スタイル的人工選項一組：停止原因、反撃相關路徑實際次數，與 S22 對照。

## 完成條件
pytest 全綠；STATUS（≤120 行）、deviations、unresolved 更新。結束時務必送出三段報告。
