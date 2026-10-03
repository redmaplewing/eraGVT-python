# S32：HATUJOU_TO_HAIRAN 忠實移植

## 範圍
- 依使用者要求補上 S31 未納入的函式，不改動原作規則或文字。
- 依據：ERB/ゲーム内_戦闘処理/SUBEVENT_BATTLEE.ERB@HATUJOU_TO_HAIRAN:513–585。
- 條件、亂數判定及狀態更新手寫為 Python；敘述從原文抽取並沿用 catalog。
- 接回現有戰鬥呼叫端，不新增無呼叫者的模組。
- source/、reference/ 保持唯讀。

## 測試與查證
- table-driven pytest 先紅後綠；expected 由 ERB 推導。
- 驗證早退條件、10% 邊界、亂數消耗、既有旗標保留、回傳值與文字分支。
- 查證必要的引擎語意並記錄 reference 路徑及行號。
- 驗證原停止 seed 52／124／240 可通過該呼叫。
- 完整 pytest；預設及 tokusou 各 seed 0–249、max-shop 200、actions 101–108，前景分批模擬。
- 核對停止原因與 S31：預設 243 上限／4 回標題／3 本函式未實作；tokusou 250 上限。

## 收尾
- 更新 STATUS（≤120 行）及相關 wiki；新增未決或偏離才更新對應紀錄。
- 檢查 LF、UTF-8 無 BOM、git diff 範圍及唯讀路徑未動。
- commit 並推上 main，回報成果、查證依據及需裁決事項。

## 驗收結果
- 新增 22 項測試；完整 pytest：`1868 passed, 1 warning in 319.48s (0:05:19)`。
- 兩組各 seed 0–249，max-shop 200、actions 101–108，前景分批跑完。
- 預設：246 上限／4 回標題／0 未實作停止（S31：243／4／3）。
- tokusou：250 上限／0 回標題／0 未實作停止（與 S31 相同）。
- seed 52／124／240 各成功觸發一次，均達 200 SHOP；兩組 catalog 失敗皆為 0。
- 原作條件、顯示順序、旗標與 RETURN 已查證；引擎引用見 narration.md 與程式／測試。
- 無新增 UNVERIFIED／DEVIATION；source/、reference/ 未動。
