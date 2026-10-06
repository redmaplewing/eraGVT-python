# 共用 Web 輸入（S60b／S85）

## 明確請求與邊界

- `WaitInputRequest` 表示 Enter 確認；`TextInputRequest` 表示文字；既有 `yield None` 仍表示數字輸入。
- 不根據 `TextOutput.wait_count`、歷史行的 `wait` 或 `yield None` 推定 WAIT。輸出可能已被略過，接著的 yield 可能是真正 INPUT。
- S60b僅將 `ERB/ゲーム内_イベント発生/オープニング処理.ERB@TUTORIAL` 的五個 PRINTW（483／501／516／540／575）接到明確等待標記。
- S60b的tutorial 原先以 `TextInputRequest` 等待，已可接受空字；本次改成獨立確認按鈕及正確的 `input_kind=wait`。S85再修復下列四處同步包裝；其他舊等待仍未全面遷移。
- `TextOutput.printw`／`wait` 保留既有輸出及計數功能，不自行暫停 generator。其他呼叫者須逐處核對後遷移。
- 不變更 INPUT 數字解析、INPUTS 空字／空白規則、遊戲狀態、RNG 或選單預設。不依賴未提交 S60 角色編輯器。

## S85：同步確認與當前控制項

- 已查證的同步包裝共有四個呼叫點：`game/achievements.py@unlock`，以及`game/ending.py@_endless_record`與`score`的兩處等待；全部由`wait(None)`改傳`WaitInputRequest()`。包裝只轉送明確請求，不依輸出計數或generator的`None`猜測。
- 原作依據：`ERB/インターミッション画面/SHOP_TROPHY.ERB@UNLOCK_ACHIEVEMENT:15–19`（成就保存前），`ERB/ゲーム内_イベント発生/エンディング/ENDING.ERB@ENDING_1:270–277`（新紀錄保存前；共用ENDING_3／ENDING_6），`ERB/ゲーム内_イベント発生/エンディング/SCORE.ERB@SCORE:694–698、738–749`（最高評分及通關數保存前）。
- WAIT不寫RESULT(S)或消耗RNG。`unlock`確認後函式流落的RESULT:0=0仍保留；ENDLESS進等待前LOADGLOBAL失敗寫RESULT:0=0仍保留，依`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:1293–1299`，不錯歸為WAIT的寫入。
- 等待頁保留歷史選單的標籤及樣式，但不建立可提交的選項按鈕；頁尾只提供確認與返回標題。恢復INPUT後按原輸入類型顯示控制項，不清空敘事歷史，也不新增選項值白名單。
- S79／S80的catalog `waits=True`既有通道直接沿用；混合WAIT／INPUT／INPUTS／FORCEWAIT及catalog呼叫原生成就的雙層通道，均保留原請求型別與順序。沒有全面啟用尚未逐處核對的舊catalog／同步printw。
- 模擬器只認`session.input_kind == "wait"`，移除以`achievement_wait` callback存在推斷確認的舊捷徑；真正數字INPUT仍使用策略選項，確認不消耗策略RNG。正常包裝在轉送數字INPUT前已恢復callback，舊捷徑只覆蓋四處同步確認，故此工具改動不改正常數字選擇策略。
- 未完成範圍：既有只印分隔、不真正等待的同步printw／wait，以及其他舊以數字輸入包裝的等待，仍屬W07。S85不是WAIT全數遷移或W07結包。

## 引擎依據

- WAIT：`reference/emuera-1824/Emuera/GameProc/Function/Instraction.Child.cs:562–577` 呼叫 `ReadAnyKey()`。
- PRINTW：同檔 `:226–230` 在換行後呼叫 `ReadAnyKey()`。
- `reference/emuera-1824/Emuera/GameView/EmueraConsole.cs:497–508`：預設請求為 `EnterKey`。
- 同檔 `:707–734`：只有 IntValue／StrValue 呼叫 InputInteger／InputString；Enter 確認不寫 RESULT／RESULTS。
- 同檔 `:709–719`：無預設值的空數字不能通過 TryParse；`:722–729`：字串空輸入保留空字。

## Web 傳輸與驗收

- 等待頁顯示可聚焦的確認按鈕；載入後捲到底並聚焦按鈕，Enter 可提交空字。數字仍為 required；文字可空白。
- 每頁表單帶 `input_token`。相同 token 的重送／重啟前舊頁不再推進 generator；鎖保護檢查及推進，避免同步 POST 重複消耗。
- API 回傳 token，POST 可附 token 去重。省略 token 的既有 API／表單客戶端保持相容，因此**不提供無 token 客戶端的重送保護**。
- token 是 Web 傳輸細節，不是存檔資料或遊戲狀態；重啟使用新 token，並沿既有 `close()` 關閉 generator。
- 先紅：新增中性測試在缺 `WaitInputRequest` 時 collection 失敗；實作後定向通過。
- 指令：`python -m pytest tests/test_generic_input.py tests/test_tutorial.py tests/test_text_output.py -q -k "not web_opening_continue"`。
- 子代理結果：`54 passed, 2 deselected, 1 warning in 1.98s`。排除的兩項含完整開局；未執行全局模擬、S60 編輯器驗收或全 pytest。
- 中性瀏覽器：`python tools/preview_generic_input.py --port 8871`，開啟 `http://127.0.0.1:8871`。先 Enter、再按確認；數字空字不可送，輸入 12；文字可直接 Enter；最後確認60行長內容的捲動與焦點，返回標題。
- 預覽用實際 app／模板／JS／session 握手，僅載入資料及中性 generator，存檔目錄為臨時目錄；不進入角色或遊戲內容。真瀏覽器結果由父代理另行記錄。

## 父代理獨立驗收

- 相同中性定向指令：`54 passed, 2 deselected, 1 warning in 1.94s`。未執行全pytest或500局，不代表S60或完整遊戲驗收通過。
- 真瀏覽器8871：Enter推進第一等待、按鈕推進第二等待；數字空白顯示必填且不推進，12進文字，空字提交顯示空字；60行長頁焦點在確認按鈕，等待中返回標題成功。
- S60角色編輯改動保持未提交；本次無新增UNVERIFIED或需裁決偏離。舊WAIT偏離仍未完成。
- 父代理於HEAD隔離複本（僅覆蓋S60b檔案）獨立重跑：`54 passed, 2 deselected, 1 warning in 1.89s`；不含S60新角色編輯模組，相關舊模組逐byte與HEAD一致，確認本次不依賴未提交S60。

## S85定向驗收與瀏覽器入口

- 先紅：新明確請求與模板契約`8 failed, 137 passed`；另模擬器「callback存在但請求為number」合成前態的契約亦先紅後綠，並非已發現正常流程可達的誤選。
- 定向：`python -m pytest tests/test_generic_input.py tests/test_explicit_wait.py tests/test_achievements.py tests/test_records.py tests/test_opening_sequence.py tests/test_battle_side_events.py tests/test_tutorial.py -q` → `280 passed, 1 warning in 5.45s`。
- 工具契約：`python -m pytest tests/test_sim_isolation.py -q -k achievement_confirmation_preserves_policy_rng` → `1 passed, 5 deselected in 0.07s`。沒有重跑無關模擬工具批次。
- 新增六案驗成就保存前後RESULT(S)／RNG、三種文字值、catalog巢狀成就的正常／中止；沿用S60b重送與重啟、S79／S80明確等待測試。ENDLESS新紀錄及SCORE兩等待的既有案例補RESULT(S)／RNG斷言。
- 臨時瀏覽器fixture：`python tmp/s85/browser_fixture.py --scenario mixed --port 8885`，中性catalog順序為Enter→數字空白必填→[12]→確認→空字Enter→60行尾端確認→標題；任一等待也可返回標題。
- 另一入口：`python tmp/s85/browser_fixture.py --scenario achievement --port 8886`，全新25歲人工角色正常初始化後施攻擊500前態，真`get_state_trophy`等待→確認→[7]數字INPUT→標題。確認前GLOBAL220=0／未保存；之後GLOBAL220=1／已保存；RNG全程不變。
- fixture的`/audit`提供RESULT(S)、保存／RNG／catalog失敗／worker狀態；臨時存檔不碰既有存檔，未設定的另一形態年齡-1保留。上述fixture API冒煙通過；主代理真瀏覽器及提交前全pytest結果由STATUS收口。
- 此修改只傳遞原有四個停止點的請求型別及呈現，未新增狀態寫入／排程／RNG／存讀行為，W07尚未結包，依分級驗證不跑500局。無新增UNVERIFIED／DEVIATION。

- S85主代理兩路真瀏覽器已通過：mixed的Enter、數字空白必填、[12]、確認、空文字、60行尾端焦點與捲動、返回標題；achievement確認前後GLOBAL220／保存及[7]數字輸入均符合上述expected。等待期間歷史選項僅文字；普通數字／文字期間既有歷史按鈕行為未改。
- 兩路catalog／console失敗0，完成後worker空、journal深度0；RNG不變、RESULT(S)尾格保留。證據tmp/s85/browser-summary.json／browser-achievement-wait.png／browser-mixed-tail.png；主代理只加/audit-view HTML呈現稽核資料，不改流程。
- 主代理全pytest：`5404 passed, 1 warning in 181.72s (0:03:01)`。此階段沒有重跑500，沿用S84最近完整基線；不把本次fixture初始化當新一次完整開局驗收。
