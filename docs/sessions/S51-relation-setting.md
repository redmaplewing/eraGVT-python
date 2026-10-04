# S51：開局角色關係設定

## 目標
- 接通 HEROINE_PRESET [30] 相関関係，消除開局可點選的未移植停止點。
- 手翻 CONVERT_RELATION／SET_RELATION 與原作可達選單；重用既有關係讀取及檢查。

## 範圍
- 查 ERB/SYSTEM/キャラメイキング関連/CHARA_RELATION.ERB 及開局呼叫順序。
- 核對角色選擇、可選條件、雙向關係、互斥規則、確認／取消與資料回寫；不假設每種關係對稱。
- 依原作處理暫存、RESULT／RESULTS、INPUT與WAIT；引擎行為附reference行號。
- 固定文字優先抽取，邏輯原生Python手翻，亂數使用注入RNG。
- 接通實際開局流程，驗證既有狀態顯示與存讀檔讀到新設定。
- 不擴充其他角色製作選單、不改既有裁決；原作疑義需附證據，不自行修正。

## 驗收
- 先紅後綠的table-driven測試，expected從ERB推導。
- 覆蓋角色選擇、各關係資料與限制、無效輸入、返回及重入；少量Web／存讀檔邊界案例。
- 主代理獨立完整pytest；source／reference唯讀，UTF-8無BOM／LF，diff檢查。
- default與tokusou各seed 0–249、max-shop 200、actions 101–108，前景每批50局。
- 以tmp/s50為基線，核對500局完整記錄、seed全集、批次exit、log／JSONL及catalog失敗。
- 更新STATUS（≤120行）與相關wiki；有新未決／偏離才登記，交使用者裁決。
- 主代理驗收後commit／push main；完成S51即停止。

## 驗收結果
- 新增68案，先以缺模組失敗，實作後定向123案通過；CHECK_ALL_RELATION殘值案亦先紅後綠。
- 主代理完整pytest：`3491 passed, 1 warning in 284.05s (0:04:44)`。
- 原作CHARANUM越界、主人OR條件、いとこ隱藏輸入照原文保留，無新增UNVERIFIED／DEVIATION。
- 500局：default246上限／4回標題、tokusou250上限；catalog失敗0，逐seed完整結果與S50一致。
- 10批exit=0；seed全集、log／JSONL通過tmp/s51/audit.py。標準模擬未進新選單，字串顯示最後修正由完整pytest覆蓋。
- source／reference未動、UTF-8無BOM／LF、diff檢查通過；由主代理commit／push。
