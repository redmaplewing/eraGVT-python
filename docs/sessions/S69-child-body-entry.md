# S69：W02 子供身體編輯的實際收尾入口

## 完整成果
- 承接S68，解除ADD_CHILD的SIZE_SETTING預設代按；接既有body_editor.size_setting，不新增共用角色主選單。
- 僅將原作ADD_CHILD:1075–1107對應尾段抽為被ADD_CHILD實際呼叫的原生generator；在原位置yield from，不另造替身流程。
- 保留CFLAG34判斷／GENERATE_BODYLINE、身體編輯、母子RECOVER_TO_PARTY、清224、CHECK_ALL_RELATION與TARGET／RESULT(S)的原次序。
- 不修改前段出生／生成／固定年齡、經歷或敘事；S65[8]原有具體範圍阻塞維持。一般身體編輯器沿S67成果，不重新分類已查證欄位。

## 查證與測試
- 讀AGENTS、STATUS、PLAN及本規格；局部查ERB/ヒロイン関連/PREGNANT_CHILD_BIRTH.ERB@ADD_CHILD:1075–1107及實際收尾呼叫，必要引擎行為附精確引用。
- table-driven先紅後綠，expected取原文，驗等待真實輸入、一般欄位編輯／99確認、原分支返回、TARGET及共用結果殘值、RNG次序。
- 新測試用全新25歲人工角色；尾段有真實產品呼叫者，不用未接線的測試專用generator或產品年齡限制。
- 既有回歸只補真實身體確認99，不以Python輸出改expected；移除size_setting_default前先查全部實際使用者。
- 不必重新查年齡來源。已知前段原作固定年齡生成使全程25歲的完整ADD_CHILD驗收不可成立；不事後改齡冒充同一路徑。

## 瀏覽器與收尾
- 提供tmp/s69/browser_fixture.py：fresh-adult-25-v1、Null敘事、臨時存檔，直接進上述實際產品尾段，與ADD_CHILD同一實作。
- 驗一般外貌／文字欄位、確認、原收尾及TARGET還原；以只讀端點核對25歲、所改一般欄位及收尾狀態，至少涵蓋一般返回與原作育兒收尾分支。
- 明寫『ADD_CHILD尾段函式邊界驗收』；不是完整子供加入、自然流程或B05整列通過。不執行／測試未成年性內容。
- 凍結後主代理全pytest、真瀏覽器及正式500；default／tokusou各seed0–249、max-shop200、actions101–108，每50局前景一批，與S68完整JSON比較。子代理不啟動500。
- 更新相關wiki、PLAYABILITY及既有偏離的剩餘範圍；不把局部完成寫成W02完成。STATUS／PLAN由主代理收口。
- 文件繁體中文、LF／UTF-8無BOM，source／reference唯讀。不commit/push；核對diff，回報成果／依據／裁決。
