# S41：SHOP角色強化

## 目標與範圍
- 使用者同意接通SHOP [111] CHARA_POWERUP，本階段完成後停止。
- 手翻角色選取、強化選單、條件／費用／上限、狀態更新與返回SHOP。
- 按原作實際依賴完成必要子流程，沿用既有能力與戰鬥資料模型。
- 不擴展其他獨立SHOP系統；source/、reference/永遠唯讀。
- 沿用既有偏離時明確記錄本入口的影響，不宣稱完全等同原作。

## 實作要求
- 依序讀AGENTS、STATUS、PLAN、本規格，按需查相關wiki及局部原文。
- 測試先行，table-driven expected由ERB推導，不由Python輸出反推。
- 規則原生Python手寫，文字／資料優先沿用抽取；不做直譯器捷徑。
- 引用原作檔案@函式:行號；引擎reference檔案:行號須實際核對。
- RNG注入；RESULT／RESULTS、輸入等待、取消、無效輸入照原作。
- 覆蓋角色資格、強化前後狀態、資源不足、恰足、上限與重複操作。
- 實際GameSession驗證SHOP入口、強化、返回及後續狀態可見。
- 新未知／偏離依規則回報，不自行改原作怪處或裁決既有待決事項。
- 文件繁體中文，LF、UTF-8無BOM。

## 驗收與收尾
- 集中完成產品／測試／邊界核對並固定，再通知主代理跑獨立完整pytest。
- 標準模擬default／tokusou各seed0–249、max-shop200、actions101–108。
- 每50局前景批次，python -X utf8 -u、--verbose；log／JSONL／exit留tmp/s41/。
- 核對10批exit0、seed全集、log／JSONL；與S40完整逐局結果比較。
- S40基準：default246上限／4回標題、tokusou250上限、catalog失敗0。
- 標準模擬不操作強化選單，另以定向案例驗證本功能。
- 更新STATUS（≤120行）、相關wiki；有新增事項才更新unresolved／deviations。
- 子agent不commit／push；主代理驗收diff、編碼與唯讀目錄後commit並推main。
- 最後回報：做了什麼／已查證的依據／需要使用者決定。
