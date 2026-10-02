# S26b：事件戰新聞的 RESULTS:0 殘值照原作

依使用者既有裁決（2026-10-02「殘值照原作」，S21／S22）處理 S26 留下的暫定 DEVIATION。路徑相對 `source/earGVP/ERB/`。

## 背景
`SHOP_FLASHNEWS.ERB`:74–87 `TRYCALLFORM EVENT_BATTLE_FLASHNEWS_n` 後 `LOCALS'=RESULTS`；呼叫對象不寫 RESULTS:0 的情況
（3001／3002／6001／6002 本體全註解、3004 任務失敗、5 任務前敗北被俘）會讀到前次殘留的 RESULTS:0。S22 判斷「RESULTS:0 不需模型化」，
S26 發現此反例；目前 `flashnews.py` 以 `# DEVIATION:` 讀 Python 手上的值（多半空字串）。模擬中 3001／3002 走到此路 102／87 次（預設／初期セット）。

## 範圍
1. 追查原作從**事件戰結束**到 SHOP 的 FLASHNEWS:74 之間（以及事件戰中最後幾步），會寫 RESULTS:0 的所有來源：
   直接代入、`RESULTS =`、式中関数當命令用（`Instraction.Child.cs`:390–409）、STRDATA／INPUTS 等內建命令、TRYCALLFORM 呼叫的函式內寫入（例：`TENTACLE_ACCESS`:200 的錯誤字串）。
   全域 grep 先看總筆數，逐一確認哪些在這段路徑上會被執行。
2. 對其中**已移植**的位置，讓 Python 同步寫入共用 RESULTS:0（照 `docs/wiki/python/result.md` 規則），使 FLASHNEWS:74 讀到與原作相同的值；
   移除 S26 的 DEVIATION，更新 deviations.md 與 result.md（訂正「RESULTS:0 不需模型化」的範圍說明：列出已模型化的寫入來源）。
3. 若某寫入來源在未移植系統內、路徑上確實會被執行，列出並說明影響（照慣例：該情況停止或記錄）。

## 測試
3001／3002 戰後、3004 任務失敗、5 任務前敗北各一條代表路徑：FLASHNEWS 讀到的 RESULTS:0 與手算原作一致（附 ERB 行號）。

## 模擬
`tools/sim.py` 預設、初期セット各 250 場（seed 0–249，`--max-shop 200`）：確認無新停止。

## 完成條件
pytest 全綠；STATUS（≤120 行）、deviations、wiki 更新。結束時務必送出三段報告。
