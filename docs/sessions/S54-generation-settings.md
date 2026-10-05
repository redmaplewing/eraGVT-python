# S54：角色自動生成設定

## 目標
- 消除 FLAG:824 自動分配フィート與 FLAG:825 限定有口上性格的未移植停止。
- 接到既有 initialize_race／initialize_personality 與全域設定載入，不新增臨時角色製作 UI。

## 範圍
- 查明 SET_FEAT_DEFAULT、性格抽選原文、依賴函式及全部呼叫者。
- 原生 Python 手翻分配與抽選，保留原作順序、限制、重抽、結果殘值與注入 RNG 消耗。
- 查證 TRYCCALLFORM 等所需引擎行為，引用 ERB 函式與 reference 行號。
- 有口上判斷與必要呼叫沿用既有 catalog／敘事介面；不自行以近似判斷取代。
- 原作缺漏、不可達或錯誤分支先列證據；需偏離時交使用者裁決，不自行修正。
- 手動設定 UI 留待完整角色製作階段；原作預設未開啟時行為保持一致。

## 驗收
- 先紅後綠 table-driven pytest，expected 由原文推導。
- 覆蓋各種族分配、性格存在／缺少口上、重抽與 RNG、結果殘值、既有設定保留。
- 少量實際開局與 Web／存讀檔案例，由全域設定載入兩選項後可正常繼續。
- 產品測試固定後通知主代理獨立跑完整 pytest。
- default、tokusou 各 seed 0–249，max-shop 200、actions 101–108，10 個前景批次各 50 局。
- tmp/s54 結果逐 seed 與 tmp/s53 完整比對；核對退出碼、seed 全集、log／JSONL、catalog 失敗。
- 更新 STATUS（≤120 行）、相關 wiki；新未決／偏離才更新對應文件。
- source／reference 唯讀，UTF-8 無 BOM、LF、diff 檢查。
- 子代理不 commit／push；主代理驗收後 commit／push main，完成 S54 即停止。

## 查證與定向結果
- SET_FEAT_DEFAULT已於S13完整手翻，復用現有實作並接通初始化。
- 性格抽選使用真實catalog COLOR；保留重抽累積、多個前置同型角色計數與清色／暫存副作用。
- TDD：初始61案失敗；最終71個新案，移除1個舊停止案；定向231 passed、1 warning。
- 主代理完整pytest：3633 passed、1 warning；標準500局與S53逐seed完整紀錄一致，catalog失敗0。
- 無新增UNVERIFIED／DEVIATION；10批退出碼、seed全集、log／JSONL與編碼／唯讀範圍檢查通過。
