# S35：子供與變身後命名

## 範圍
- 依使用者確認，補齊子供命名及變身後命名：手動文字輸入、隨機命名、確認與原作預設路徑。
- 查明實際呼叫端並接入既有遊戲／Web 輸入流程，不建立無呼叫者的模組。
- 遊戲規則手翻 Python；候選文字優先抽取，保留原作 RNG 順序、重抽與共用 RESULT／RESULTS 語意。
- 遇 INPUTS 應等待玩家輸入，依原作處理空字串、取消、重選與確認，不自創名稱或預設。
- source/、reference/ 唯讀；不改既有裁決、不擴至市民戰或其他下一階段。

## 開發與驗收
- 精確搜尋先確認總筆數；局部閱讀，附 ERB 檔案@函式:行號及必要引擎 reference 行號。
- table-driven pytest 先紅後綠，expected 由原文推導，RNG 透過注入。
- 驗證命名各分支、取消／重選、字串保存、隨機抽取及實際呼叫續行。
- 少量 Web 輸入／存讀檔邊界測試；確認等待、提交後畫面與狀態正確。
- 凍結產品及測試後執行完整 pytest。
- 標準模擬：預設／tokusou各seed0–249、max-shop200、actions101–108，前景分批。
- 正常config2／3各seed0–9、40 SHOP，驗證原命名停止局可繼續，回報後續停止。
- S34基線：預設246上限／4回標題；tokusou250上限，catalog失敗0。
- S34 config2：5上限／2回標題／3子供命名；config3：4上限／1回標題／2子供命名／3市民戰。
- 模擬使用 python -X utf8 -u 與 --verbose，逐局輸出；最終版本才跑大批，保留可核對結果。

## 收尾
- 更新 STATUS（≤120行）及相關 wiki；僅有新增未決／偏離才更新對應文件。
- 核對 LF、UTF-8無BOM、source/reference未動與實際修改範圍。
- 子代理不commit/push；主代理獨立驗收後commit並推上main，本階段完成即停止。
- 回報做了什麼、已查證的依據、需要使用者決定。

## 驗收紀錄
- 先紅7個命名測試；最終新增37case（36個命名＋1個子供完整續行），含RNG重抽/static/文字/Web/存讀檔。
- 父代理首輪完整2106通過；欄寬顯示修正後最終完整：`2107 passed, 1 warning in 324.90s (0:05:24)`。
- config2：8上限／2標題；config3：5上限／1標題／4市民戰；各seed0–9、40SHOP，catalog失敗0，原命名停止已消除。
- 標準500局完成：預設246上限／4標題、tokusou250上限，與S34基線一致；10×50批次全部exit0。
- 520局catalog失敗0，seed全集／逐局log==jsonl已由`s35-summary.py --final`核對，檔案留於Windows TEMP。
- 原文與引擎依據見`docs/wiki/python/naming.md`；無新增UNVERIFIED／DEVIATION；source/reference唯讀。
