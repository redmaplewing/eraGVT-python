# S39：SHOP衣裝設定

## 目標與範圍
- 使用者同意上一階段建議，接通SHOP [112] 衣裝設定，完成後停止。
- 依原作手翻選角、衣裝／裝備子選單、條件檢查、變更與返回SHOP流程。
- 按實際依賴接通必要的資料與顯示，沿用既有戰鬥衣裝模型。
- 必要前置含57種衣裝自訂、共用自訂、變身部件及其戰鬥補正。
- 不擴展其他獨立SHOP子系統；必要前置若太大先回報，不自行換路徑。
- 既有原文資料優先抽取或沿用catalog，不新增情節或規則。

## 實作要求
- 依序讀AGENTS、STATUS、PLAN及本規格，再按需查原作與相關wiki。
- 由ERB推導table-driven測試，先紅後綠；遊戲規則手寫Python。
- 原作引用檔案@函式:行號；引擎行為查reference並附行號。
- 選項可用條件、持有品、價格、裝備欄位與效果依原作，不能猜測。
- 輸入等待、取消、無效輸入、返回路徑與RESULT／RESULTS殘值照原作。
- RNG透過注入物件；新模組接實際SHOP入口，補GameSession代表整合。
- source/、reference/永遠唯讀；既有裁決維持，新未知／偏離須回報。
- 文件繁體中文，檔案LF、UTF-8無BOM。

## 驗收與收尾
- 程式與測試固定後，完整pytest及標準500局模擬。
- 預設／tokusou各seed0–249、max-shop200、actions101–108，各50局前景批次。
- 使用python -X utf8 -u及--verbose，保留log、JSONL、exit，核對seed全集。
- S38基準：預設246上限／4回標題；tokusou250上限；catalog失敗0。
- 標準模擬未必操作衣裝選單，另以定向案例驗證實際SHOP操作及裝備狀態。
- 更新STATUS（≤120行）、相關wiki；有新增事項才更新unresolved／deviations。
- 確認唯讀目錄未動、diff與編碼檢查通過。
- 子agent不commit／push；主agent獨立驗收後commit並推上main。
- 回報：做了什麼／已查證的依據／需要使用者決定。
