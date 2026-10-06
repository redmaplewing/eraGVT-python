# S64：W02 共用角色模板CSV載入

## 完整成果
- 承接S63，完成共用角色編輯[999]的FIRSTSETTING_CHARA_LOADCSV及必要子流程，屬W02／B02、B08。
- 依原文完成候選顯示、選擇／取消、角色替換／確認／重入，接回真實共用character_editor，不能只寫資料載入工具。
- 釐清原作載入的資料來源與單位，沿實際CSV／ADDCHARA等語意；不預設成OS檔案選擇或自行發明上傳流程。
- 保留非固有／醫療入口限制、呼叫端獎勵參數與原作初始化／重置先後；開局／招募／醫療／引繼共用呼叫者均核對。
- 性別／經歷、SIZE_SETTING其餘操作與主製作初始狀態／人數仍在W02後續；不宣稱整包完成。

## 查證與實作
- 依序讀AGENTS、STATUS、PLAN及本規格；僅查本函式、呼叫者及必要資料／引擎依賴，不掃整包repo或口上。
- 原作附檔案@函式:行號，引擎附reference完整路徑:行號；已有csvbase、角色定義與新增／刪除語意優先沿用已查證實作。
- 從原文推導table-driven前態與expected，先紅後綠；不能從Python結果反推expected。
- 尤其核對角色索引、NO／TARGET／MASTER、共享RESULT(S)、替換前後欄位保留、RNG及獎勵呼叫次數；MAIN:322–332取消後仍加bonus*10，依明文保留，不額外加或減。
- 固定文字優先抽取；遊戲流程手寫Python，不新增ERB直譯器，也不動source/reference。
- 本次測試／真瀏覽器沿fresh-adult-25-v1全新人工定義，年齡25；如需外部CSV，以全新人工25歲檔做fixture，不改原作或產品年齡規則。
- 不新增敘事情節，沿既有年齡來源查證；有新疑慮限定指出實際函式與資料來源，不概括或反覆重查。
- 原作未完成保留；原作錯誤／依據不明不能自行補行為，按AGENTS記錄必要UNVERIFIED／DEVIATION。

## 驗收與交付
- 定向覆蓋所有候選／分頁／邊界（原文有的才做）、取消與重入、無效輸入、限制、獎勵／初始化及結果殘值。
- 少量真GameSession邊界；確認替換後真正回到共用編輯並能完成至SHOP。
- 提供tmp/s64/browser_fixture.py，使用25歲人工資料／臨時存檔／Null敘事及只讀一般數值端點；如有catalog則與Null範圍區分，不以常數失敗欄冒充實測。
- 子代理定向通過後通知產品凍結，給啟動命令／按鍵步驟；主代理獨立跑全pytest、真瀏覽器及正式500。
- 正式500沿tools/sim_adult.py：default／tokusou各seed0–249、max-shop200、actions101–108，每50局前景分批，逐seed完整JSON比較tmp/s63/adult25-v1。
- 子代理更新PLAYABILITY、相關wiki及必要bridge；STATUS／PLAN由主代理收口，避免巨型歷史紀錄。
- 子代理不commit/push；主代理核對實際diff、唯讀目錄、LF／UTF-8無BOM，明確stage再推main。最後三段回報成果／依據／裁決。

## 驗收結果
- 主代理全pytest：`4136 passed, 1 warning in 261.77s (0:04:21)`；新35案，含雙欄修正的先紅後綠3案。
- 25歲真瀏覽器已走完wiki所列路徑，數值／取消重入／WAIT／男性汎用至SHOP通過，瀏覽器錯誤0；人工7000／7001、Null敘事，不冒充自然通關。
- 正式500：default247上限／3回標題，tokusou250上限；catalog失敗0、fixture停止0；十批退出0、逐seed完整JSON與S63相同，見tmp/s64/adult25-v1/audit.json。
- source/reference未動，UTF-8無BOM／LF與diff檢查通過；COUNT沿既有W07偏離，無新增裁決。
