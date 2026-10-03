# S30：catalog 剩餘不可執行函式（KOJO_AEGI・STRDATA 等）

使用者指定（2026-10-03）。S29 後 `python -m eragvt --narration-report`：13,384 函式中可執行 13,161。本階段補上剩餘的 unsupported 原因，
目標是口上／地の文全部可執行（做不到的逐一列出原因）。路徑相對 `source/earGVP/ERB/`。

## 範圍
1. **KOJO_AEGI 的 `GOTO ＭＡＸ２`（199 函式）**：`口上/口上システム関係/KOJO_AEGI.ERB`:4055 → :4062。GOTO 的跳轉目標
   `$ＭＡＸ２` 在外層 SELECTCASE 的另一個 CASE 之內（可能也在迴圈內），同檔的 `ＭＡＸ１` 等同類跳轉一併處理。
   跳進 SELECTCASE／IF／迴圈內部後，碰到 CASE／ELSE／ENDSELECT／NEXT 等的行為一律查
   `reference/emuera-1824`（`Instraction.Child.cs`、`FunctionIdentifier.cs`、GOTO 與迴圈命令的實作）並附行號，
   照引擎語意實作，不得以近似規則代替。S28c2 已支援「跳進 IF／SELECTCASE 內的 GOTO」（`runtime.Interp._exec_body`），請在其上擴充。
2. **STRDATA（17 函式）**：照引擎語意（`reference/emuera-1824` 的 STRDATA 實作：DATA／DATAFORM／DATALIST 的選擇與亂數使用）。
3. **其餘**：SETCOLORBYNAME、FINDCHARA、GETCOLOR，以及地の文經由呼叫碰到的 ADDRANDCHOOSE（RANDCHOOSE_NUM）、
   UNLOCK_ACHIEVEMENT（GLOBAL：照既有 deviation「全域資料不寫」處理，不另開例外）。
4. 補完後若出現新的第一原因，能在本階段範圍內合理補上的就補；需要大範圍新系統的停下列出。
5. 既有行為與測試不得改變；共用 RESULT／RESULTS 照 `docs/wiki/python/result.md`。

## 不在範圍
`KOJO_4_HITOKUTI_SHOP` 經動態呼叫碰到 INPUT 的處理（待使用者裁決，維持現況）。

## 測試（table-driven，expected 由 ERB 推導）
GOTO 跨 CASE／迴圈的引擎語意（小型 ERB 片段）；KOJO_AEGI 的代表分岐（含 ＭＡＸ１／ＭＡＸ２ 路徑）；STRDATA 的選擇與亂數；
其他各命令／式中関数；覆蓋率回歸（剩餘原因清單）。

## 模擬
`tools/sim.py --actions 101–108`，預設、初期セット各 250 場（seed 0–249，`--max-shop 200`），前景分批：停止原因、
catalog 執行時失敗與日誌還原次數（S29 的計數器全量統計），與 S29 對照（S29：預設 上限 245／初期セット 248）。

## 完成條件
pytest 全綠；覆蓋率數字更新到 STATUS（≤120 行）；deviations、unresolved、`docs/wiki/python/narration.md` 更新。
結束時務必送出三段報告。
