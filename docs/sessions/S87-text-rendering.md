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

## 子代理交付證據
- 新增18案；初始9失敗／3通過，CLEARLINE原本正確的3案直接綠，不偽稱先紅。定向830通過（63.34秒）；後補交易／模板與narration共98通過；最終受影響共用輸入／Web組67通過（6.77秒），皆1個既有Starlette警告。
- 原生System.Drawing Font.ToHfont＋GetTabbedTextExtentW獨立80案，ctypes全相同；原字型26空白182px、54個―756px。已安裝MS Gothic，沒有新增字型或改系統設定。
- CLEARLINE依引擎刪整個論理行，未換行緩衝原本就不清；HTML br屬同一組。先前偏離誤列已更正；LINECOUNT依VariableToken.cs:1529–1538與EmueraConsole.Print.cs:103。
- 三路fixture為render／powerup／system；全新25歲人工資料，人工前態與操作見tmp/s87/browser_fixture.py；子代理只做fixture傳輸冒煙，不冒充真瀏覽器。
- 非Windows與Web字形光柵化、個別精簡排版保留既有偏離；HTML只承諾原實用子集。無新增UNVERIFIED／DEVIATION，W07尚未結包，不跑500。
- 主代理最終全pytest：`5465 passed, 1 warning in 212.31s (0:03:32)`；初次5461通過後因瀏覽器實際失敗而修正，最終全套已含追加4案。
- 三路真瀏覽器通過：render保留60行歷史並清舊選項；system重複無效值／讀檔返回；powerup預約／清除／提交／返回，BASE50+100、點數900，前文不侵蝕。render／system沿用已過結果，只重驗修正路徑。
- 三路RNG不變、catalog／console失敗0、journal0、無worker；tmp/s87/browser-summary.json及截圖。全新25歲資料，替代MAXBASE41依原初始化為-1；人工局部前態，不冒充完整開局。服務／頁籤已關。
- source／reference未動，LF／UTF-8無BOM；不跑500，沿S84完整基線。未決13不變、未勾選偏離25→23，其他既有顯示差異保留；下一S88共用COUNT。

- 第1輪瀏覽器修正：CHARA_POWERUP少INPUT回顯造成每次多刪前文一行，已局部補回，原角色列表按原文保留；追加4案先紅後綠，受影響141案通過（2.11秒，1個既有警告）。產品／測試／fixture已凍結，僅需重驗powerup路徑，render不重跑。
