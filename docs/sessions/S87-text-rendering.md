# S87：W07 共用文字輸出、排版與重繪

## 完整成果與範圍
- 接續W07，完成既有顯示偏離中的共用字型／PRINTLC欄寬、CLEARLINE重繪、DRAWLINEFORM、原作實用HTML子集及無效輸入暫時行；對應B03／B08／B09。
- 先查deviations既有原項與實際呼叫者，原作文字資料抽取／catalog沿用，不新增敘事或遊戲邏輯解譯捷徑。
- 依reference查證輸出緩衝、換行、字型／粗斜體、欄位計量、刪行與暫時行語意，不能把Web慣例當作引擎依據。
- 以原作實際使用範圍接回TextOutput、catalog及Web；保留字串／按鈕值／輸入種類、RESULT(S)、RNG及狀態副作用。
- 各角色設定／命名／衣裝／SHOP／戰鬥使用共用輸出者，重繪後不能留下可提交的舊選項；不得靠全面清掉敘事歷史避開重繪語意。
- 字型缺失、原字型像素與Web呈現如有不可等價處，先確認實際環境與來源，具體保留既有偏離或交裁決，不自行批准近似。
- COUNT、尚未遷移WAIT、catalog執行失敗處置仍屬W07後續成果，本階段不冒充W07結包。
- W02／W04已記錄阻塞不重查；一般功能以全新25歲人工資料驗證，不改產品年齡規則。

## 查證與測試
- 依序讀AGENTS、STATUS、PLAN、本規格及必要wiki；局部查ERB／reference並附檔案與函式行號。
- source-derived expected先紅後綠；挑代表邊界：部分行／換行／CLEARLINE、混合寬度／樣式／按鈕、字型狀態及HTML實際標記、無效值重繪。
- 不為每個字串或每個呼叫者新增鏡像測試；少量Web邊界案例驗真模板／樣式及輸入續行。
- 提供tmp/s87/browser_fixture.py，最少真UI路徑覆蓋長頁／重繪／混合文字與按鈕／設定前後；列人工前態、操作與expected。
- 產品、測試、fixture完全凍結後通知主代理，之後只收文件；子代理只跑定向，主代理獨立瀏覽器及一次全pytest。

## 分級驗證與收尾
- 預設共用顯示修正：定向＋必要真瀏覽器＋提交前一次全pytest；不是工作包完成，不因共用輸出檔名而跑500。
- 若查到會改RNG／排程／存讀等跨系統核心行為，先回報具體證據再調整驗證，避免無依據擴大。
- 更新deviations原項、PLAYABILITY及必要wiki，清楚分開已解與剩餘；新UNVERIFIED／DEVIATION照規則記錄。
- STATUS／PLAN留主代理收口。繁體中文、LF／UTF-8無BOM；source／reference唯讀；自查範圍、不commit/push，最後三段回報。
