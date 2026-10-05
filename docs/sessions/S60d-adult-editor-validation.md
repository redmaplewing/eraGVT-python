# S60d：成年人工前態的角色編輯一般 UI 驗證

- 承接 W02／B02、B08；保留未提交 S60，不宣稱整包已驗收。
- 使用者指定以成年參數重新驗證；建立全新人工角色，實年齡與外見年齡皆 25。
- 初批驗姓名、稱呼、子頁返回、主頁確認與重入；後續一般子選單依下方接續授權驗證，不新增性屬性或敘事內容。
- 不使用先前 11 歲角色、不讀寫使用者存檔、不改原作年齡生成規則。
- 以 tmp 下測試啟動器載入真實 create_app、GameSession、模板及 character_editor。
- 人工前態直接設定既有初始化旗標 CFLAG:240；不執行開局／角色初始化。
- 使用 NullNarrationService；必要一般欄位依既有資料結構設定。
- 原文依據沿用 S60／S60c 已核對的 FIRSTSETTING_CHARA_MAIN、NAME、CALLNAME。
- 驗證前後核對兩個年齡欄位；明確區分人工前態與自然流程驗收。
- 必要的一般功能修正須按原文先紅後綠；無錯誤則不為測試修改產品碼。
- 父代理操作真瀏覽器；子代理先交付可跑啟動器與確切步驟。
- 本次不跑全遊戲模擬，不將成年樣本推論為全年齡路徑已通過。
- 更新 STATUS 的實際驗收範圍；source／reference 唯讀；不 commit／push。

## 定向結果與重現

- 啟動：`python tmp/s60d/adult_editor_fixture.py`，瀏覽器開 `http://127.0.0.1:8766/`。
- GET `/fixture/state` 回傳人工前態標記、姓名、稱呼、實年齡／外見年齡與確認次數。
- 三角色均為全新人工資料；BASE/MAXBASE:40、41皆25，CFLAG:240非0；CSV/Base.csv:22的42為無名稱欄。
- 選項順序：`1→3→99→Enter→99→2→99→99→1` 驗不改／返回／確認／重入。
- 修改順序：`1→1→姓→名→2→1→稱呼→99→1`，重入核對姓名與稱呼。
- 空名字順序：`1→1→姓→空字→Enter→名→99→1`，核對警告確認後仍可輸入。
- 只操作上述入口；頁尾返回標題是產品原有新局入口，不屬此人工前態測試。
- `python -m pytest -q tmp/s60d/test_adult_editor_fixture.py tests/test_character_name_neutral.py`：`9 passed, 1 warning in 1.86s`。
- 三條Web定向路徑皆核對每步BASE:40／41為25、RNG未變、模板200及最終姓名／稱呼；未修改產品程式。
- 父代理真瀏覽器8766：姓名改為「驗證成人」、稱呼改為「成年稱呼」；取消排列後清除子頁、返回主頁、99確認及重入均正常，重入保留兩值，年齡25。
- 父代理獨立定向：`9 passed, 1 warning in 1.85s`；全pytest／遊戲模擬未執行，不將此次樣本等同完整S60驗收。

## 接續驗收（使用者已授權）
- 沿用成年人工前態，補其餘已接入的一般子選單：一人稱、口上開關、變身姓名／稱呼／喊聲／自介、一般衣裝與武器自訂。
- 不執行敘事；衣裝使用一般服裝。所有參與測試角色為全新人工成年資料，不改產品年齡規則。
- 核對確認時ITEM還原、CSTR/TARGET/RESULT/RESULTS及RNG，並以人工成年生成依賴驗開局／招募／醫療／引繼到編輯器的呼叫契約；清楚區分人工依賴與自然流程。
- 已驗姓名／稱呼不重跑，除非相關產品修改；新增失敗先由原文推導expected後修正。
- 父代理獨立定向與真瀏覽器驗剩餘一般互動；未通過全回歸不宣稱整包S60完成，不提交未驗收產品。

## 接續定向成果
- `python -m pytest -q tmp/s60d/test_adult_editor_remaining.py`：`28 passed, 1 warning in 6.36s`。未修改產品碼；沒有以實作輸出反推expected，亦未執行舊有全年齡fixture或完整遊戲模擬。
- 同一Web啟動器已改人工前態為變身能力1、普通衣裝119與訓練劍；`/fixture/state`新增一人稱、口上／主觀、變身文字／旗標、衣裝、武器及TARGET，供真瀏覽器核對。
- 一人稱確認／取消再入、口上六選項／主觀開關四案、變身名／稱呼／喊聲／自介（空字、999保留、停用連動）、三欄普通衣裝取消／確認、三距離武器名／風格／取消均通過。只設定口上，未執行敘事。
- 普通衣裝選118ライダースーツ與308スパッツ；變身衣裝變更清EQUIP:600–699，取消保留；確認主頁還原ITEM、清SAVESTR:0–3，保留TARGET與RESULT(S)尾格；壓縮武器解碼清CSTR:15–17再入不覆蓋。手動編輯RNG不變，每步角色實／外見年齡均25。
- 入口契約：真實creation_menu的1／101與bonus傳遞；招募／醫療到真實editor並返回、醫療restricted=1；引繼真實選單→修練P先扣20加10→creation_menu→editor確認不重加。ADDCHARA、FINALIZE及引繼reset_data依需要替代成年人工依賴，不是自然完整流程。
- 依據：`ERB/SYSTEM/キャラメイキング関連/FIRSTSETTING_CHARA.ERB@FIRSTSETTING_CHARA_MAIN`、`@FIRSTSETTING_CHARA_KOJO`、`@FIRSTSETTING_CHARA_SELFCALL`；同目錄`FIRSTSETTING_CHARA_TRANSFORMATION.ERB@FIRSTSETTING_CHARA_TRANSAFTERNAME`／`@FIRSTSETTING_CHARA_TRANSAFTERCALLNAME`／`@FIRSTSETTING_CHARA_TRANSCALL`／`@FIRSTSETTING_CHARA_NANORI`。
- 衣裝／武器依據：`ERB/武器と衣装/衣装関連/CLOTH_WEAR.ERB@CLOTH_SETTING_OUTER`／`@CLOTH_SETTING_OUTER2`／`@CLOTH_SETTING_INNER`；`ERB/武器と衣装/武器カスタマイズ関連/WEAPON_CUSTOMIZE.ERB@SETTING_WEAPON_NAME`／`@SETTING_FSTYLE`、`WEAPON_ARCHIVE.ERB@DECODE_WEAPON_DATA`。各入口與殘值精確依據列於測試註解。
- 父代理獨立新增28案全綠；真瀏覽器完成一人稱、口上設定、四變身文字、三衣裝欄與近距離武器名／風格，99確認後重入保留值、年齡25。16欄預覽取消保留119，確認後改118；17=118、18=308。
- 全回歸、自然開局／招募／醫療／引繼、未移植子選單、舊PRINTW等待遷移均不算通過。此次沒有新增UNVERIFIED／DEVIATION。

## 四入口接續驗收
- 使用者要求年齡25；優先以原作支援的年齡指定欄位建立全新成年測試資料，讓真實INITIALIZE／FINALIZE運作。不得將此前未成年角色改年齡後重用。
- 前輪僅入口契約：本輪補真實生成與確認返回銜接，使用NullNarration、臨時存檔，不執行性敘事或子供／其他受限流程。
- 產品年齡生成規則與source/reference不改；若入口需要測試注入，精確列出替代點，不能稱完全自然開局。
- 先以小範圍API驗證四入口，提供父代理真實瀏覽器可操作的入口fixture；每個顯示點斷言實／外見年齡25。
- 僅修本輪發現的一般整合錯誤，原文expected先紅後綠；沿用本規格與STATUS，不新開階段。
- 四入口定向：`python -X utf8 -m pytest -q tmp/s60d/test_adult_entry_flows.py` → `5 passed, 1 warning in 2.67s`；真實ADDCHARA／INITIALIZE／FINALIZE／引繼reset_data均未替代，四入口到SHOP；引繼獎勵10點於編輯確認／重入保留、FINALIZE才分配。
- 啟動：`python -X utf8 tmp/s60d/adult_entry_fixture.py <entry>`；opening=8771、recruitment=8772、medical=8773、succession=8774；完整產品Web與模板，每次HTTP回應斷言所有角色BASE／MAXBASE:40、41皆25，`/fixture/state`供瀏覽器核對。
- 人工依賴：記憶體全新CharaDef(0/999)，BASE:40/41=25與CSTR:204/205/206="25"，普通服裝與變身能力；非開局入口以兩名真實生成成人建立人工SHOP前態（資金60000、招募旗標），引繼從succession_gen直接進入並回真實SHOP。臨時目錄、NullNarration；不是自然遊玩通關，不更動既有角色年齡或來源。
- 順序：開局`0,1,99,1,99,1000,0`；招募`180,1,99,1`；醫療`113,100,1,4,999,99,1,999`（4/999鎖定留主頁）；引繼`0,1,999,999,1,1,99,1000,0`。父真瀏覽器四入口全部回SHOP，開局確認重入、醫療4/999留在限制編輯器均正常；沒有新增產品修改／UNVERIFIED／DEVIATION，全回歸／500局未執行。
- 父獨立定向：`5 passed, 1 warning in 2.42s`。四個瀏覽器最終狀態皆4人（含管理員）、四年齡格全25；資金依序5000／60000／10000／1000。真實生成、確認與引繼重置未替代；既有產品變更仍待完整回歸與正式500局，不把本輪記為整包S60完成。
