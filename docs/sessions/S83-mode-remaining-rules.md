# S83：W06 模式剩餘規則接通

## 完整成果與範圍
- W05驗收完成後依固定佇列進入W06；手翻接通PLAYABILITY所列六處ENDLESS／能力降低／INSTANT缺口，保留已完成七模式入口。
- 查ENDLESS擊破、戰後期限與既有最高紀錄的完整呼叫；沿原作持續／再生／終局條件，不把SURVIVAL當有限模式通關，不替SANDBOX新增結局。
- 查敵行動、PALAM_KIRYOKUDOWN／PALAM_SEITAISEIDOWN及INSTANT的EVENTCOMEND呼叫順序、選項與門檻；相同規則共用原生Python，不用catalog代執行狀態。
- 不只刪六處raise：新分支須有真呼叫者、原作返回／副作用及正常選項可達證據；若既有合法分支也漏翻，同一成果接通。
- 既有成就／GLOBAL、模式選擇、角色編輯、末王與結局實作重用；W02／W04已記錄阻塞不重查，W07顯示／WAIT與W08原作錯誤不擅擴張。

## 查證與測試
- 依序讀AGENTS、STATUS、PLAN、本規格與必要PLAYABILITY／wiki；精確搜尋先計數，只讀相關ERB／reference局部。
- 原文expected附檔案@函式:行號，引擎行為附reference檔案:行號；table-driven先紅後綠，不從Python輸出反推。
- 覆蓋選項ON/OFF、模式相依、門檻上下、零值／上限、RESULT(S)殘值、RNG耗用與副作用順序；至少各一條真戰鬥／回合呼叫鏈。
- 全新人工資料從建立起四年齡欄25，保留原生未設定哨兵；不改產品年齡規則。文字重用原catalog，不新增／改寫或摘錄露骨敘事。
- 若原作無定義或有錯，記入既有bridge並明示阻塞範圍，先完成可獨立部分；不得擅造係數、預設選項或永久限制。
- 新互動如有INPUT／確認，接既有generator與真輸入；不能用Null吞掉待驗路徑。

## 分級驗證與收尾
- 子代理只跑新增／受影響定向測試，提供tmp/s83/browser_fixture.py、可見前態、必要操作及原文expected；產品／測試凍結後主代理真瀏覽器與提交前一次全pytest。
- 本次為局部模式規則，預設不跑500；若查證實際改動共用排程／RNG／存讀檔等跨系統核心流程，先在本規格補具體理由才擴大。僅寫日期或碰共用檔案不自動觸發。
- W06整包仍需七模式生命週期／結局周回連續驗收；未達成整包DoD不提早跑結包500，也不宣稱B06或W09完成。
- 工具修正只重跑失敗／受影響範圍，純文件收尾沿用已通過證據，不重跑全套。
- 更新必要wiki、PLAYABILITY與bridge，STATUS／PLAN由主代理收口；下一完整成果須留在W06，列出具體未驗範圍。
- 繁體中文、LF／UTF-8無BOM、source／reference唯讀；自查git status／diff，不commit/push。
- 最後三段回報做了什麼／已查證的依據／需要使用者決定（UNVERIFIED／DEVIATION），附紅綠／定向摘要與實際修改路徑。
