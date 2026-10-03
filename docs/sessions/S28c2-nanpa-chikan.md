# S28c2：自由行動事件本編（ナンパ・酒ナンパ・痴漢）

自主推進（使用者指定 2026-10-02）第 7 階段第 3 部分之二（S28 最後一份）。路徑相對 `source/earGVP/ERB/`。
S28c1 已移植發生判定與 `PASTIME_CHIKAN:4–465`；本階段補上三個本編，解除 S28c1 留下的三個停止點。

## 範圍
1. `ゲーム内_イベント発生/自由行動中イベント/PASTIME_ナンパ.ERB@MESSAGE_PASTIME_NANPA`（:73–）及其子函式。
2. `PASTIME_酒ナンパ.ERB@MESSAGE_PASTIME_SAKE_NANPA`（:74–）及其子函式。
3. `PASTIME_痴漢.ERB@MESSAGE_PASTIME_CHIKAN`（:470–）及其子函式。
4. 分工比照 S28c1：有 INPUT 或狀態變化為主的函式手翻成 Python（接到 `pastime.py`，必要時另開 `pastime_nanpa.py`）；
   以本文為主的函式走 S07 catalog，狀態變化以 hooks 表登記並測試原文一致。
5. 本編若呼叫未移植的系統（クズ市民戰、雑魚戦、其他未移植事件），照慣例停止並記錄位置與頻度；不要擴大範圍去翻那些系統。
6. 共用 RESULT／RESULTS 照 `docs/wiki/python/result.md`；性行為系的經驗／処女／妊娠等狀態走既有模組（`lovesex.py`、`pregnancy.py` 等）。

## 測試（table-driven，expected 由 ERB 推導）
三個本編各自的選單分岐（例：ナンパ的拒否／同行、痴漢的抵抗／下車／防犯ブザー）與代表性狀態變化；
整合：SHOP 預約自由行動 → ナンパ本編 → TURNEND → SHOP。

## 模擬
`tools/sim.py --actions 101–108`，預設、初期セット各 250 場（seed 0–249，`--max-shop 200`），前景分批跑：
停止原因、三個本編的次數與主要分岐，與 S28c1 對照（S28c1：預設 上限 95／ナンパ 120／痴漢 18／酒ナンパ 16）。

## 完成條件
pytest 全綠；STATUS（≤120 行）、deviations、unresolved、`docs/wiki/era/actions.md` 更新。結束時務必送出三段報告。
