# 共用 Web 輸入（S60b）

## 明確請求與邊界

- `WaitInputRequest` 表示 Enter 確認；`TextInputRequest` 表示文字；既有 `yield None` 仍表示數字輸入。
- 不根據 `TextOutput.wait_count`、歷史行的 `wait` 或 `yield None` 推定 WAIT。輸出可能已被略過，接著的 yield 可能是真正 INPUT。
- 本次僅將 `ERB/ゲーム内_イベント発生/オープニング処理.ERB@TUTORIAL` 的五個 PRINTW（483／501／516／540／575）接到明確等待標記。
- tutorial 原先以 `TextInputRequest` 等待，已可接受空字；本次改成獨立確認按鈕及正確的 `input_kind=wait`。**沒有全面修復其他舊 WAIT 必須輸入數字的問題**。
- `TextOutput.printw`／`wait` 保留既有輸出及計數功能，不自行暫停 generator。其他呼叫者須逐處核對後遷移。
- 不變更 INPUT 數字解析、INPUTS 空字／空白規則、遊戲狀態、RNG 或選單預設。不依賴未提交 S60 角色編輯器。

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
