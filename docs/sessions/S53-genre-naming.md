# S53：主題隨機命名

## 目標
- 手翻 RANDOMNAMING_FROMGENRE，接通開局與角色製作現有停止入口。
- 依原作主題資料、抽選順序與結果殘值產生命名；不自行新增名字或命名規則。

## 範圍
- 精確查明定義、全部呼叫者及主題設定來源，先看搜尋總數再讀相關局部。
- 名稱資料優先抽取；選擇與亂數流程寫為原生 Python，不新增直譯器。
- 查證 RESULT／RESULTS、陣列、字串、亂數與重複抽選語意，附 ERB 函式與引擎行號。
- 接通既有開局／角色製作呼叫者與 GlobalStore GLOBAL:8 載入；主題手動 UI 留待完整角色製作階段。
- 原作不完整或需偏離時列出證據，交使用者裁決，不猜測補完。

## 驗收
- 先紅後綠 table-driven pytest；expected 由原文推導，RNG 使用注入物件。
- 覆蓋各主題、邊界、抽選順序、結果殘值、實際呼叫與固定資料重抽。
- 少量 Web／存讀檔邊界案例，由既有全域設定載入主題，確保開局不中斷。
- 產品與測試固定後通知主代理獨立跑完整 pytest。
- default、tokusou 各 seed 0–249，max-shop 200、actions 101–108，10 個前景批次各 50 局。
- 結果寫 tmp/s53，逐 seed 與 tmp/s52 完整紀錄比對；核對退出碼、seed 全集、log／JSONL、catalog 失敗。
- 更新 STATUS（≤120 行）、相關 wiki；新未決／偏離才更新對應文件。
- source／reference 唯讀；UTF-8 無 BOM、LF、diff 檢查。
- 子代理不 commit／push；主代理驗收後 commit／push main，完成 S53 即停止。

## 驗收結果
- 新增49案，先紅為缺少新模組；定向144案全過，主代理完整`3563 passed, 1 warning in 297.70s (0:04:57)`。
- 標準500局：預設246上限／4回標題、初期セット250上限，catalog失敗0；完整紀錄逐seed與S52一致。
- 全部10批exit=0，seed全集與log／JSONL核對通過；無新增未決／偏離，主題手動UI留待完整角色製作階段。
