# S43：SHOP追加招募

## 目標與範圍
- 使用者授權接通SHOP [180] TSUIKAYOUSEI_NORMAL；完成本階段後停止。
- 原作查證：[180]只新增角色且無費用；[169]名簿／[170]引退是獨立入口，本階段不擴張。
- 手翻角色加入、資格、取消及返回；特徵選單依原作等待玩家選擇。
- 沿用既有狀態／角色製作／引退實作，不新增無實際呼叫者的模組。
- source/、reference/唯讀；醫療室AMPUTEE提示截斷裁決維持。

## 實作要求
- 依序讀AGENTS、STATUS、PLAN、本規格，按需讀相關wiki與原作局部。
- 先查完整呼叫鏈與狀態結果，確認名稱是否真的包含主動引退選單，不憑名稱假設。
- 測試先行，table-driven expected由ERB推導，先紅後綠；亂數注入。
- 原作引用檔案@函式:行號；引擎語意查reference並附行號。
- 必要玩家選擇等待輸入；暫略角色製作UI只能沿原作不改設定直接確認路徑。
- 接通GameSession入口，涵蓋資格邊界、取消、無費用／負資金亦可加入、角色索引與RESULT殘值。
- 不自行修原作怪處；未知與偏離標記並記錄，重大決策交主代理。
- 字串優先抽取；不擴寫敘事或採ERB直譯器捷徑。
- 文件繁體中文，LF、UTF-8無BOM；規格≤60行、STATUS≤120行。

## 驗收與收尾
- 產品／測試固定後通知主代理獨立跑完整pytest；目前基準2734 passed。
- 標準模擬default／tokusou各seed0–249、max-shop200、actions101–108。
- 10個獨立前景exec批次各50局，可平行；python -X utf8 -u，--verbose。
- log／JSONL／exit留tmp/s43；核對seed全集、退出碼及逐局結果。
- 比較tmp/s42-truncate基準：default246上限／4標題、tokusou250上限、catalog失敗0。
- 更新STATUS及相關wiki；有新未知／偏離才更新unresolved／deviations。
- 子agent不得commit／push；主代理驗收範圍、唯讀目錄與編碼後提交推main。
- 最後回報做了什麼／已查證的依據／需要使用者決定。
