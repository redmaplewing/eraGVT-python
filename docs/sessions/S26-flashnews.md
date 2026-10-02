# S26：FLASHNEWS（每日新聞）

自主推進（使用者指定 2026-10-02）第 5 階段。路徑相對 `source/earGVP/ERB/`。

## 背景
`shop.flashnews` 目前只印「（未實作）」（deviations.md「FLASHNEWS 未移植」）：新聞產生（含亂數、寫 `SAVESTR:20`、`FLAG:60`）、
ゲームオーバーモードの固定ニュース（`FLAG:60 = 10001`，:91–）都沒有執行。這會影響亂數序列與 SAVESTR:20／FLAG:60 的值。

## 範圍
1. `インターミッション画面/SHOP_FLASHNEWS.ERB` 全體：`@FLASHNEWS`（:3–752）、`@FLASH_VIRALMEDIA`（:754）、`@FLASHNEWS_CHOOSEHEROINE`（:888）、
   `@FLASHNEWS_CHOOSEIDOL`（:927，含 S14 記錄的 CFLAG:284 加權）。新聞文字照原文輸出（地の文性質的部分可走 S07 catalog）。
2. 讀取的狀態若屬未移植系統（特別活動的偶像等），照原文讀現有值（未移植系統的值通常為 0），不另加停止；若有分岐會呼叫未移植函式，照慣例停止並記錄。
3. 共用 RESULT／RESULTS：此檔若有多值 RETURN 或 RESULTS 寫入，照 `docs/wiki/python/result.md` 的規則同步。
4. deviations.md「FLASHNEWS 未移植」結案（或縮小到剩餘部分）。

## 測試（table-driven，expected 由 ERB 推導）
各新聞分岐的觸發條件與輸出（FixedRng）；ゲームオーバーモード固定ニュース（DAY:2 起算）；SAVESTR:20／FLAG:60 的寫入。

## 模擬
`tools/sim.py` 預設、初期セット各 250 場（seed 0–249，`--max-shop 200`）：確認無新停止；亂數序列會改變，結果與 S25 不可直接比較，只看停止。
受亂數影響的既有 seed 測試若需調整，依 ERB 重新推導或改指定經路，不得照 Python 輸出改。

## 完成條件
pytest 全綠；STATUS（≤120 行）、deviations、unresolved 更新。結束時務必送出三段報告。
