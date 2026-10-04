# S45：SHOP設施擴充

## 目標與範圍
- 使用者授權接通SHOP [150]設施擴充；完成本階段後停止。
- 查原作選單與呼叫鏈，手翻購買條件、費用、升級／持有狀態、確認取消及返回。
- 核對設施效果的實際呼叫者，既有系統優先共用；本入口必要但未接通的效果須完成或回報阻礙。
- source/、reference/永遠唯讀；既有裁決保持。

## 實作要求
- 讀AGENTS、STATUS、PLAN、本規格，再按需查原作與相關wiki。
- 測試先行，table-driven expected由ERB推導，先紅後綠；遊戲亂數注入。
- 原作引用檔案@函式:行號；引擎語意查reference並附行號。
- 不預設原作有確認／升級機制，依實際原文決定；金額、邊界及持有判斷不可猜。
- 接GameSession，涵蓋不足／恰足、重複購入、資格、無效值、取消與返回。
- 用代表性定向案例驗證購入後效果，不能只驗證旗標有改。
- 純顯示若會被返回SHOP的LB遮掉，依原作PRINTW位置局部等待，沿用S44已查證模式。
- 文字優先抽取，不新增敘事、不做ERB直譯器；新模組有實際呼叫者。
- 未知標UNVERIFIED並記錄；偏離不得自行裁決，重大問題先回報主代理。
- 文件繁體中文，UTF-8無BOM、LF；STATUS≤120行，本規格≤60行。

## 驗收與收尾
- 產品／測試固定通知主代理獨立完整pytest；目前基準2875 passed。
- 標準模擬default／tokusou各seed0–249、max-shop200、actions101–108。
- 10個獨立前景exec批次各50局，可平行；python -X utf8 -u、--verbose。
- log／JSONL／exit與audit留tmp/s45，核對seed全集、退出碼及逐局結果。
- 比較tmp/s44基準：default246上限／4標題、tokusou250上限、catalog失敗0。
- 更新STATUS及相關wiki；新未知／偏離才更新unresolved／deviations。
- 子agent不commit／push；主代理審查、驗收唯讀目錄與編碼後提交推main。
- 最後回報做了什麼／已查證的依據／需要使用者決定。
