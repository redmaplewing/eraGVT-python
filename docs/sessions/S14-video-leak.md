# S14：動画流出（DOUGA_RYUSUTU 與動画サイト表示）

## 背景
S13 後最大的停止原因是動画流出（預設開局 250 場中 40 場）。停止點：
`battle/after.py@douga_ryusutu`（`ゲーム内_イベント発生/戦闘イベント.ERB@DOUGA_RYUSUTU`:1338–1478 的一般流出與レイプ動画流出兩分岐）、
`battle/sexmsg.py:554`（`MESSAGE_SEX_SPCOM7`:1242–1279 的動画サイト表示，INPUTS 輸入 "1" 時）。路徑相對 `source/earGVP/ERB/`。

## 範圍
1. **流出本體**：`DOUGA_RYUSUTU` 全體（TFLAG:21 各 bit 的組合分岐、CFLAG:284／285 的增加、SHORTLINE 等被呼叫函式），
   呼叫端 `BATTLE_TRAIN_AFTER.ERB`:503 的 RESULT 來源照原文確認。
2. **流出的後續影響**：CFLAG:284／285 在已移植流程中的讀取處全部接上——
   `SHOP_TURNEND.ERB`（4 處）、`SHOP_FLASHNEWS.ERB`（2 處；FLASHNEWS 本體未移植，只移植會改變狀態的部分，
   顯示部分照既有「FLASHNEWS 未移植」的 deviation 處理）。
   其餘讀取者（`FORCE_クズ市民の脅迫`、`PASTIME_写真`、`SEISAN_*`）屬未移植系統，只記錄不移植。
3. **動画サイト表示**：`地の文/MESSAGE_WindowLibrary_VideoHostSite.ERB@MESSAGE_SEX_VIDEO_SITE_Window`（1473 行）。
   以顯示為主：文字走 S07 catalog；catalog 不支援的語法（例如 HTML_PRINT 子集外、繪圖指令）先擴充 catalog 支援子集，
   仍不可行時以 DEVIATION（只影響顯示）印佔位並說明。若其中有狀態變化，照 hooks 表方式移植。
   INPUTS 的互動照 S11 既有的輸入模式接 Web。
4. **catalog 擴充**：若本階段需要，順帶支援 GOTO／SPLIT／STRDATA 等 S07 覆蓋率報告中與本階段函式相關的語法，
   並更新覆蓋率數字。不做與本階段無關的擴充。

## 不做
- クズ市民の脅迫、自由行動中的写真、特別活動（SEISAN）等其他讀取 CFLAG:284／285 的系統。
- FLASHNEWS 顯示本體。

## 查證要點
- TFLAG:21 各 bit、CFLAG:284／285 的意義照 `●開発者向け資料/●GVTフラグ一覧.txt` 與原文註解。
- 引擎行為（INPUTS、HTML_PRINT、SETCOLOR 等）附 `reference/emuera-1824/...cs:行號`。

## 測試（table-driven，expected 由 ERB 推導）
- DOUGA_RYUSUTU：TFLAG:21 的代表組合（依原文分岐挑選，至少覆蓋每個 IF 的兩側）→ 輸出行與 CFLAG:284／285。
- レイプ動画流出（ARG == 1）。
- 動画サイト表示：INPUTS "1" 與其他輸入的分岐；若有狀態變化則驗證。
- SHOP_TURNEND 中 CFLAG:284／285 的後續影響。

## 模擬
`tools/sim.py` 跑預設開局與初期セット各 250 場（seed 0–249，`--max-shop 200`）：停止原因頻度、停止前 SHOP 次數，與 S13 對照寫進 STATUS。

## 完成條件
pytest 全綠；STATUS、deviations、unresolved 更新；必要時更新 `docs/wiki/python/narration.md` 的覆蓋率。
