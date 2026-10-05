# S55：角色製作主選單與共通設定

## 目標
- 接通原作 CHARA_MAKE_MAIN 主選單與共通設定，讓 S53／S54 功能可由 Web 操作。
- 可修改共通設定、載入／儲存全域設定、完成角色製作並正常進入開局後續流程。

## 範圍
- 查明主選單與共通設定各分支、顯示、輸入、返回及完成時的呼叫順序。
- 手翻主選單、共通命名／種族／特性／性格設定及全域讀寫；固定文字優先抽取。
- 復用已有命名、數值解析、生成、初期セット等實作；不新增通用 ERB 直譯器。
- 主選單其他入口若尚未移植，依原作呈現入口並明確停止，不靜默略過或發明替代。
- 預設直接完成的狀態與 RNG 必須等同目前原作預設路徑；核對兩次 FINALIZE。
- 查證 INPUT／INPUTS、全域存取、RESULT／RESULTS、字串及返回語意，附原作與引擎行號。
- 先確認實際相依範圍；原作缺漏／需偏離則列證據交使用者裁決。

## 驗收
- 先紅後綠 table-driven pytest，expected 由原文推導。
- 覆蓋共通選項、有效／無效輸入、取消／返回、全域讀寫、殘值與 RNG。
- Web 可操作主題與兩項生成設定，完成開局、存讀檔後一致；手動編輯未完成處明確停止。
- 同步更新非互動 helper／模擬的預設輸入，僅增加原作直接確定的步驟，不改遊戲選擇。
- 產品測試固定後通知主代理獨立完整 pytest。
- default、tokusou 各 seed 0–249，max-shop 200、actions 101–108，10 個前景批次各 50 局。
- tmp/s55 逐 seed 與 tmp/s54 完整比對；核對退出碼、seed 全集、log／JSONL與 catalog 失敗。
- 更新 STATUS（≤120 行）、相關 wiki；新未決／偏離才更新對應文件。
- source／reference 唯讀；UTF-8 無 BOM、LF、diff 檢查。
- 子代理不 commit／push；主代理驗收後 commit／push main，完成 S55 即停止。

## 驗收結果
- 新增58案；定向136 passed，主代理完整3691 passed, 1 warning in 326.65s (0:05:26)。
- 500局全部逐seed完整結果同S54：default246上限／4回標題，tokusou250上限，catalog失敗0。
- 10批前景exit=0，seed全集與log／JSONL一致；`tmp/s55/audit.py` 通過。
- 其他固定說明套組確認後停止；6／7／8的隨機AA說明未移植，在說明入口停止。
- 無新增UNVERIFIED／DEVIATION；source／reference未動。
