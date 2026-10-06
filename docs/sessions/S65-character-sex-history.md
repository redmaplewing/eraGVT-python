# S65：W02 共用性別編輯

## 完整成果
- 承接S64，完成共用character_editor尚未接通的[0]FIRSTSETTING_CHARA_SEX，屬W02／B02、B08。
- 依原文實作各可達分支、顯示／輸入／返回／確認與重入，接回現有主選單及四呼叫者，不能只新增無呼叫者模組。
- 隱藏入口、固有／醫療限制與已存在的性別／身體設定相依均按原文；後續TS生命週期仍W03，不把編輯端完成宣稱全流程完成。
- [8]原有停止保留：最小查證已證實生成器直接依8／12／16歲門檻及學生類型產生性經驗數值（`ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA_EXP.ERB@FIRSTSETTING_CHARA_EXP:582–593、797–800`）；涉及未成年分支不新增實作，不自行加成人限制，不當成原作未完成。
- 其餘SIZE_SETTING、主製作初始狀態／人數及子供獨立流程仍留W02；不改工作包順序。

## 查證與實作
- 依序讀AGENTS、STATUS、PLAN及本規格，僅查本函式、呼叫者及必要依賴；不掃整包原作／口上。
- 原作附檔案@函式:行號，引擎附reference完整路徑:行號；先讀懂意圖再寫原生Python，不新增直譯器。
- 從原文推導table-driven前態與expected，先紅後綠；涵蓋循環／上限／互斥／取消／確認、未顯示但允許的手輸與共享RESULT(S)，只有原文有的規則才做。
- 清楚分辨暫存預覽、立即寫入、確認後重算；不能自行添加回滾或把重入變成重複初始化。
- 隨機性走注入RNG；固定文字優先抽取，不新增敘事情節。
- 全部新測試與瀏覽器使用全新人工25歲定義，沿fresh-adult-25-v1；不修改原作、產品年齡規則或既存角色年齡。
- 依既有年齡來源結論，不重複盤查；疑慮限實際待改函式與輸出。一般可獨立邏輯持續完成。
- 原作未完成保留，原作錯誤／查不到的行為不可自行補完，依AGENTS記錄必要UNVERIFIED／DEVIATION。

## 驗收與交付
- 新功能先紅後綠，少量GameSession/Web邊界，確認修改後可重入且完成至SHOP。
- 提供tmp/s65/browser_fixture.py、全新25歲人工資料、臨時存檔、Null敘事及只讀一般數值端點；全員年齡契約沿既有fixture。
- 若需要catalog副作用，測試使用實際catalog；Null瀏覽器只能證明該人工範圍，不用常數0冒充catalog失敗實測。
- 定向通過後通知產品凍結，給瀏覽器啟動命令與按鍵路徑；主代理獨立跑全pytest、真瀏覽器及正式500，子代理不要重複跑全套／500。
- 正式500沿tools/sim_adult.py，default／tokusou各seed0–249、max-shop200、actions101–108，每50局前景分批；與tmp/s64/adult25-v1逐seed完整JSON比較。
- 子代理更新PLAYABILITY及相關wiki／必要bridge；STATUS／PLAN由主代理收口。文件繁體中文、LF／UTF-8無BOM。
- 子代理不commit/push；核對git status/diff與source/reference未動，回報做了什麼／已查證依據／需要使用者決定。

## 驗收結果
- 主代理全pytest：`4169 passed, 1 warning in 251.70s (0:04:11)`；新33案，定向回歸99案通過。
- 25歲真瀏覽器四種組合、否決／確認、退點與重入、完成至SHOP均通過；重入完整數值一致、瀏覽器錯誤0。
- 正式500：default247上限／3回標題，tokusou250上限；catalog失敗0、fixture停止0；十批退出0，逐seed完整JSON與S64相同。
- source/reference未動，LF／UTF-8無BOM及diff檢查通過；性別功能無新增UNVERIFIED／DEVIATION。[8]範圍阻塞仍保留，不宣稱W02完成。
