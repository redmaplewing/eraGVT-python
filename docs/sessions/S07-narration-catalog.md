# S07：口上／地の文抽取管線（catalog + 條件樹 → NarrationService）

## 目標
把 `ERB/口上/`（114 檔）與 `ERB/地の文/`（61 檔）的**文字與選擇條件**抽成可執行的資料樹，由 Python 求值後輸出；
取代 S05／S06 的「〈地の文：…〉」佔位與 `NullNarrationService` 的 -1 回落。**不是** ERB 直譯器：
只支援「文字輸出＋條件分岐」這個受限子集，子集外的函式一律標為不支援並回落，不去補一般化的執行引擎。

## 範圍
1. **抽取器**（`src/eragvt/narration/extract.py` 之類）：以函式（`@NAME`）為單位把 ERB 轉成節點樹。
   - 支援：PRINT 系（PRINT/PRINTL/PRINTW/PRINTFORM*/PRINTS*/PRINTPLAIN*/PRINTDATA+DATA/DATAFORM）、
     IF/ELSEIF/ELSE、SELECTCASE（含 CASE 範圍／IS 比較／CASEELSE）、SIF、SETCOLOR/RESETCOLOR、
     FONTBOLD/FONTREGULAR、DRAWLINE、WAIT、RETURN、LOCAL／LOCALS 代入、白名單內的 CALL（見下）。
   - FORM 字串（`%式%`、`{式}`、`\@ ? # \@`）與條件式解析成小型 AST；變數存取、四則／比較／邏輯（短路、同優先度
     左結合，已於 S05／S06 查證）、`RAND:n`、白名單函式（CALLNAME、SELF_CALL、スラング系…依實際需要逐一移植）。
   - 遇到子集外的敘述（對非 LOCAL 變數代入、未知 CALL、GOTO…）→ 整個函式標 `unsupported`（附原因與行號），
     **不猜**。已在 `battle/sexmsg.py` 移植過狀態變化的地の文函式：抽取時可略過那些狀態變化行，
     但必須逐行列出略過清單並與 sexmsg 的註解互相對照（不得悄悄吞掉任何代入）。
   - 輸出每檔／每函式的覆蓋率報告（腳本或 `python -m eragvt --narration-report`），列進 STATUS。
2. **執行器**：對節點樹求值，寫入 `TextOutput`（顏色、粗體、按鈕切法沿用 `text/output.py`）；
   亂數一律用注入的 `GameRng`，**依 ERB 的求值順序**抽 RAND（這會改變既有 seed 測試的亂數序列：受影響的 expected
   要依 ERB 重新推導並附行號，不可照 Python 輸出改）。
3. **NarrationService 介面調整**：現行 `narrate() -> str | None` 不足以表達顏色與 state 存取，改為可寫入
   TextOutput、能讀 GameState 的形式（回傳 -1 = 找不到；行數語意照 `KOJO_ROOT.ERB` 的 RETURN）。
   `KOJO_ROOT` 的派發規則（汎用口上 `KOJO_{C_NO}_%CODE%_{SEIKAKU_CHECK_F(TARGET)}`、COLOR 函式、
   `OTHER_` 系、TRYCCALLFORM/CATCH、FLAG:62／FLAG:900）照原文移植；`SEIKAKU_CHECK_F` 查原文。
4. **接上現有呼叫點**：`action.kojo_root`、`shop` 一口メッセージ、`battle/core.chinobun` 的所有呼叫、
   `MESSAGE_BATTLE_END_LOSS` 等 S05／S06 已經走到的地の文。可執行的函式改輸出本文；unsupported 的保留原佔位。
   Web 預設改用 catalog 版 NarrationService（無 source 目錄時回落 Null）。
5. **catalog 的存放**：從 `source/` 在執行期（lazy、依檔案）抽取並快取；**不要**把數 MB 的產生物 commit 進 repo。
   若啟動時間 > 3 秒再考慮產生快取檔（放 `.gitignore` 內）。

## 查證要點
- Emuera：PRINTDATA 的選擇方式、FORM 字串 `\@…?…#…\@` 語法、`%式,寬,LEFT%`、SELECTCASE 的 CASE 語法、
  TRYCCALLFORM/CATCH、RETURN 與 RESULT、LINECOUNT —— 全部附 `reference/emuera-1824/...cs:行號`。
- 原作：`KOJO_ROOT.ERB`、`KOJO_式中関数.ERB`、スラング系函式的原文行號。

## 測試（table-driven，expected 由 ERB 推導）
- 抽取器：代表片段 → 節點樹（IF/SELECTCASE/PRINTDATA/FORM/unsupported 判定各數例）。
- 執行器：固定 FixedRng 下，至少 3 個真實函式（例：`KOJO_0_HITOKUTI_SHOP_13`、一個 MESSAGE_SEX_COM、
  `MESSAGE_BATTLE_END_LOSS`）輸出與手算 ERB 結果一致。
- KOJO_ROOT：氣絕／結界／找不到（-1）／汎用性格派發。
- Web 整合：新遊戲 → SHOP 畫面出現一口メッセージ本文（seed 固定）。
- 全部既有測試仍綠（受 RAND 序列影響的，依上述規則更新）。

## 不做
- AI 敘事生成；口上的「狀態變化」新移植（除非已被現有流程呼叫且只是 LOCAL）。
- 子集外語法的一般化支援（登記到 STATUS 的覆蓋率報告即可，S08+ 再決定）。

## 完成條件
pytest 全綠；覆蓋率報告（函式數／可執行數／前 10 大 unsupported 原因）寫進 STATUS；
新的 DEVIATION／UNVERIFIED 登記；wiki 新增 `docs/wiki/python/narration.md`（< 300 行）說明節點格式與子集。
