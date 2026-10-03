# S28b：特別活動（ACTION_SEISAN・特別活動/）

自主推進（使用者指定 2026-10-02）第 7 階段第 2 部分。路徑相對 `source/earGVP/ERB/`。

## 範圍
1. `ゲーム内_行動実行処理/ACTION_SEISAN.ERB`（SEISAN_INIT、變身選擇、RES_SCHEDULE 111、各活動派發、`_ABLUP, 1`、TRANSFORM）。
2. `ゲーム内_行動実行処理/特別活動/` 全部：SEISAN_INIT、CALC_SEISAN、CALC_CHARM_FEAT（S28a 已部分移植者重用）、
   SEISAN_0_PART_TIME〜SEISAN_8_IDOL_LIVE。
3. 地の文 `地の文/特別活動関係/MESSAGE_SEISAN_*` 走 S07 catalog（狀態變化以 hooks 表）；需要的話擴充 catalog。
4. 讀寫其他系統的值：S14 記錄的 CFLAG:284／285（動画流出）、S26 FLASHNEWS 讀的 SAVESTR:21〜26、CFLAG:283／287（偶像等）——
   照原作寫入，使 FLASHNEWS 的偶像／動画系新聞可以出現；共用 RESULT／RESULTS 照 `docs/wiki/python/result.md`。
5. SHOP 行動預約讓特別活動可選（照原文可選條件）；`action.py` 中特別活動的停止點解除。
6. 不在範圍：SHOP 的 CHARA_POWERUP（`SHOP.ERB`:254）、DRUG_PREPARATION（:264）、TSUIKAYOUSEI_NORMAL（:294）——它們是 SHOP 子選單，不是行動；列入後續候選。

## 測試（table-driven，expected 由 ERB 推導）
各活動的成功／失敗與報酬、偶像系的狀態累積、動画流出相關的 CFLAG 變化；整合：SHOP 預約特別活動 → TURNEND → SHOP（含新聞）。

## 模擬
`tools/sim.py` 的 `--actions` 加入特別活動，預設、初期セット各 250 場（seed 0–249，`--max-shop 200`）：停止原因、各活動次數，與 S28a 對照。

## 完成條件
pytest 全綠；STATUS（≤120 行）、deviations、unresolved、`docs/wiki/era/actions.md` 更新。結束時務必送出三段報告。
