# S71：W03 妊娠狀態TS轉換與生命週期輸入接線

## 完整成果與範圍
- 工作包W03；驗收矩陣B04／B05／B08，只回填本次實測邊界，不宣稱整包或整列完成。
- NINSIN_FLAG／NINSIN_TS_FIX按原作呼叫S70既有TS_MtoF，逐題外貌選擇真正等待，完成後回原呼叫點續行。
- 原作ERB/ヒロイン関連/PREGNANT_SOURCE_NINSIN.ERB@NINSIN_FLAG:195–257、@NINSIN_TS_FIX:262–271；保留狀態判定、即時處理、訊息及返回順序。
- NINSIN_FLAG:248–256的女性／變身時ＴＳ>0／變身中／妊娠=4條件照原文；NINSIN_TS_FIX:263–270未變身分支不自行轉換。
- NINSIN_HANTEI、NINSIN_CHECK_AFTER及全部既有可達呼叫者傳遞generator，不新增同步耗盡輸入或自動選答捷徑。
- 戰後四路：ERB/ゲーム内_戦闘処理/BATTLE_TRAIN_AFTER.ERB@EVENTEND:204／252／300／393。
- 共用結算：TENTACLE_SYASEI_POINT→TENTACLE_SYASEI_CHECK→PALAM_UP→PALAM_CAL，以及sexcom._finish及實際命令／dispatcher。
- 原作ERB/ゲーム内_戦闘処理/TENTACLE_SYASEI.ERB@TENTACLE_SYASEI_POINT:306／326、@TENTACLE_SYASEI_CHECK:159／184／202、PALAM_UP.ERB@PALAM_UP:145、COMMON_PALAM_CAL.ERB@PALAM_CAL:24。
- 幽閉命令／routine、akuoti／turnend、yobai、seisan及其行動呼叫者完整續接；gather、lovesex、pastime、small_tentacle、battle.rape既有generator亦核對。
- tentacle_access_prison的NAME／PALAM_HOSEI同步getter保持可用；只有PRISON_ROUTINE需等待，不無差別把讀值改成generator。
- catalog NINSIN_HANTEI hook沿既有run_event_gen／input_fn；驗自由行動既有呼叫入口，不擴寫catalog或增加敘事。
- 不新增妊娠判定／年齡／經歷生成規則；W02[8]既有阻塞、SUPART_BLOOD(W05)及未移植裝備不納入。

## 查證與測試
- 依序讀AGENTS、STATUS、PLAN、本規格；精確搜尋先看總數，只查相關原函式、真實呼叫鏈與必要引擎語意，引用檔案@函式:行號／reference路徑:行號。
- table-driven從原文推導expected，先紅後綠；所有新前態為全新25歲人工角色、兩形態均預先25歲，不修改產品年齡規則。
- 不生成或摘錄露骨敘事；功能驗收以Null敘事及一般外貌選擇為主。既有[8]查證沿用，不重複盤點。
- 驗正常觸發、即時處理、未觸發、變身中／未變身／非TS／非女性分支，以及CHECK_AFTER妊娠=2的兩種配置與抽選後續。
- 驗無效輸入不提前續行、不重複先前狀態或RNG；完成後TARGET、RESULT(S)尾格、變身狀態與原後續順序一致。
- 新generator呼叫點不得被忽略；原有回傳值、共用RESULT寫入責任及動態分派保留。至少實測共用結算鏈與戰後實際入口，不能只測孤立TS函式。
- 原測試因generator需改driver時只調整呼叫／必要真實輸入，不改原expected迎合實作；有輸入的路徑不能以list()吞掉None。

## 驗收與收尾
- 提供tmp/s71/browser_fixture.py，以fresh-adult-25-v1／Null／臨時存檔進真實正常狀態入口與EVENTEND→CHECK_AFTER入口；只讀一般狀態、外貌、TARGET及年齡端點。
- 真瀏覽器走髮型／色彩選擇、無效重試及完成後續行；明記人工函式邊界，不稱自然戰鬥或整個生命週期通過。
- 子代理完成定向測試後凍結；主代理獨立全pytest、真瀏覽器、正式500局（兩入口各seed0–249、max-shop200、actions101–108、每50局前景一批），與S70逐seed完整JSON比較。
- 更新必要既有wiki／PLAYABILITY／bridge；STATUS／PLAN由主代理收口。無新增未決或偏離時不製造條目。
- 繁體中文、LF／UTF-8無BOM，source／reference唯讀；核對git status／diff，回報成果／依據／裁決，不commit/push。
