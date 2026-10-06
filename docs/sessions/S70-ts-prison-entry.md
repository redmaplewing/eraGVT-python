# S70：W03 三種TS轉換與幽閉首次事件輸入

## 完整成果與佇列
- W02一般入口已接通；[8]既有具體範圍阻塞維持，W02不標完成。依PLAN阻塞時接可獨立工作的規則，開始下一包W03的既有角色轉換。
- 手寫ERB/ヒロイン関連/TRANS_SEX.ERB@TS_MtoF:4–173、@TS_FtoM:179–346、@TS_NORMAL:352–925，接幽閉首次事件真實呼叫及catalog三個hook。
- 三函式只操作既有角色與兩形態；不依賴[8]或新增年齡／經歷生成。保留原逐題外貌選擇，不插入共用SIZE_SETTING或自動代按。
- 保留TRANSFORM、衣裝／尺寸計算、選項／無效值重試、既有狀態復原、TARGET及RESULT(S)殘值次序。TS_NORMAL原女性錯誤返回在TARGET恢復之前，照原文保留並明記，不能自行修正。
- 將turnend.event_turnend→prison.event.prison→prison_event→_msg_first真正串為可等待；catalog沿既有run_event_gen／generator hook，Null fallback按同一分派呼叫同一原生實作。
- 不把原作TS流程搬進catalog當捷徑，不擴充口上直譯器或生成新敘事。
- 原作MESSAGE_PRISON.ERB@MESSAGE_PRISON_PRISENTENCE_FIRST:97／113／150是本次呼叫；NINSIN_FLAG／NINSIN_TS_FIX另留同W03後續，SUPART_BLOOD仍W05，不宣稱全TS生命週期完成。

## 查證與測試
- 依序讀AGENTS、STATUS、PLAN、本規格；只查上述原函式、實際呼叫鏈與必要依賴；引擎語意附reference精確路徑與行號。
- table-driven先紅後綠，從ERB推導前態／expected；亂數走注入RNG。比對兩形態數值、尺寸、外貌選項、RETURN／TARGET／RESULT(S)及變身前後狀態。
- 全部新定向資料為全新25歲人工角色，兩形態預先25歲；原作複製年齡仍照原文，不修改產品年齡範圍、不新增成人限制、不執行／測試未成年性內容。
- 至少驗真實首次事件呼叫鏈及catalog hook的yield傳遞；不能只有新模組孤立單元測試。原有同步呼叫者必須逐一核對，沒有輸入時也要正確耗盡generator。
- 既有測試若因真正等待需加輸入，依原提示調整driver，不改原expected迎合實作；不使用假generator冒充產品路徑。
- 已查證年齡來源與[8]範圍不重查。若有新增原作bug／不可分割依賴，記錄具體證據；可獨立完成部分持續推進。

## 驗收與收尾
- 提供tmp/s70/browser_fixture.py：fresh-adult-25-v1、Null敘事、臨時存檔，進真實首次事件的TS邊界，三種形態各有前態；只讀一般狀態／外貌／TARGET與年齡端點。
- 真瀏覽器驗逐題外貌選擇、保留原值、無效重試、完成後續行與原變身狀態復原；明寫人工函式邊界驗收，不稱自然幽閉全流程通過。
- 凍結後由主代理跑全pytest、真瀏覽器及正式500，default／tokusou各seed0–249、max-shop200、actions101–108，每50局前景一批，與S69完整JSON及停止原因比對。子代理不啟動500。
- 更新相關wiki、PLAYABILITY及必要bridge，精確保留W02阻塞／W03未完呼叫者與其他包；STATUS／PLAN由主代理收口。
- 文件繁體中文、LF／UTF-8無BOM，source／reference唯讀。凍結後核對diff並回報成果／依據／裁決，不commit/push。
