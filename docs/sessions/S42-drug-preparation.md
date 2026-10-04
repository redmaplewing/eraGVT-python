# S42：SHOP醫療室（DRUG_PREPARATION）

## 目標與範圍
- 使用者同意接通SHOP [113] DRUG_PREPARATION，本階段完成後停止。
- 經查證此入口沒有配方製作系統；手翻醫療室治療、檢查／手術、藥品購買／處方、機器人維修／加入與返回SHOP。
- 依原作完成此入口必要子流程，沿用既有資料與道具系統，不擴展獨立系統。
- source/、reference/永遠唯讀；既有裁決維持，不自行改原作怪處。
- 使用者追加要求：[51]須全盤查證作者意圖後修正原作bug，不以停止或慣例取消代替判斷。
- 查明停用分支、提示文意、跳轉與依賴；區分已證事實與推論，不復活刻意停用的功能。

## 實作要求
- 依序讀AGENTS、STATUS、PLAN、本規格，再按需查原作與相關wiki。
- 測試先行，table-driven expected由ERB推導，不由Python輸出反推。
- 遊戲規則原生Python手寫，資料／原文文字優先沿用抽取，不做直譯器。
- 原作檔案@函式:行號、引擎reference檔案:行號須逐項實核。
- RNG注入；輸入、取消、無效選項及RESULT／RESULTS照原作。
- 覆蓋治療效果／消耗、資源不足／恰足、購買數量／處方邊界、重複操作與返回。
- 以實際GameSession驗證SHOP入口、購買後庫存、手術確認及返回。
- 同時核對PRINT／PRINTPLAIN按鈕分段，避免狀態文字誤成可點選項。
- 新未知／偏離依規則回報；沿用既有偏離時明記本入口影響。
- 文件繁體中文，LF、UTF-8無BOM。
- 2026-10-04追加授權：依查證意圖修復[51]確認死循環；0照原手術、1拒絕返回、其他值重讀。
  保留隱藏入口與作者停用的NPC／AMPUTEE；文件區分原文事實與修復推論。

## 驗收與收尾
- 完成所有必要產品／測試／顯示邊界核對後固定，主代理獨立完整pytest。
- 標準模擬default／tokusou各seed0–249、max-shop200、actions101–108。
- 10個獨立exec前景批次各50局，可平行；不使用背景job或串行大迴圈。
- python -X utf8 -u、--verbose，log／JSONL／exit留tmp/s42/。
- 核對退出碼、seed全集、log／JSONL，與S41完整逐局結果比較。
- S41基準：default246上限／4回標題、tokusou250上限、catalog失敗0。
- 標準模擬不操作本選單，另以定向案例覆蓋功能。
- [51]追加修復採先紅後綠定向測試＋主代理全套pytest；既有500局不操作此分支，毋須重跑。
- 更新STATUS（≤120行）及wiki；有新增事項才更新unresolved／deviations。
- 子agent不commit／push；主代理驗收diff、編碼、唯讀目錄後commit並推main。
- 最後回報：做了什麼／已查證的依據／需要使用者決定。
