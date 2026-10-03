# S28c1：自由行動（ACTION_PASTIME）＋一般自由行動事件

自主推進（使用者指定 2026-10-02）第 7 階段第 3 部分之一。自由行動事件共約 12.8K 行，拆為：
S28c1（本規格，約 5.4K 行）與 S28c2（ナンパ・酒ナンパ・痴漢，約 7K 行）。路徑相對 `source/earGVP/ERB/`。

## 範圍
1. `ゲーム内_行動実行処理/ACTION_PASTIME.ERB` 全體（PASTIME_SelectSchool、變身選擇「気晴らし」、RES_SCHEDULE(113)、各事件派發）；
   SHOP 預約 [108] 的停止點解除。
2. `ゲーム内_イベント発生/自由行動中イベント/` 中下列檔案：
   PASTIME_学校に行く（1658）、運動する（648）、淫気応急（562）、改造制服（507）、遠出する（478）、街に出る（429）、ファッション（415）、
   人気投票（391）、悪堕ち遭遇（259；S21 Part D 的 D4：`:19` `SQRT(FLAG:852)` 防衛力負數當 0，標 DEVIATION）、写真（255）、告られ（88）、学校途中編入（44）。
3. 上述事件呼叫到 ナンパ／酒ナンパ／痴漢（S28c2）時，照慣例停止並記錄；呼叫到クズ市民戰、雑魚戰等未移植戰鬥也同樣停止。
4. 地の文走 S07 catalog（狀態變化以 hooks 表）；共用 RESULT／RESULTS 照 `docs/wiki/python/result.md`。

## 測試（table-driven，expected 由 ERB 推導）
派發表（各 RAND 分岐）、各事件的代表分岐與狀態變化；整合：SHOP 預約自由行動 → TURNEND → SHOP。

## 模擬
`tools/sim.py --actions` 加入 108，預設、初期セット各 250 場（seed 0–249，`--max-shop 200`）：停止原因（預期 S28c2 的停止會出現，列出頻度）、各事件次數，與 S28b 對照。

## 完成條件
pytest 全綠；STATUS（≤120 行）、deviations、unresolved、`docs/wiki/era/actions.md` 更新。結束時務必送出三段報告。
