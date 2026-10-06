# S63：W02 種族、變身能力與基礎點編輯

## 完整成果
- 承接S62，完成共用角色編輯[4]FIRSTSETTING_CHARA_SYUZOKU、[10]FIRSTSETTING_CHARA_TRANSABILITY、[23]FIRSTSETTING_STATUS_BONUS，屬W02／B02、B08。
- 三個選單的全部可選條件、數值／旗標連動、原作解鎖、返回／確認／重入均依原文；原作未改設定時的結果必須一致。
- 接回開局／招募／醫療／引繼的現有共用入口；沿用原作固有角色限制與呼叫端傳入的獎勵，不自動代按。
- SIZE_SETTING其餘操作、性別／經歷／CSV及主製作初始狀態／人數仍屬W02後續，不宣稱整包完成。
- W02完成編輯與可用狀態的確認；新選項產生的TS／特殊裝備生命週期仍依PLAN交W03，保留其明確停止，不偽裝全流程可玩。

## 查證與實作
- 依序讀AGENTS、STATUS、PLAN、本規格；只查三個函式、呼叫者與必要原作／引擎依賴，不掃整包repo或口上。
- 原作引用檔案@函式:行號，引擎引用reference完整路徑:行號；讀懂意圖後手寫Python，不新增ERB直譯器。
- 從ERB推導table-driven expected與前態，先紅後綠；不得以Python輸出反推expected。
- 特別核對種族互斥、能力開關／重抽、原作獎勵點扣還／上限／重入、CSV基礎值與TALENT／CFLAG／BASE／MAXBASE的先後順序。
- RNG一律注入，保留TARGET／RESULT(S)／共享暫存副作用；固定文字優先抽取。
- 全新25歲人工定義用於本次數值／選單驗證，產品年齡規則不變，不新增敘事情節；沿用既有年齡查證，不重查或重複派工。
- 原作bug／無依據部分不能自行修正或猜測；依AGENTS一次記錄具體來源與受影響分支，能獨立做的繼續。

## 驗收與交付
- 定向覆蓋所有選項、非法值、解鎖／固有角色限制、點數邊界、未改設定、修改／返回／重入與原作結果殘值。
- 少量真GameSession邊界案例，確認共用入口與獎勵傳遞；不做未接入的模組。
- 提供tmp/s63/browser_fixture.py：fresh-adult-25-v1、臨時存檔、Null敘事、只含一般數值的只讀狀態端點，主代理操作真瀏覽器至SHOP。
- 子代理定向通過即通知產品凍結，給啟動命令／具體按鍵／狀態端點；主代理跑全pytest、正式500與真瀏覽器，避免重跑耗時驗收。
- 正式500沿用tools/sim_adult.py：default／tokusou各seed0–249、max-shop200、actions101–108，每50局前景分批。
- 比較tmp/s62/adult25-v1逐seed完整JSON，分開記錄遊戲停止、catalog失敗與fixture停止。
- 子代理更新PLAYABILITY、相關wiki與必要bridge；STATUS／PLAN由主代理最後收口。source/reference唯讀，檔案LF／UTF-8無BOM。
- 子代理不commit/push；主代理獨立驗收並檢查實際diff後，明確stage並推main。最後回報成果／依據／裁決。

## 最終驗收
- 新增105案；主代理最終全pytest：`4101 passed, 1 warning in 258.30s (0:04:18)`。
- 真瀏覽器以25歲人工資料／Null敘事驗三選單至SHOP；重入完整數值一致、WAIT按鈕／Enter、警察第二級名稱／降級退款皆通過。
- 原作FINALIZE會分配剩餘點數，SHOP後態不可沿用編輯前態斷言；來源與截圖／數值紀錄見[數值編輯](../wiki/era/character-build.md)。
- 正式500：default247上限／3標題、tokusou250上限；catalog失敗0／fixture停止0，十批退出0，逐seed完整JSON與S62一致。
- 數值流程凍結後執行500；期間只修正新選單名稱／字形，固定模擬策略不進該選單；修正後另完成全pytest及真瀏覽器複驗。
- source/reference未動，LF／UTF-8無BOM；無新增UNVERIFIED／DEVIATION，其餘W02及既有W07項仍保留。
