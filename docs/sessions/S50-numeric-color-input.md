# S50：色彩輸入的數值格式補完

## 目標
- 消除 STATUS 所列色指定 R//G//B 十六進位／指數表記停止點。
- 依 Emuera 1.824 TOINT 實作完成現有原生 Python 輸入路徑，不新增直譯器。

## 範圍
- 先定位 chara_make 等現有數字轉換與狀態畫面的實際呼叫者。
- 查 reference 的詞法、進位、指數、正負號、空白、溢位及無效輸入行為；逐項附行號。
- 查原作色彩選單與相關既有共用呼叫者，確認範圍裁切、重新輸入及 RESULT(S) 語意。
- 手翻必要轉換規則，重用現有介面；同一共用函式的既有呼叫者同步驗證。
- 不擴充整套角色製作、不改其他尚未裁決事項；發現原作錯誤先登記，不自行修正。

## 驗收
- 從引擎與 ERB 推導 table-driven expected，先紅後綠；測試代表合法、邊界與無效格式。
- 少量存檔色碼→Web 狀態畫面顯示案例，確認新格式可到達、結果正確；不新增手動色彩選單。
- 主代理完整 pytest；source／reference 唯讀、UTF-8 無 BOM／LF、diff 檢查。
- 預設與 tokusou 各 seed 0–249、max-shop 200、actions 101–108，前景每批50局。
- 逐seed完整記錄與 S49 對照，驗證批次exit、seed全集、log／JSONL一致、catalog失敗數。
- 更新 STATUS（≤120行）與相關wiki；新未決／偏離才寫入對應文件。
- 主代理驗收後 commit／push main；完成本階段即停止。

## 驗收結果
- 先紅：`76 failed, 27 passed`；定向：`177 passed, 1 warning in 2.37s`。
- 主代理完整pytest：`3423 passed, 1 warning in 301.12s (0:05:01)`；新增108案。
- .NET Framework 4全BMP編碼／數字分類及1000組固定格式查證完成。
- 500局：default246上限／4回標題、tokusou250上限；catalog失敗0，完整結果逐seed與S49一致。
- 10批exit=0、seed全集及log／JSONL一致；source／reference未動，無新增未決／偏離。
