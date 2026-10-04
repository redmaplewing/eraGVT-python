# S40：SHOP衣裝購入

## 目標與範圍
- 使用者同意接通SHOP [120] 衣裝購入，本階段完成後停止。
- 沿用S39衣裝瀏覽與設定，手翻原作購買入口、商品條件、付款與持有狀態。
- 接通選取、確認、金額不足、已持有、分類／翻頁／篩選與返回SHOP。
- 原文若沒有額外確認，不自行加設；所有狀態與殘值照原作。
- 不擴展其他獨立SHOP系統；source/、reference/永遠唯讀。

## 實作要求
- 依序讀AGENTS、STATUS、PLAN與本規格，按需讀衣裝wiki與局部原作。
- 測試先行，table-driven expected由ERB推導，不由實作反推。
- 規則原生Python手寫；資料與原文文字沿用抽取，不做直譯器捷徑。
- 引用原作檔案@函式:行號、引擎reference檔案:行號。
- 驗證實際GameSession：購入→返回SHOP→衣裝設定可選取購入物品。
- 覆蓋價格邊界、不可購買物品、重複輸入、購買後列表／頁碼更新及RESULT(S)。
- 新未知或偏離依規則記錄，既有使用者裁決維持。
- 文件繁體中文，LF、UTF-8無BOM。

## 驗收與收尾
- 產品與測試固定後通知主代理，主代理獨立跑完整pytest。
- 標準模擬：default／tokusou各seed0–249、max-shop200、actions101–108。
- 每50局前景批次，python -X utf8 -u、--verbose，保留log／JSONL／exit。
- 與S39逐局比較：default246上限／4回標題、tokusou250上限、catalog失敗0。
- 核對10批退出碼、seed全集與log／JSONL一致；產物留tmp/s40/。
- 標準模擬不操作購買，需另有實際入口的定向測試。
- 更新STATUS（≤120行）與相關wiki；有新增事項才更新unresolved／deviations。
- 子agent不commit／push；主代理核對diff、唯讀目錄、編碼後commit並推main。
- 最後回報三段：做了什麼／已查證的依據／需要使用者決定。
