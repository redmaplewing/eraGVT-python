# S89：W07 衣裝／武器與共用選取的 COUNT 同步

## 完整成果與範圍
- 接續S88同一COUNT工作項，完成count wiki的衣裝63行及汎用／武器5行群組之實際可達原生邊界；搜尋行不等同功能缺口。
- 依共用CUSTOM_NUM、COPY／SAVE／DRAW、外衣slot及武器字串／選取呼叫鏈收斂，原作未完成／停用範圍保留並附來源，不另造行為。
- 沿用GameState.count與既有catalog／JSON v4，不再建立第二份COUNT或改版本；FOR LOCAL／CCOUNT不得誤寫COUNT。
- 依原作確定開始、每次本體、NEXT／BREAK／RETURN及CALL覆寫的時序；可觀察終值與中途被呼叫者讀值都要正確，不只在函式尾補常數。
- 手寫原生Python，禁止用ERB執行來代替遊戲邏輯；不新增敘事，既有W02／W04受限分支不重查。
- 攻擊／ABL／狀態／製作／SHOP／事件與其他戰鬥COUNT仍列原偏離；不把本群組完成稱全作COUNT完成。

## 查證與測試
- 讀AGENTS、STATUS、PLAN、本規格及wiki/python/count.md；沿已查明引擎規則，新增疑義才局部查reference。
- 全域搜尋先計數再讀目標；引用原作檔案@函式:行號、引擎reference檔案:行號。
- 來源推導table-driven expected先紅後綠，覆蓋共用入口、正常／提早退出、跨CALL與存讀後可見殘值；不要為每個等價參數重複鏡像測試。
- 子代理只跑受影響定向測試；提供tmp/s89/browser_fixture.py，使用全新25歲人工資料或中性catalog，最少真實衣裝／武器UI操作驗收。
- 產品／測試／fixture凍結後通知主代理；主代理獨立diff、真瀏覽器及提交前一次全pytest，文件後補沿用結果。

## 分級驗證與收尾
- 預設局部COUNT同步：定向＋必要真瀏覽器＋一次全pytest；不改已建立存讀格式、不結W07，單純已保存欄位的局部終值改變不自動跑500。
- 若發現COUNT覆寫會改跨系統開局／排程／共用RNG或存讀控制流，先列具體消費來源與影響再決定擴大；不可用共用檔名作理由。
- 更新count wiki群組與deviations既有原項，對未接／不可達／catalog已承接分開；新未決依規則回填，不擅自裁決。
- STATUS／PLAN交主代理收口；LF／UTF-8無BOM、繁體中文、唯讀目錄未動；不commit/push，最後三段回報。
