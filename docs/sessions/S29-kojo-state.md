# S29：口上的狀態副作用（非 LOCAL 變數代入）

使用者指定（2026-10-03）。解除 `deviations.md`「口上的狀態副作用」：目前口上函式只要對非 LOCAL 變數代入，catalog 就判為
unsupported，KOJO_ROOT 當「找不到」（不輸出、不改狀態）；原作會輸出口上並改變狀態。路徑相對 `source/earGVP/ERB/`。

## 現況（`python -m eragvt --narration-report`，2026-10-03）
函式 13384，可執行 12851。unsupported 第一原因中與本階段相關者：非 LOCAL 代入 CFLAG 187、TALENT 30、NAME 20、CSTR 20、
BASE 20、CDFLAG 13，未対応の変数 TCVAR 12（共約 300 函式；例 `口上/★KOJO_0_16_真面目/鍛錬.ERB` 的 TRAINING 系寫 CFLAG）。

## 範圍
1. 先盤點：列出全部口上（`口上/`）與地の文中「非 LOCAL 代入」的變數種類、索引形式（含キャラ指定 `CFLAG:TARGET:n`、CSV 名索引、
   `+=` 等複合代入、字串變數），以及這些函式內 CALL 的非口上函式（會改狀態者）。盤點結果寫進 `docs/wiki/python/narration.md`。
2. catalog 支援把這些代入**直接寫入 `GameState`**（對應既有的狀態模型：CFLAG／TALENT／BASE／NAME／CSTR／CDFLAG／TCVAR 等），
   語意查 `reference/emuera-1824`（索引範圍、字串／整數、キャラ變數的角色指定、BASE 與 MAXBASE 的關係等）並附行號。
   不再需要逐行登記 hooks 表的變數種類，以「全口上的代入都被支援」的測試保證不遺漏；hooks 表保留給 CALL 到 Python 移植函式的情況。
3. 口上內 CALL 的會改狀態的非口上函式：已有 Python 移植者接到 hook；尚未移植者照慣例停止並列出（不擴大範圍）。
4. 失敗回復（`deviations.md`「口上 catalog 的實行時失敗」）：catalog 寫入 GameState 時記錄變更（transaction），執行中失敗即可完整回復，
   不再因「狀態已變」而停止。原作會報錯停止的情況（除以 0、範圍外參照）照既有處理並更新文件說明。
5. 已用 hooks 表登記的既有代入行（LOVESEX／PRISON／PASTIME／NANPA 等）行為不得改變；若改用新機制，既有測試必須全綠。
6. 共用 RESULT／RESULTS 照 `docs/wiki/python/result.md`。

## 測試（table-driven，expected 由 ERB 推導）
各變數種類的代入（含キャラ指定、CSV 名索引、複合代入、字串）；代表口上函式（例 TRAINING 系）執行後的狀態；
失敗回復（中途失敗後狀態完全回到呼叫前）；覆蓋率回歸：上述「非 LOCAL 代入」「TCVAR」原因歸零或列出剩餘原因。

## 模擬
`tools/sim.py --actions 101–108`，預設、初期セット各 250 場（seed 0–249，`--max-shop 200`），前景分批：停止原因、
口上可執行數變化，與 S28c2 對照（S28c2：上限 247／249）。

## 完成條件
pytest 全綠；覆蓋率數字更新到 STATUS（≤120 行）；deviations（「口上的狀態副作用」「實行時失敗」改寫）、unresolved、
`docs/wiki/python/narration.md` 更新。結束時務必送出三段報告。
