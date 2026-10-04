# S44：SHOP引退名簿／主動引退

## 目標與範圍
- 使用者授權接通SHOP [169] CHAR_INTAI_LIST與[170] CHARA_INTAI；完成本階段後停止。
- 查原作完整入口與必要子流程，手翻名簿顯示、引退資格、確認、取消、資料處理與返回。
- 既有自動引退、存檔、角色索引與相關紀錄依原作核對，優先共用既有實作。
- source/、reference/永遠唯讀；既有裁決包含醫療室未完成支線截斷不變。

## 實作要求
- 讀AGENTS、STATUS、PLAN、本規格，再按需查原作與相關wiki。
- 先查明實際語意與呼叫鏈，不憑名稱推定角色刪除或紀錄規則。
- 測試先行，table-driven expected由ERB推導，先紅後綠；RNG注入。
- 原作引用檔案@函式:行號；引擎刪除／排序／RESULT等行為查reference並附行號。
- 真實選擇等待輸入；無效值、取消、名簿空白／多筆、資格與索引邊界逐項覆蓋。
- 接到GameSession；驗證名簿、引退與返回後角色／目標／紀錄一致，少量存讀檔邊界測試。
- 名簿／報告PRINTW依原作局部等待Enter，避免下一次LB遮掉；等待不寫RESULT／RESULTS，最後確認後才刪除角色。
- 文字優先抽取，不新增敘事，不做ERB直譯器；新模組必須有實際呼叫者。
- 無法查明標UNVERIFIED並記錄；任何偏離不得自行裁決，重大問題交主代理。
- 文件繁體中文，LF、UTF-8無BOM；STATUS≤120行，本規格≤60行。

## 驗收與收尾
- 產品／測試固定通知主代理獨立完整pytest；目前基準2773 passed。
- 標準模擬default／tokusou各seed0–249、max-shop200、actions101–108。
- 10個獨立前景exec批次各50局，可平行；python -X utf8 -u、--verbose。
- log／JSONL／exit與audit留tmp/s44，核對seed全集、退出碼及逐局結果。
- 比較tmp/s43基準：default246上限／4標題，tokusou250上限，catalog失敗0。
- 更新STATUS及相關wiki；有新未知／偏離才更新unresolved／deviations。
- 子agent不commit／push；主代理審查、驗收唯讀目錄與編碼後提交推main。
- 最後回報做了什麼／已查證的依據／需要使用者決定。
