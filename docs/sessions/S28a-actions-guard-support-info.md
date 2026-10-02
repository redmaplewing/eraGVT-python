# S28a：行動——防衛・支援・情報収集・鍛錬スケジュール等

自主推進（使用者指定 2026-10-02）第 7 階段的第 1 部分。S28 規模約 19K 行（行動 6.1K＋自由行動事件 12.8K），拆為
S28a（本規格）、S28b（特別活動 SEISAN）、S28c（自由行動 PASTIME＋事件）。路徑相對 `source/earGVP/ERB/`。

## 背景
`action.py:256`：「行動は未移植（休憩・鍛錬・出撃のみ移植済み）」；`action.py:444` 鍛錬スケジュール（RES_SCHEDULE、CFLAG:110）；
`action.py:738` SENGIUP Lv5 的變身能力獲得；`action.py:253` 雑魚戦候補なし後的處理；`shop.py:960` 拉致監禁中角色的狀況顯示。

## 範圍
1. `ゲーム内_行動実行処理/ACTION_GUARD.ERB`（拠点防衛）、`ACTION_SUPPORT.ERB`（支援）、`ACTION_GATHER_INFORMATION.ERB`（情報収集，約 1.1K 行；
   含 S18 記錄的クズ市民監禁救出 CFLAG:71 減少、S21 Part D 的 D4：`:142` 的 `SQRT(FLAG:852)` 在防衛力為負時當 0，標 DEVIATION（使用者裁決 2026-10-02））。
2. `ACTIONsub_SCHEDULE.ERB`（RES_SCHEDULE、鍛錬スケジュール）、`ACTIONsub_TRANSFORMATION_SELECT.ERB`、`ACTIONsub_CHARA_POWERUP.ERB`、
   `ACTIONsub_DRUG_PREPARATION.ERB`、`ACTIONsub_TSUIKAYOUSEI_NORMAL.ERB`——若它們由本階段範圍內的行動（或已移植行動）呼叫則移植；
   只由 SEISAN／PASTIME 呼叫者留給 S28b／S28c。
3. `action.py:738` SENGIUP（戦闘基礎 Lv5 → 變身能力獲得，`:737–790`）、`action.py:253` MOB_TENTACLE_BATTLE 為 -1 後的處理、
   `shop.py:960` SHOP_SHOW_SITUATION_LIST:121–134（拉致監禁中角色顯示）。
4. SHOP 行動預約（[100] 系）讓上述行動可被選擇（照原文的可選條件）；Web 照既有輸入模式。
5. 共用 RESULT／RESULTS 寫入照 `docs/wiki/python/result.md`。

## 測試（table-driven，expected 由 ERB 推導）
各行動的成功／失敗分岐與狀態變化；情報収集的救出路徑（CFLAG:71）；RES_SCHEDULE；SENGIUP Lv5；整合：SHOP 預約防衛／支援／情報收集各一回 → TURNEND → SHOP。

## 模擬
`tools/sim.py` 讓隨機方針也會預約這些行動（若需要加參數），預設、初期セット各 250 場（seed 0–249，`--max-shop 200`）：停止原因、各行動實際次數，與 S27 對照。

## 完成條件
pytest 全綠；STATUS（≤120 行）、deviations、unresolved、`docs/wiki/era/actions.md` 更新。結束時務必送出三段報告。
